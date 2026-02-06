import { NextRequest, NextResponse } from 'next/server';
import {
  buildSessionCookieHeader,
  clearSessionCookieHeader,
  getAuthSession,
} from '@/lib/auth/session';

export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  const rawCookie = request.cookies.get('auth_session')?.value;
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

  // Sliding cookie: keep the session alive for 30 days after last successful usage.
  const cookieHeader = setCookie ?? (rawCookie ? buildSessionCookieHeader(rawCookie) : undefined);
  if (cookieHeader) response.headers.append('Set-Cookie', cookieHeader);

  return response;
}
