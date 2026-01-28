import fs from 'fs/promises';
import { NextRequest, NextResponse } from 'next/server';

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

export async function GET(
  _request: NextRequest,
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
    const fileBuffer = await fs.readFile(filePath);
    const metadata = await readMetadata(`${filePath}.json`);
    const fallbackExtension = resolveExtension(filePath);
    const inferredType = mimeTypeFromExtension(fallbackExtension);
    const contentType = metadata?.mime_type || inferredType;
    return new NextResponse(fileBuffer, {
      headers: {
        'Content-Type': contentType || 'application/octet-stream',
        'Content-Length': String(fileBuffer.length),
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });
  } catch {
    return NextResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
  }
}
