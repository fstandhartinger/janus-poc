import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs/promises';

import { resolveArtifactRoot, sanitizeSegment, resolveExtension, safeJoin } from '@/lib/artifact-storage';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type ArtifactPayload = {
  id: string;
  type: string;
  mime_type: string;
  display_name: string;
  size_bytes?: number;
  url: string;
  sha256?: string;
};

export async function POST(request: NextRequest) {
  let body: { chatId?: string; artifact?: ArtifactPayload } | null = null;
  try {
    body = (await request.json()) as { chatId?: string; artifact?: ArtifactPayload };
  } catch {
    body = null;
  }

  const chatId = body?.chatId;
  const artifact = body?.artifact;

  if (!chatId || !artifact || typeof artifact.url !== 'string') {
    return NextResponse.json({ error: 'INVALID_REQUEST' }, { status: 400 });
  }

  if (!artifact.url.startsWith('http')) {
    return NextResponse.json({ url: artifact.url });
  }

  const root = await resolveArtifactRoot();
  const safeChatId = sanitizeSegment(chatId);
  const extension = resolveExtension(artifact.display_name, artifact.mime_type);
  const baseName = sanitizeSegment(artifact.id || artifact.display_name || 'artifact');
  const filename = `${baseName}${extension}`;
  const folder = safeJoin(root, safeChatId);
  const filePath = safeJoin(folder, filename);
  const metaPath = `${filePath}.json`;

  await fs.mkdir(folder, { recursive: true });

  try {
    await fs.access(filePath);
  } catch {
    const response = await fetch(artifact.url);
    if (!response.ok) {
      return NextResponse.json({ url: artifact.url });
    }
    const buffer = Buffer.from(await response.arrayBuffer());
    await fs.writeFile(filePath, buffer);
    await fs.writeFile(
      metaPath,
      JSON.stringify(
        {
          id: artifact.id,
          display_name: artifact.display_name,
          mime_type: artifact.mime_type,
          size_bytes: artifact.size_bytes ?? buffer.length,
          sha256: artifact.sha256,
          source_url: artifact.url,
        },
        null,
        2
      )
    );
  }

  return NextResponse.json({ url: `/api/artifacts/${safeChatId}/${filename}` });
}
