import fs from 'fs/promises';
import path from 'path';

const PRIMARY_ROOT =
  process.env.JANUS_UI_ARTIFACT_ROOT ||
  process.env.JANUS_ARTIFACT_ROOT ||
  '/var/data/janus-artifacts';
const FALLBACK_ROOT = path.join(process.cwd(), '.janus-artifacts');

let resolvedRoot: string | null = null;

async function ensureDirectory(target: string): Promise<boolean> {
  try {
    await fs.mkdir(target, { recursive: true });
    return true;
  } catch {
    return false;
  }
}

export async function resolveArtifactRoot(): Promise<string> {
  if (resolvedRoot) return resolvedRoot;
  if (await ensureDirectory(PRIMARY_ROOT)) {
    resolvedRoot = PRIMARY_ROOT;
    return resolvedRoot;
  }
  await ensureDirectory(FALLBACK_ROOT);
  resolvedRoot = FALLBACK_ROOT;
  return resolvedRoot;
}

export function sanitizeSegment(value: string): string {
  return value.replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 160) || 'artifact';
}

const MIME_EXTENSION_MAP: Record<string, string> = {
  'image/jpeg': '.jpg',
  'image/jpg': '.jpg',
  'image/png': '.png',
  'image/webp': '.webp',
  'image/gif': '.gif',
  'image/svg+xml': '.svg',
  'application/pdf': '.pdf',
  'application/json': '.json',
  'text/plain': '.txt',
  'text/markdown': '.md',
};

const EXTENSION_MIME_MAP: Record<string, string> = Object.entries(MIME_EXTENSION_MAP).reduce(
  (acc, [mime, ext]) => {
    acc[ext] = mime;
    return acc;
  },
  {} as Record<string, string>
);

export function resolveExtension(displayName?: string, mimeType?: string): string {
  if (displayName) {
    const ext = path.extname(displayName);
    if (ext) {
      return ext;
    }
  }
  if (mimeType && MIME_EXTENSION_MAP[mimeType]) {
    return MIME_EXTENSION_MAP[mimeType];
  }
  return '.bin';
}

export function mimeTypeFromExtension(extension: string): string | undefined {
  return EXTENSION_MIME_MAP[extension.toLowerCase()];
}

export function safeJoin(root: string, ...segments: string[]): string {
  const target = path.resolve(root, path.join(...segments));
  const normalizedRoot = root.endsWith(path.sep) ? root : `${root}${path.sep}`;
  if (!target.startsWith(normalizedRoot)) {
    throw new Error('Invalid artifact path');
  }
  return target;
}
