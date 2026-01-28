import type { Artifact } from '@/types/chat';
import { applyPreReleaseHeader } from '@/lib/preRelease';

export async function cacheArtifact(chatId: string, artifact: Artifact): Promise<Artifact> {
  if (!artifact.url || artifact.url.startsWith('data:') || artifact.url.startsWith('/api/artifacts/')) {
    return artifact;
  }

  try {
    const response = await fetch('/api/artifacts/cache', {
      method: 'POST',
      headers: applyPreReleaseHeader({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ chatId, artifact }),
      credentials: 'include',
    });
    if (!response.ok) {
      return artifact;
    }
    const data = (await response.json()) as { url?: string };
    if (data.url) {
      return { ...artifact, url: data.url };
    }
  } catch {
    // ignore cache errors
  }

  return artifact;
}
