import { useState, useRef, useCallback, useEffect } from 'react';

interface AudioRecorderState {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioBlob: Blob | null;
  audioUrl: string | null;
  error: string | null;
  stream: MediaStream | null;
  mimeType: string | null;
}

interface UseAudioRecorderOptions {
  maxDuration?: number;
  sampleRate?: number;
  audioBitsPerSecond?: number;
}

const DEFAULT_MAX_DURATION = 120;
const DEFAULT_SAMPLE_RATE = 16000;
const DEFAULT_BITS_PER_SECOND = 32000;

const SUPPORTED_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
  'audio/wav',
];

const initialState: AudioRecorderState = {
  isRecording: false,
  isPaused: false,
  duration: 0,
  audioBlob: null,
  audioUrl: null,
  error: null,
  stream: null,
  mimeType: null,
};

function pickMimeType(): string | null {
  if (typeof MediaRecorder === 'undefined') {
    return null;
  }

  if (typeof MediaRecorder.isTypeSupported !== 'function') {
    return null;
  }

  for (const mimeType of SUPPORTED_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }

  return null;
}

export function useAudioRecorder(options: UseAudioRecorderOptions = {}) {
  const {
    maxDuration = DEFAULT_MAX_DURATION,
    sampleRate = DEFAULT_SAMPLE_RATE,
    audioBitsPerSecond = DEFAULT_BITS_PER_SECOND,
  } = options;

  const [state, setState] = useState<AudioRecorderState>(initialState);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const discardRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearTimer();
    stopStream();
    if (state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl);
    }
    setState(initialState);
    chunksRef.current = [];
    discardRef.current = false;
  }, [clearTimer, stopStream, state.audioUrl]);

  const stopRecording = useCallback(() => {
    clearTimer();
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, [clearTimer]);

  const cancelRecording = useCallback(() => {
    discardRef.current = true;
    stopRecording();
    stopStream();
    if (state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl);
    }
    setState(initialState);
    chunksRef.current = [];
  }, [state.audioUrl, stopRecording, stopStream]);

  const startRecording = useCallback(async () => {
    if (!navigator?.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setState((prev) => ({
        ...prev,
        error: 'Audio recording is not supported in this browser',
      }));
      return;
    }

    if (state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl);
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;
      chunksRef.current = [];
      discardRef.current = false;

      const mimeType = pickMimeType();
      const options = mimeType
        ? { mimeType, audioBitsPerSecond }
        : { audioBitsPerSecond };

      let mediaRecorder: MediaRecorder;
      try {
        mediaRecorder = new MediaRecorder(stream, options);
      } catch {
        mediaRecorder = new MediaRecorder(stream);
      }

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        clearTimer();
        const shouldDiscard = discardRef.current;
        discardRef.current = false;

        stopStream();

        if (shouldDiscard) {
          chunksRef.current = [];
          setState(initialState);
          return;
        }

        const finalMimeType = mimeType || mediaRecorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(chunksRef.current, { type: finalMimeType });
        const audioUrl = URL.createObjectURL(audioBlob);

        setState((prev) => ({
          ...prev,
          isRecording: false,
          isPaused: false,
          audioBlob,
          audioUrl,
          stream: null,
          mimeType: finalMimeType,
        }));
      };

      mediaRecorder.onerror = () => {
        clearTimer();
        stopStream();
        setState((prev) => ({
          ...prev,
          isRecording: false,
          error: 'Recording failed',
        }));
      };

      mediaRecorder.start(250);

      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        const duration = Math.floor((Date.now() - startTime) / 1000);
        setState((prev) => ({ ...prev, duration }));

        if (duration >= maxDuration) {
          stopRecording();
        }
      }, 200);

      setState({
        isRecording: true,
        isPaused: false,
        duration: 0,
        audioBlob: null,
        audioUrl: null,
        error: null,
        stream,
        mimeType,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to access microphone';

      setState((prev) => ({
        ...prev,
        error: message.toLowerCase().includes('permission')
          ? 'Microphone permission denied'
          : message,
      }));
    }
  }, [audioBitsPerSecond, maxDuration, sampleRate, state.audioUrl, stopRecording, clearTimer, stopStream]);

  useEffect(() => {
    return () => {
      clearTimer();
      stopStream();
      if (state.audioUrl) {
        URL.revokeObjectURL(state.audioUrl);
      }
    };
  }, [clearTimer, stopStream, state.audioUrl]);

  return {
    ...state,
    startRecording,
    stopRecording,
    cancelRecording,
    reset,
  };
}
