import { NextRequest, NextResponse } from 'next/server';
import { checkIpRateLimit, getClientIp, incrementIpChatCount } from '@/lib/rateLimit';
import { clearSessionCookieHeader, getAuthSession } from '@/lib/auth/session';

export const runtime = 'nodejs';

const GATEWAY_URL = (process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8000').replace(/\/+$/, '');

export async function POST(request: NextRequest) {
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: 'INVALID_REQUEST', message: 'Invalid JSON payload' }, { status: 400 });
  }

  const authResult = await getAuthSession(request);
  const session = authResult.session;

  if (!session) {
    const clientIp = getClientIp(request);
    const { allowed, remaining, used } = await checkIpRateLimit(clientIp);

    if (!allowed) {
      const response = NextResponse.json(
        {
          error: 'RATE_LIMIT_EXCEEDED',
          message: 'Free chat limit reached',
          details: {
            used,
            remaining,
            limit: 5,
            requiresLogin: true,
          },
        },
        { status: 429 }
      );

      if (authResult.clearCookie) {
        response.headers.append('Set-Cookie', clearSessionCookieHeader());
      }

      return response;
    }

    await incrementIpChatCount(clientIp);
  }

  if (session?.userId) {
    payload.user_id = session.userId;
  }

  if (session?.accessToken) {
    payload.chutes_access_token = session.accessToken;
  }

  const preReleaseHeader = request.headers.get('x-prereleasepassword');
  const upstreamHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  if (preReleaseHeader) {
    upstreamHeaders['X-PreReleasePassword'] = preReleaseHeader;
  }

  const upstreamResponse = await fetch(`${GATEWAY_URL}/v1/chat/completions/arena`, {
    method: 'POST',
    headers: upstreamHeaders,
    body: JSON.stringify(payload),
    cache: 'no-store',
  });

  const responsePayload = await upstreamResponse.text();
  const response = new NextResponse(responsePayload, {
    status: upstreamResponse.status,
    headers: {
      'Content-Type': upstreamResponse.headers.get('Content-Type') || 'application/json',
    },
  });

  if (authResult.setCookie) {
    response.headers.append('Set-Cookie', authResult.setCookie);
  }
  if (authResult.clearCookie) {
    response.headers.append('Set-Cookie', clearSessionCookieHeader());
  }

  return response;
}
