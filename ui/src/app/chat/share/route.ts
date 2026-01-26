import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const redirectUrl = new URL('/chat/share/preview', request.url);
  redirectUrl.search = new URL(request.url).search;
  return NextResponse.redirect(redirectUrl, 303);
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const title = formData.get('title');
  const text = formData.get('text');
  const url = formData.get('url');

  const redirectUrl = new URL('/chat/share/preview', request.url);
  const params = new URLSearchParams();

  if (title) params.set('title', String(title));
  if (text) params.set('text', String(text));
  if (url) params.set('url', String(url));

  redirectUrl.search = params.toString();

  return NextResponse.redirect(redirectUrl, 303);
}
