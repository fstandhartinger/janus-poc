import fs from 'fs/promises';
import { createReadStream } from 'fs';
import { NextRequest, NextResponse } from 'next/server';
import { Readable } from 'stream';

import {
  resolveArtifactRoot,
  sanitizeSegment,
  safeJoin,
  resolveExtension,
  mimeTypeFromExtension,
} from '@/lib/artifact-storage';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

async function readMetadata(metaPath: string): Promise<{ mime_type?: string } | null> {
  try {
    const data = await fs.readFile(metaPath, 'utf8');
    return JSON.parse(data) as { mime_type?: string };
  } catch {
    return null;
  }
}

type ArtifactRouteParams = { path?: string[] };

function parseRangeHeader(
  rangeHeader: string,
  sizeBytes: number
): { start: number; end: number } | null {
  const trimmed = rangeHeader.trim();
  const match = /^bytes=(\d*)-(\d*)$/i.exec(trimmed);
  if (!match) {
    return null;
  }
  const startRaw = match[1] || '';
  const endRaw = match[2] || '';
  if (!startRaw && !endRaw) {
    return null;
  }

  // Suffix range: bytes=-500
  if (!startRaw) {
    const suffixLength = Number(endRaw);
    if (!Number.isFinite(suffixLength) || suffixLength <= 0) {
      return null;
    }
    const start = Math.max(0, sizeBytes - suffixLength);
    return { start, end: sizeBytes - 1 };
  }

  const start = Number(startRaw);
  if (!Number.isFinite(start) || start < 0) {
    return null;
  }
  if (start >= sizeBytes) {
    return null;
  }

  // Open-ended range: bytes=500-
  if (!endRaw) {
    return { start, end: sizeBytes - 1 };
  }

  let end = Number(endRaw);
  if (!Number.isFinite(end) || end < start) {
    return null;
  }
  end = Math.min(end, sizeBytes - 1);
  return { start, end };
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<ArtifactRouteParams> }
) {
  const params = await context.params;
  const segments = Array.isArray(params?.path) ? params.path : [];
  if (segments.length < 2) {
    return NextResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
  }

  const safeSegments = segments.map((segment) => sanitizeSegment(segment));
  const root = await resolveArtifactRoot();
  let filePath: string;
  try {
    filePath = safeJoin(root, ...safeSegments);
  } catch {
    return NextResponse.json({ error: 'INVALID_PATH' }, { status: 400 });
  }

  try {
    const stats = await fs.stat(filePath);
    const metadata = await readMetadata(`${filePath}.json`);
    const fallbackExtension = resolveExtension(filePath);
    const inferredType = mimeTypeFromExtension(fallbackExtension);
    const contentType = metadata?.mime_type || inferredType;

    const sizeBytes = stats.size;
    const rangeHeader = request.headers.get('range');
    const range = rangeHeader ? parseRangeHeader(rangeHeader, sizeBytes) : null;

    if (rangeHeader && !range) {
      return new NextResponse(null, {
        status: 416,
        headers: {
          'Content-Range': `bytes */${sizeBytes}`,
          'Accept-Ranges': 'bytes',
        },
      });
    }

    const headers: Record<string, string> = {
      'Content-Type': contentType || 'application/octet-stream',
      'Cache-Control': 'public, max-age=31536000, immutable',
      'Accept-Ranges': 'bytes',
    };

    // Stream the file to avoid buffering large artifacts in memory.
    if (range) {
      const { start, end } = range;
      const stream = createReadStream(filePath, { start, end });
      const body = Readable.toWeb(stream) as unknown as ReadableStream<Uint8Array>;
      headers['Content-Range'] = `bytes ${start}-${end}/${sizeBytes}`;
      headers['Content-Length'] = String(end - start + 1);
      return new NextResponse(body, { status: 206, headers });
    }

    const stream = createReadStream(filePath);
    const body = Readable.toWeb(stream) as unknown as ReadableStream<Uint8Array>;
    headers['Content-Length'] = String(sizeBytes);
    return new NextResponse(body, { status: 200, headers });
  } catch {
    return NextResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
  }
}
