import { NextRequest, NextResponse } from 'next/server';
import { guessMimeType, readCachedArtifact, streamFileResponse } from '@/lib/artifact-cache';

export async function GET(_request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const segments = path || [];
  if (segments.length === 0) {
    return NextResponse.json({ error: 'Missing artifact path' }, { status: 400 });
  }

  const cached = await readCachedArtifact(segments);
  if (!cached) {
    return NextResponse.json({ error: 'Artifact not found' }, { status: 404 });
  }

  const mimeType = guessMimeType(cached.path);
  return streamFileResponse(cached.path, cached.size, mimeType);
}
