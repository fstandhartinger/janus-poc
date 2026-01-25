import { GATEWAY_URL } from './api';

const WHISPER_ENDPOINT = 'https://chutes-whisper-large-v3.chutes.ai/transcribe';

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
  const base64 = await blobToBase64(audioBlob);

  const apiKey = process.env.NEXT_PUBLIC_CHUTES_API_KEY;
  if (!apiKey) {
    throw new TranscriptionFailedError(
      'Chutes API key not configured',
      'API_KEY_MISSING',
      false,
      'Please type your message instead'
    );
  }

  const response = await fetch(WHISPER_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      language: options.language ?? null,
      audio_b64: base64,
    }),
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
  const base64 = await blobToBase64(audioBlob);

  const response = await fetch(`${GATEWAY_URL}/api/transcribe`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      language: options.language ?? null,
      audio_b64: base64,
    }),
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

async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      const base64Data = base64.split(',')[1];
      resolve(base64Data || '');
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

export type { TranscriptionOptions, TranscriptionResult, TranscriptionErrorDetail };
