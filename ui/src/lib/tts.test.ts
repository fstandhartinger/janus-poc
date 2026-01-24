import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('tts', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    vi.stubGlobal(
      'btoa',
      (input: string) => Buffer.from(input, 'binary').toString('base64')
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
    vi.clearAllMocks();
  });

  it('strips markdown and caches audio', async () => {
    const createObjectURL = vi.fn(() => 'blob:tts-audio');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL } as unknown as typeof URL);

    const audioBuffer = new TextEncoder().encode('audio');
    mockFetch.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: () => Promise.resolve(audioBuffer.buffer),
    });

    const { generateSpeech, clearAudioCache } = await import('./tts');

    const text = [
      '# Header',
      '',
      'Hello **world**!',
      '',
      '`code`',
      '',
      '[Link](https://example.com)',
      '',
      '![Alt](image.png)',
      '',
      '- item',
      '1. item',
      '',
      '```',
      'block',
      '```',
    ].join('\n');

    const audioUrl = await generateSpeech(text, 'af_sky', 1.0);
    const body = JSON.parse(mockFetch.mock.calls[0][1].body as string);

    expect(body.text).toBe(
      'Header\n\nHello world!\n\ncode\n\nLink\n\nimage: Alt\nitem\nitem\n\ncode block'
    );
    expect(audioUrl).toBe('blob:tts-audio');

    const cachedUrl = await generateSpeech(text, 'af_sky', 1.0);
    expect(cachedUrl).toBe('blob:tts-audio');
    expect(mockFetch).toHaveBeenCalledTimes(1);

    clearAudioCache();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:tts-audio');
  });
});
