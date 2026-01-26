import { NextRequest } from 'next/server';

export const runtime = 'nodejs';

const GATEWAY_URL = (process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8000').replace(/\/+$/, '');

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ request_id: string }> }
) {
  const { request_id } = await context.params;
  const { searchParams } = new URL(request.url);
  const baseline = searchParams.get('baseline');

  const upstreamUrl = new URL(`${GATEWAY_URL}/api/debug/stream/${request_id}`);
  if (baseline) {
    upstreamUrl.searchParams.set('baseline', baseline);
  }

  const preReleaseHeader = request.headers.get('x-prereleasepassword');
  const upstreamHeaders: Record<string, string> = {
    Accept: 'text/event-stream',
  };
  if (preReleaseHeader) {
    upstreamHeaders['X-PreReleasePassword'] = preReleaseHeader;
  }

  const upstreamResponse = await fetch(upstreamUrl.toString(), {
    headers: upstreamHeaders,
    cache: 'no-store',
  });

  if (!upstreamResponse.ok) {
    const errorText = await upstreamResponse.text();
    return new Response(errorText, {
      status: upstreamResponse.status,
      headers: {
        'Content-Type': upstreamResponse.headers.get('Content-Type') || 'text/plain',
      },
    });
  }

  const headers = new Headers(upstreamResponse.headers);
  headers.set('Cache-Control', 'no-cache');
  headers.set('Connection', 'keep-alive');

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    headers,
  });
}
