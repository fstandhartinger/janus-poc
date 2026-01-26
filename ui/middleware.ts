import { NextRequest, NextResponse } from 'next/server';

const PRE_RELEASE_HEADER = 'x-prereleasepassword';
const PRE_RELEASE_COOKIE = 'janus_pre_release_pwd';

function isValidPassword(request: NextRequest, password: string): boolean {
  const headerValue = request.headers.get(PRE_RELEASE_HEADER);
  if (headerValue && headerValue === password) {
    return true;
  }
  const cookieValue = request.cookies.get(PRE_RELEASE_COOKIE)?.value;
  return Boolean(cookieValue && cookieValue === password);
}

export function middleware(request: NextRequest) {
  const password = process.env.CHUTES_JANUS_PRE_RELEASE_PWD;
  if (!password) {
    return NextResponse.next();
  }
  if (request.method === 'OPTIONS') {
    return NextResponse.next();
  }
  if (isValidPassword(request, password)) {
    return NextResponse.next();
  }
  return NextResponse.json(
    {
      error: 'PRE_RELEASE_PASSWORD_REQUIRED',
      message: 'Pre-release password required',
    },
    { status: 401 }
  );
}

export const config = {
  matcher: ['/api/:path*'],
};
