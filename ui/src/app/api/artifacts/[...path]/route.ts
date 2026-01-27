import { NextResponse } from 'next/server';
import { guessMimeType, readCachedArtifact, streamFileResponse } from '@/lib/artifact-cache';

export async function GET(_request: Request, context: { params: { path?: string[] } }) {
  const segments = context.params.path || [];
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
