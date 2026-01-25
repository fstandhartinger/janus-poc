import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchWithRetry, normalizeGatewayUrl } from './api';

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe('normalizeGatewayUrl', () => {
  it('adds protocol to bare hostnames', () => {
    expect(normalizeGatewayUrl('example.com')).toBe('https://example.com');
  });

  it('keeps localhost on http', () => {
    expect(normalizeGatewayUrl('localhost:8080')).toBe('http://localhost:8080');
  });

  it('falls back to localhost when empty', () => {
    expect(normalizeGatewayUrl('  ')).toBe('http://localhost:8000');
  });
});

describe('fetchWithRetry', () => {
  it('retries on retryable status codes', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('', { status: 503 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

    global.fetch = fetchMock as typeof fetch;

    const response = await fetchWithRetry('https://example.com', {}, { retries: 1, retryDelayMs: 1 });
    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('returns immediately for non-retryable responses', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('Bad request', { status: 400 }));
    global.fetch = fetchMock as typeof fetch;

    const response = await fetchWithRetry('https://example.com', {}, { retries: 2, retryDelayMs: 1 });
    expect(response.status).toBe(400);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
