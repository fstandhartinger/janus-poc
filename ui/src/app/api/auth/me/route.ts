import { NextRequest, NextResponse } from 'next/server';
import { clearSessionCookieHeader, getAuthSession } from '@/lib/auth/session';

export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  const { session, setCookie, clearCookie } = await getAuthSession(request);

  if (!session) {
    const response = NextResponse.json({ user: null }, { status: 401 });
    if (clearCookie) {
      response.headers.append('Set-Cookie', clearSessionCookieHeader());
    }
    return response;
  }

  const response = NextResponse.json({
    user: {
      id: session.userId,
      username: session.username,
    },
  });

  if (setCookie) {
    response.headers.append('Set-Cookie', setCookie);
  }

  return response;
}
