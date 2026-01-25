export interface ParsedAudio {
  url: string;
  type: 'speech' | 'music' | 'sound';
  title?: string;
  metadata?: Record<string, unknown>;
}

const AUDIO_BLOCK_REGEX = /:::audio\[([^\]]*)\]\s*\r?\n(data:audio\/[^;]+;base64,[A-Za-z0-9+/=]+)\s*\r?\n:::/g;
const INLINE_AUDIO_REGEX = /data:audio\/(wav|mp3|ogg);base64,[A-Za-z0-9+/=]+/g;

/**
 * Parse audio content from message text.
 *
 * Supports formats:
 * - data:audio/wav;base64,...
 * - :::audio[type=music,title=My Song]
 *   data:audio/wav;base64,...
 *   :::
 */
export function parseAudioContent(content: string): ParsedAudio[] {
  const results: Array<{ index: number; item: ParsedAudio }> = [];
  const blockRanges: Array<[number, number]> = [];
  let match: RegExpExecArray | null;

  while ((match = AUDIO_BLOCK_REGEX.exec(content)) !== null) {
    const attrs = parseAttributes(match[1]);
    const type = normalizeAudioType(attrs.type);
    const title = typeof attrs.title === 'string' ? attrs.title : undefined;
    results.push({
      index: match.index,
      item: {
        url: match[2],
        type,
        title,
        metadata: attrs,
      },
    });
    blockRanges.push([match.index, match.index + match[0].length]);
  }

  while ((match = INLINE_AUDIO_REGEX.exec(content)) !== null) {
    if (isInsideRange(match.index, blockRanges)) {
      continue;
    }

    const contextBefore = content.slice(Math.max(0, match.index - 100), match.index).toLowerCase();
    let type: 'speech' | 'music' | 'sound' = 'sound';

    if (contextBefore.includes('speech') || contextBefore.includes('tts') || contextBefore.includes('spoken')) {
      type = 'speech';
    } else if (contextBefore.includes('music') || contextBefore.includes('song') || contextBefore.includes('melody')) {
      type = 'music';
    }

    results.push({
      index: match.index,
      item: {
        url: match[0],
        type,
      },
    });
  }

  return results.sort((a, b) => a.index - b.index).map((entry) => entry.item);
}

function normalizeAudioType(value: unknown): 'speech' | 'music' | 'sound' {
  if (value === 'speech' || value === 'music' || value === 'sound') {
    return value;
  }
  return 'sound';
}

function isInsideRange(index: number, ranges: Array<[number, number]>): boolean {
  return ranges.some(([start, end]) => index >= start && index < end);
}

function parseAttributes(attrString: string): Record<string, unknown> {
  const attrs: Record<string, unknown> = {};
  const regex = /(\w+)=([^,\]]+)/g;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(attrString)) !== null) {
    const key = match[1];
    const value = match[2];
    attrs[key] = coerceValue(value);
  }

  return attrs;
}

function coerceValue(value: string): string | number | boolean {
  const trimmed = value.trim();
  if (/^(true|false)$/i.test(trimmed)) {
    return trimmed.toLowerCase() === 'true';
  }
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : trimmed;
  }
  return trimmed;
}
