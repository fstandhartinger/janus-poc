import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('transcription', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
    vi.clearAllMocks();
  });

  it('transcribes via gateway', async () => {
    process.env.NEXT_PUBLIC_GATEWAY_URL = 'http://localhost:9999';

    const { transcribeViaGateway } = await import('./transcription');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ text: 'hello' }),
    });

    const result = await transcribeViaGateway(new Blob(['test'], { type: 'audio/webm' }));

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:9999/api/transcribe',
      expect.objectContaining({ method: 'POST' })
    );

    const [, init] = mockFetch.mock.calls[0];
    expect(init?.body).toBeInstanceOf(FormData);
    const formData = init?.body as FormData;
    expect(formData.get('model')).toBe('whisper-1');
    expect(result.text).toBe('hello');
  });

  it('requires a public api key for direct transcription', async () => {
    process.env.NEXT_PUBLIC_CHUTES_API_KEY = '';

    const { transcribeAudio } = await import('./transcription');

    await expect(transcribeAudio(new Blob(['test']))).rejects.toThrow('Chutes API key not configured');
  });

  it('sends direct transcription requests with auth', async () => {
    process.env.NEXT_PUBLIC_CHUTES_API_KEY = 'test-key';

    const { transcribeAudio } = await import('./transcription');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ text: 'hello' }),
    });

    const result = await transcribeAudio(new Blob(['test'], { type: 'audio/webm' }));

    expect(mockFetch).toHaveBeenCalledWith(
      'https://chutes-whisper-large-v3.chutes.ai/transcribe',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer test-key' }),
      })
    );
    const [, init] = mockFetch.mock.calls[0];
    expect(init?.body).toBeInstanceOf(FormData);
    expect(result.text).toBe('hello');
  });
});
