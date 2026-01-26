import { NextRequest, NextResponse } from 'next/server';
import { PRE_RELEASE_HEADER } from '@/lib/preRelease';

export const runtime = 'nodejs';

const COOKIE_NAME = 'janus_pre_release_pwd';

export async function POST(request: NextRequest) {
  const expected = process.env.CHUTES_JANUS_PRE_RELEASE_PWD;
  if (!expected) {
    return NextResponse.json({ ok: true, message: 'Pre-release password not configured' });
  }

  const provided = request.headers.get(PRE_RELEASE_HEADER.toLowerCase());
  if (!provided || provided !== expected) {
    return NextResponse.json({ ok: false, error: 'INVALID_PASSWORD' }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(COOKIE_NAME, provided, {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    secure: process.env.NODE_ENV === 'production',
  });
  return response;
}
