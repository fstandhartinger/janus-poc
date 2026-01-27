import fs from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import path from 'node:path';
import type { Artifact } from '@/types/chat';

const PRIMARY_ROOT = process.env.JANUS_ARTIFACT_CACHE_DIR || '/var/data/janus-artifacts';
const FALLBACK_ROOT = '/tmp/janus-artifacts';

const MIME_EXTENSION: Record<string, string> = {
  'image/jpeg': '.jpg',
  'image/png': '.png',
  'image/webp': '.webp',
  'image/gif': '.gif',
  'image/svg+xml': '.svg',
  'audio/mpeg': '.mp3',
  'audio/wav': '.wav',
  'audio/ogg': '.ogg',
  'video/mp4': '.mp4',
  'video/webm': '.webm',
  'application/pdf': '.pdf',
};

export type CachedArtifact = {
  url: string;
  path: string;
  size?: number;
};

function sanitizeSegment(segment: string): string {
  return segment.replace(/[^a-zA-Z0-9._-]/g, '_');
}

async function resolveCacheRoot(): Promise<string> {
  try {
    await fs.mkdir(PRIMARY_ROOT, { recursive: true });
    return PRIMARY_ROOT;
  } catch {
    await fs.mkdir(FALLBACK_ROOT, { recursive: true });
    return FALLBACK_ROOT;
  }
}

function ensureExtension(name: string, mimeType?: string): string {
  const hasExt = path.extname(name);
  if (hasExt) return name;
  const ext = (mimeType && MIME_EXTENSION[mimeType]) || '';
  return `${name}${ext}`;
}

export async function cacheArtifactFile(
  chatId: string,
  artifact: Artifact
): Promise<CachedArtifact | null> {
  if (!artifact.url || artifact.url.startsWith('data:')) {
    return null;
  }

  const root = await resolveCacheRoot();
  const safeChatId = sanitizeSegment(chatId);
  const display = sanitizeSegment(artifact.display_name || artifact.id || 'artifact');
  const fileName = ensureExtension(`${artifact.id}-${display}`, artifact.mime_type);
  const dir = path.join(root, safeChatId);
  const filePath = path.join(dir, fileName);

  await fs.mkdir(dir, { recursive: true });

  try {
    await fs.access(filePath);
    return { url: `/api/artifacts/${safeChatId}/${fileName}`, path: filePath };
  } catch {
    // continue to download
  }

  const response = await fetch(artifact.url);
  if (!response.ok || !response.body) {
    throw new Error(`Failed to fetch artifact: ${response.status}`);
  }

  const arrayBuffer = await response.arrayBuffer();
  await fs.writeFile(filePath, Buffer.from(arrayBuffer));
  const stats = await fs.stat(filePath);

  return { url: `/api/artifacts/${safeChatId}/${fileName}`, path: filePath, size: stats.size };
}

export async function readCachedArtifact(pathSegments: string[]): Promise<{ path: string; size: number } | null> {
  const root = await resolveCacheRoot();
  const safeSegments = pathSegments.map(sanitizeSegment);
  const resolved = path.resolve(root, ...safeSegments);
  if (!resolved.startsWith(root)) {
    return null;
  }
  try {
    const stats = await fs.stat(resolved);
    if (!stats.isFile()) {
      return null;
    }
    return { path: resolved, size: stats.size };
  } catch {
    return null;
  }
}

export function streamFileResponse(filePath: string, size: number, mimeType?: string): Response {
  const nodeStream = createReadStream(filePath);
  const webStream = Readable.toWeb(nodeStream) as ReadableStream;
  const headers = new Headers();
  if (mimeType) {
    headers.set('Content-Type', mimeType);
  }
  headers.set('Content-Length', size.toString());
  headers.set('Cache-Control', 'public, max-age=31536000, immutable');
  return new Response(webStream, { headers });
}

export function guessMimeType(filePath: string): string | undefined {
  const ext = path.extname(filePath).toLowerCase();
  const entry = Object.entries(MIME_EXTENSION).find(([, value]) => value === ext);
  return entry?.[0];
}
