import { NextResponse } from 'next/server';
import { clearSessionCookieHeader } from '@/lib/auth/session';

export const runtime = 'nodejs';

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.headers.append('Set-Cookie', clearSessionCookieHeader());
  return response;
}
