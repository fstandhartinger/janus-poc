import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import { useAudioRecorder } from './useAudioRecorder';

class MockMediaRecorder {
  static isTypeSupported = vi.fn((mimeType: string) => mimeType.includes('webm'));

  public mimeType: string;
  public state: 'inactive' | 'recording' | 'paused' = 'inactive';
  public ondataavailable: ((event: BlobEvent) => void) | null = null;
  public onstop: (() => void) | null = null;
  public onerror: (() => void) | null = null;

  constructor(_stream: MediaStream, options?: MediaRecorderOptions) {
    this.mimeType = options?.mimeType || 'audio/webm';
  }

  start() {
    this.state = 'recording';
  }

  stop() {
    this.state = 'inactive';
    if (this.ondataavailable) {
      const blob = new Blob(['test'], { type: this.mimeType });
      this.ondataavailable({ data: blob } as BlobEvent);
    }
    this.onstop?.();
  }
}

const mockTrack = { stop: vi.fn() };
const mockStream = { getTracks: () => [mockTrack] } as unknown as MediaStream;

beforeEach(() => {
  Object.defineProperty(navigator, 'mediaDevices', {
    value: {
      getUserMedia: vi.fn().mockResolvedValue(mockStream),
    },
    configurable: true,
  });

  Object.defineProperty(URL, 'createObjectURL', {
    value: vi.fn(() => 'blob:mock'),
    configurable: true,
  });

  Object.defineProperty(URL, 'revokeObjectURL', {
    value: vi.fn(),
    configurable: true,
  });

  vi.stubGlobal('MediaRecorder', MockMediaRecorder as unknown as typeof MediaRecorder);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('useAudioRecorder', () => {
  it('starts and stops recording with a blob', async () => {
    const { result } = renderHook(() => useAudioRecorder({ maxDuration: 120 }));

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.isRecording).toBe(true);

    act(() => {
      result.current.stopRecording();
    });

    await waitFor(() => expect(result.current.audioBlob).not.toBeNull());
    expect(result.current.isRecording).toBe(false);
  });

  it('reports permission denied errors', async () => {
    const mockGetUserMedia = vi.fn().mockRejectedValue(new Error('Permission denied'));
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: mockGetUserMedia },
      configurable: true,
    });

    const { result } = renderHook(() => useAudioRecorder());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.error).toBe('Microphone permission denied');
  });

  it('auto-stops after max duration', async () => {
    vi.useFakeTimers();

    const { result } = renderHook(() => useAudioRecorder({ maxDuration: 1 }));

    await act(async () => {
      await result.current.startRecording();
    });

    await act(async () => {
      vi.advanceTimersByTime(1200);
    });

    expect(result.current.isRecording).toBe(false);

    vi.useRealTimers();
  });
});
