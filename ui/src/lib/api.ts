/**
 * API client for communicating with the Janus Gateway.
 */

import type { ChatCompletionRequest, ChatCompletionChunk, ChatStreamEvent, Model } from '@/types/chat';

function normalizeGatewayUrl(rawUrl: string): string {
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

export async function fetchModels(): Promise<Model[]> {
  const response = await fetch(`${GATEWAY_URL}/v1/models`);
  if (!response.ok) {
    throw new Error(`Failed to fetch models: ${response.statusText}`);
  }
  const data = await response.json();
  return data.data;
}

export async function* streamChatCompletion(
  request: ChatCompletionRequest,
  signal?: AbortSignal
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${GATEWAY_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...request,
      stream: true,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Chat completion failed: ${response.statusText}`);
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
  const response = await fetch(`${GATEWAY_URL}/api/research`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Deep research failed: ${response.statusText}`);
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
