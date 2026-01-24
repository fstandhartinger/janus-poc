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

export async function transcribeAudio(
  audioBlob: Blob,
  options: TranscriptionOptions = {}
): Promise<TranscriptionResult> {
  const base64 = await blobToBase64(audioBlob);

  const apiKey = process.env.NEXT_PUBLIC_CHUTES_API_KEY;
  if (!apiKey) {
    throw new Error('Chutes API key not configured');
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
    throw new Error(`Transcription failed: ${error}`);
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
    throw new Error('Transcription failed');
  }

  return response.json();
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

export type { TranscriptionOptions, TranscriptionResult };
