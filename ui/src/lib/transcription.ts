import { GATEWAY_URL } from './api';

const WHISPER_ENDPOINT = 'https://chutes-whisper-large-v3.chutes.ai/transcribe';
const DEFAULT_MODEL = 'whisper-1';

interface TranscriptionOptions {
  language?: string | null;
}

interface TranscriptionResult {
  text: string;
  language?: string;
  duration?: number;
}

interface TranscriptionErrorDetail {
  error: string;
  code: string;
  recoverable: boolean;
  suggestion?: string;
}

export class TranscriptionFailedError extends Error {
  readonly code: string;
  readonly recoverable: boolean;
  readonly suggestion?: string;

  constructor(
    message: string,
    code: string = 'UNKNOWN',
    recoverable: boolean = true,
    suggestion?: string
  ) {
    super(message);
    this.name = 'TranscriptionFailedError';
    this.code = code;
    this.recoverable = recoverable;
    this.suggestion = suggestion;
  }
}

export async function transcribeAudio(
  audioBlob: Blob,
  options: TranscriptionOptions = {}
): Promise<TranscriptionResult> {
  const apiKey = process.env.NEXT_PUBLIC_CHUTES_API_KEY;
  if (!apiKey) {
    throw new TranscriptionFailedError(
      'Chutes API key not configured',
      'API_KEY_MISSING',
      false,
      'Please type your message instead'
    );
  }

  const formData = buildTranscriptionFormData(audioBlob, options);

  const response = await fetch(WHISPER_ENDPOINT, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new TranscriptionFailedError(
      `Transcription failed: ${error}`,
      'DIRECT_API_ERROR',
      true,
      'Please try again'
    );
  }

  const result = await response.json();

  return {
    text: result.text || result.transcription || '',
    language: result.language,
    duration: result.duration,
  };
}

export async function transcribeViaGateway(
  audioBlob: Blob,
  options: TranscriptionOptions = {}
): Promise<TranscriptionResult> {
  const formData = buildTranscriptionFormData(audioBlob, options);

  const response = await fetch(`${GATEWAY_URL}/api/transcribe`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorData: TranscriptionErrorDetail;

    try {
      const data = await response.json();
      errorData = data.detail || data;
    } catch {
      errorData = {
        error: 'Transcription failed',
        code: 'UNKNOWN',
        recoverable: true,
        suggestion: 'Please try again',
      };
    }

    throw new TranscriptionFailedError(
      errorData.error || 'Transcription failed',
      errorData.code || 'UNKNOWN',
      errorData.recoverable ?? true,
      errorData.suggestion
    );
  }

  return response.json();
}

export interface TranscriptionHealthStatus {
  available: boolean;
  endpoint: string;
  api_key_configured: boolean;
  error?: string;
}

export async function checkTranscriptionHealth(): Promise<TranscriptionHealthStatus> {
  try {
    const response = await fetch(`${GATEWAY_URL}/api/transcribe/health`);
    if (!response.ok) {
      return {
        available: false,
        endpoint: '',
        api_key_configured: false,
        error: 'Health check failed',
      };
    }
    return response.json();
  } catch (e) {
    return {
      available: false,
      endpoint: '',
      api_key_configured: false,
      error: e instanceof Error ? e.message : 'Unknown error',
    };
  }
}

function buildTranscriptionFormData(audioBlob: Blob, options: TranscriptionOptions): FormData {
  const formData = new FormData();
  const extension = resolveAudioExtension(audioBlob.type);

  formData.append('file', audioBlob, `recording.${extension}`);
  formData.append('model', DEFAULT_MODEL);

  if (options.language) {
    formData.append('language', options.language);
  }

  return formData;
}

function resolveAudioExtension(mimeType: string | null | undefined): string {
  if (!mimeType) {
    return 'webm';
  }
  if (mimeType.includes('webm')) {
    return 'webm';
  }
  if (mimeType.includes('mp4')) {
    return 'm4a';
  }
  if (mimeType.includes('ogg')) {
    return 'ogg';
  }
  if (mimeType.includes('wav')) {
    return 'wav';
  }
  return 'webm';
}

export type { TranscriptionOptions, TranscriptionResult, TranscriptionErrorDetail };
