/**
 * API client for communicating with the Janus Gateway.
 */

import type { ChatCompletionRequest, ChatCompletionChunk, ChatStreamEvent, Model } from '@/types/chat';

const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_STREAM_TIMEOUT_MS = 30000;
const DEFAULT_RETRIES = 2;
const DEFAULT_RETRY_DELAY_MS = 500;
const RETRYABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

export function normalizeGatewayUrl(rawUrl: string): string {
  const trimmed = rawUrl.trim().replace(/\/+$/, '');
  if (!trimmed) {
    return 'http://localhost:8000';
  }
  if (trimmed.includes('://')) {
    return trimmed;
  }
  if (trimmed.startsWith('localhost') || trimmed.startsWith('127.0.0.1')) {
    return `http://${trimmed}`;
  }
  return `https://${trimmed}`;
}

export const GATEWAY_URL = normalizeGatewayUrl(
  process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8000'
);

type FetchRetryOptions = {
  retries?: number;
  timeoutMs?: number;
  retryDelayMs?: number;
};

function isAbortError(error: unknown): boolean {
  if (error instanceof DOMException) {
    return error.name === 'AbortError';
  }
  return Boolean((error as { name?: string })?.name === 'AbortError');
}

function shouldRetryResponse(response: Response): boolean {
  return RETRYABLE_STATUS.has(response.status);
}

function getRetryDelayMs(response: Response | null, baseDelayMs: number, attempt: number): number {
  const headerValue = response?.headers.get('retry-after');
  if (headerValue) {
    const seconds = Number(headerValue);
    if (Number.isFinite(seconds) && seconds > 0) {
      return seconds * 1000;
    }
  }
  const jitter = Math.random() * baseDelayMs * 0.2;
  return Math.min(baseDelayMs * 2 ** attempt + jitter, 8000);
}

function createAbortSignal(timeoutMs: number, upstream?: AbortSignal | null) {
  const controller = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let timedOut = false;

  const abortFromUpstream = () => {
    controller.abort();
  };

  if (upstream) {
    if (upstream.aborted) {
      controller.abort();
    } else {
      upstream.addEventListener('abort', abortFromUpstream);
    }
  }

  if (timeoutMs > 0) {
    timeoutId = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
  }

  const cleanup = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    if (upstream) {
      upstream.removeEventListener('abort', abortFromUpstream);
    }
  };

  return { signal: controller.signal, cleanup, timedOut: () => timedOut };
}

async function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

export async function fetchWithRetry(
  url: string,
  init: RequestInit = {},
  options: FetchRetryOptions = {}
): Promise<Response> {
  const {
    retries = DEFAULT_RETRIES,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    retryDelayMs = DEFAULT_RETRY_DELAY_MS,
  } = options;

  let attempt = 0;
  let lastError: unknown = null;

  while (attempt <= retries) {
    const { signal, cleanup, timedOut } = createAbortSignal(timeoutMs, init.signal);
    try {
      const response = await fetch(url, { ...init, signal });
      cleanup();

      if (!response.ok && shouldRetryResponse(response) && attempt < retries) {
        const cancelPromise = response.body?.cancel();
        if (cancelPromise) {
          cancelPromise.catch(() => undefined);
        }
        const delayMs = getRetryDelayMs(response, retryDelayMs, attempt);
        await sleep(delayMs);
        attempt += 1;
        continue;
      }

      return response;
    } catch (error) {
      cleanup();
      if (init.signal?.aborted) {
        throw error;
      }
      if (isAbortError(error) && !timedOut()) {
        throw error;
      }
      lastError = error;
      if (attempt >= retries) {
        break;
      }
      const delayMs = getRetryDelayMs(null, retryDelayMs, attempt);
      await sleep(delayMs);
      attempt += 1;
    }
  }

  throw lastError ?? new Error('Request failed');
}

async function fetchJson<T>(
  url: string,
  init: RequestInit = {},
  options: FetchRetryOptions = {}
): Promise<T> {
  const response = await fetchWithRetry(url, init, options);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchModels(): Promise<Model[]> {
  const data = await fetchJson<{ data: Model[] }>(
    `${GATEWAY_URL}/v1/models`,
    {},
    { timeoutMs: DEFAULT_TIMEOUT_MS }
  );
  return Array.isArray(data.data) ? data.data : [];
}

export async function* streamChatCompletion(
  request: ChatCompletionRequest,
  signal?: AbortSignal
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetchWithRetry(
    `${GATEWAY_URL}/v1/chat/completions`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({
        ...request,
        stream: true,
      }),
      signal,
    },
    { timeoutMs: DEFAULT_STREAM_TIMEOUT_MS }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Chat completion failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith(':')) {
        // Empty line or keep-alive comment
        continue;
      }
      if (trimmed.startsWith('data:')) {
        const data = trimmed.slice(5).trim();
        if (data === '[DONE]') {
          return;
        }
        try {
          const parsed = JSON.parse(data) as ChatStreamEvent;
          if (
            parsed &&
            typeof parsed === 'object' &&
            'type' in parsed &&
            parsed.type === 'screenshot'
          ) {
            yield parsed;
            continue;
          }
          const chunk = parsed as ChatCompletionChunk;
          if (chunk && Array.isArray(chunk.choices)) {
            yield chunk;
          }
        } catch {
          console.warn('Failed to parse SSE chunk:', data);
        }
      }
    }
  }
}

export type DeepResearchProgressPayload = {
  label?: string;
  status?: 'pending' | 'running' | 'complete' | 'error' | string;
  detail?: string;
  percent?: number;
};

export type DeepResearchEvent =
  | { type: 'progress'; data: DeepResearchProgressPayload }
  | { type: 'sources'; data: unknown }
  | { type: 'response'; data: string }
  | { type: 'error'; data: { detail?: string } }
  | { type: 'unknown'; data: unknown };

function coerceDeepResearchEvent(raw: unknown): DeepResearchEvent | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  const candidate = raw as { type?: unknown; data?: unknown };
  if (candidate.type === 'progress') {
    return { type: 'progress', data: candidate.data as DeepResearchProgressPayload };
  }
  if (candidate.type === 'sources') {
    return { type: 'sources', data: candidate.data };
  }
  if (candidate.type === 'response') {
    return { type: 'response', data: candidate.data as string };
  }
  if (candidate.type === 'error') {
    return { type: 'error', data: (candidate.data as { detail?: string }) ?? {} };
  }
  return { type: 'unknown', data: candidate };
}

export async function* streamDeepResearch(
  request: { query: string; mode?: 'light' | 'max'; optimization?: 'speed' | 'balanced' | 'quality' },
  signal?: AbortSignal
): AsyncGenerator<DeepResearchEvent> {
  const response = await fetchWithRetry(
    `${GATEWAY_URL}/api/research`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(request),
      signal,
    },
    { timeoutMs: DEFAULT_STREAM_TIMEOUT_MS }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Deep research failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith(':')) {
        continue;
      }
      if (trimmed.startsWith('data:')) {
        const data = trimmed.slice(5).trim();
        if (data === '[DONE]') {
          return;
        }
        try {
          const event = coerceDeepResearchEvent(JSON.parse(data));
          if (event) {
            yield event;
          }
        } catch {
          console.warn('Failed to parse research SSE chunk:', data);
        }
      }
    }
  }
}

export function getArtifactUrl(artifactId: string): string {
  return `${GATEWAY_URL}/v1/artifacts/${artifactId}`;
}
