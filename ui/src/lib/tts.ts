/**
 * Text-to-speech helpers for assistant playback.
 */

import { GATEWAY_URL } from './api';
import { applyPreReleaseHeader } from './preRelease';

export interface TTSVoice {
  id: string;
  name: string;
  gender: 'male' | 'female';
  accent: 'american' | 'british';
}

export const VOICES: TTSVoice[] = [
  { id: 'af_sky', name: 'Sky', gender: 'female', accent: 'american' },
  { id: 'af_bella', name: 'Bella', gender: 'female', accent: 'american' },
  { id: 'af_sarah', name: 'Sarah', gender: 'female', accent: 'american' },
  { id: 'af_nicole', name: 'Nicole', gender: 'female', accent: 'american' },
  { id: 'am_adam', name: 'Adam', gender: 'male', accent: 'american' },
  { id: 'am_michael', name: 'Michael', gender: 'male', accent: 'american' },
  { id: 'bf_emma', name: 'Emma', gender: 'female', accent: 'british' },
  { id: 'bf_isabella', name: 'Isabella', gender: 'female', accent: 'british' },
  { id: 'bm_george', name: 'George', gender: 'male', accent: 'british' },
  { id: 'bm_lewis', name: 'Lewis', gender: 'male', accent: 'british' },
];

export const DEFAULT_VOICE = 'af_sky';

const TTS_ENDPOINT = 'https://chutes-kokoro.chutes.ai/speak';
const TTS_PROXY_ENDPOINT = `${GATEWAY_URL}/api/tts`;

// Audio cache to avoid re-generating
const audioCache = new Map<string, string>();

function toBase64(input: string): string {
  if (typeof btoa === 'function') {
    const bytes = new TextEncoder().encode(input);
    let binary = '';
    bytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return btoa(binary);
  }
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(input, 'utf-8').toString('base64');
  }
  return input;
}

function getCacheKey(text: string, voice: string, speed: number): string {
  const hash = `${text.slice(0, 100)}${text.length}${voice}${speed}`;
  return toBase64(hash).slice(0, 32);
}

export async function generateSpeech(
  text: string,
  voice: string = DEFAULT_VOICE,
  speed: number = 1.0
): Promise<string> {
  const cacheKey = getCacheKey(text, voice, speed);

  // Return cached audio URL if available
  if (audioCache.has(cacheKey)) {
    return audioCache.get(cacheKey)!;
  }

  // Strip markdown formatting for cleaner speech
  const cleanText = stripMarkdown(text);
  const apiKey = process.env.NEXT_PUBLIC_CHUTES_API_KEY;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }

  const endpoint = apiKey ? TTS_ENDPOINT : TTS_PROXY_ENDPOINT;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: applyPreReleaseHeader(headers),
    body: JSON.stringify({
      text: cleanText,
      voice,
      speed,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    const detail = errorText || response.statusText || String(response.status);
    throw new Error(`TTS failed: ${detail}`);
  }

  // Convert audio buffer to blob URL
  const audioBuffer = await response.arrayBuffer();
  const blob = new Blob([audioBuffer], { type: 'audio/wav' });
  const audioUrl = URL.createObjectURL(blob);

  // Cache for replay
  audioCache.set(cacheKey, audioUrl);

  return audioUrl;
}

function stripMarkdown(text: string): string {
  return text
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, 'code block')
    // Remove inline code
    .replace(/`([^`]+)`/g, '$1')
    // Remove images
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, 'image: $1')
    // Remove links but keep text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove bold/italic
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    // Remove headers
    .replace(/^#{1,6}\s+/gm, '')
    // Remove horizontal rules
    .replace(/^[-*_]{3,}$/gm, '')
    // Remove list markers
    .replace(/^[\s]*[-*+]\s+/gm, '')
    .replace(/^[\s]*\d+\.\s+/gm, '')
    // Clean up extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function clearAudioCache(): void {
  // Revoke all blob URLs to free memory
  audioCache.forEach((url) => URL.revokeObjectURL(url));
  audioCache.clear();
}
