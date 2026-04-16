import { NextRequest, NextResponse } from 'next/server';
import { generatePKCE, generateState, sealState } from '@/lib/auth/pkce';
import { OAUTH_CONFIG, assertOAuthConfig } from '@/lib/auth/config';
import { isOAuthConfigError, toOAuthConfigErrorResponse } from '@/lib/auth/errors';

export const runtime = 'nodejs';

const resolveAppOrigin = (request: NextRequest): string => {
  // Render (and most reverse proxies) forward the public host/proto via
  // X-Forwarded-* headers. `request.nextUrl.origin` on the server can resolve
  // to the internal bind address (e.g. `https://localhost:10000`) when those
  // headers aren't trusted by Next.js, so prefer explicit proxy headers and
  // fall back to the configured OAuth redirect URI origin before using the
  // request origin as a last resort.
  const forwardedHost =
    request.headers.get('x-forwarded-host') || request.headers.get('host') || '';
  const forwardedProto = request.headers.get('x-forwarded-proto') || 'https';
  if (forwardedHost && !forwardedHost.startsWith('localhost')) {
    try {
      return new URL(`${forwardedProto}://${forwardedHost}`).origin;
    } catch {
      // fall through to other strategies
    }
  }
  if (OAUTH_CONFIG.redirectUri) {
    try {
      return new URL(OAUTH_CONFIG.redirectUri).origin;
    } catch {
      // fall through to request origin
    }
  }
  return request.nextUrl.origin;
};

const resolveReturnTo = (request: NextRequest, returnToParam: string | null) => {
  const appOrigin = resolveAppOrigin(request);
  const fallback = new URL('/chat', appOrigin).toString();
  if (!returnToParam) {
    return fallback;
  }
  try {
    const url = new URL(returnToParam, appOrigin);
    if (url.origin !== appOrigin) {
      return fallback;
    }
    return url.toString();
  } catch {
    return fallback;
  }
};

const handleAuthError = (error: unknown) => {
  if (isOAuthConfigError(error)) {
    return NextResponse.json(toOAuthConfigErrorResponse(error), { status: 500 });
  }
  return NextResponse.json(
    { error: 'OAUTH_LOGIN_FAILED', message: 'Unable to initiate OAuth login' },
    { status: 500 }
  );
};

export async function GET(request: NextRequest) {
  try {
    assertOAuthConfig();

    const returnTo = resolveReturnTo(request, request.nextUrl.searchParams.get('returnTo'));
    const { codeVerifier, codeChallenge } = await generatePKCE();
    const state = generateState();

    const sealedState = await sealState({
      state,
      codeVerifier,
      returnTo,
    });

    const authorizationUrl =
      `${OAUTH_CONFIG.authorizationEndpoint}?` +
      new URLSearchParams({
        response_type: 'code',
        client_id: OAUTH_CONFIG.clientId,
        redirect_uri: OAUTH_CONFIG.redirectUri,
        scope: OAUTH_CONFIG.scopes.join(' '),
        state,
        code_challenge: codeChallenge,
        code_challenge_method: 'S256',
      }).toString();

    const response = NextResponse.redirect(authorizationUrl);
    response.cookies.set('oauth_state', sealedState, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 600,
      path: '/',
    });

    return response;
  } catch (error) {
    return handleAuthError(error);
  }
}
