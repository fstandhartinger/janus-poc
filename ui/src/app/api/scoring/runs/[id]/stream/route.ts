export const runtime = 'nodejs';

import { SCORING_SERVICE_URL, SCORING_UNAVAILABLE_BODY } from '@/lib/scoringProxy';

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;

  let upstream: Response;
  try {
    upstream = await fetch(`${SCORING_SERVICE_URL}/api/runs/${id}/stream`, {
      headers: {
        Accept: 'text/event-stream',
      },
    });
  } catch {
    return Response.json(SCORING_UNAVAILABLE_BODY, { status: 503 });
  }

  if (!upstream.ok || !upstream.body) {
    return new Response(await upstream.text(), { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
    },
  });
}
