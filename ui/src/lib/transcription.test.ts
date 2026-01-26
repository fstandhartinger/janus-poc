import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

class MockFileReader {
  result: string | null = null;
  onloadend: ((ev: ProgressEvent<FileReader>) => void) | null = null;
  onerror: ((ev: ProgressEvent<FileReader>) => void) | null = null;

  readAsDataURL(_blob: Blob) {
    this.result = 'data:audio/webm;base64,Zm9v';
    this.onloadend?.(new Event('loadend') as ProgressEvent<FileReader>);
  }
}

describe('transcription', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('FileReader', MockFileReader as unknown as typeof FileReader);
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
    expect(init?.body).toContain('"audio_b64":"Zm9v"');
    expect(result.text).toBe('hello');
  });

  it('handles list responses from gateway', async () => {
    process.env.NEXT_PUBLIC_GATEWAY_URL = 'http://localhost:9999';

    const { transcribeViaGateway } = await import('./transcription');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([{ text: 'Hello' }, { text: 'world' }]),
    });

    const result = await transcribeViaGateway(new Blob(['test'], { type: 'audio/webm' }));

    expect(result.text).toBe('Hello world');
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
    expect(init?.body).toContain('"audio_b64":"Zm9v"');
    expect(result.text).toBe('hello');
  });
});
