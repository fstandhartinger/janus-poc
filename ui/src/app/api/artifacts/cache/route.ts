import { NextResponse } from 'next/server';
import type { Artifact } from '@/types/chat';
import { cacheArtifactFile } from '@/lib/artifact-cache';

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { chatId?: string; artifact?: Artifact };
    const chatId = body.chatId;
    const artifact = body.artifact;

    if (!chatId || !artifact?.url) {
      return NextResponse.json({ error: 'Missing chatId or artifact' }, { status: 400 });
    }

    if (artifact.url.startsWith('data:')) {
      return NextResponse.json({ url: artifact.url, cached: false });
    }

    const cached = await cacheArtifactFile(chatId, artifact);
    if (!cached) {
      return NextResponse.json({ url: artifact.url, cached: false });
    }

    return NextResponse.json({ url: cached.url, cached: true, size: cached.size });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
