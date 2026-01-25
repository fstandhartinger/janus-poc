import { NextRequest, NextResponse } from 'next/server';
import { generatePKCE, generateState, sealState } from '@/lib/auth/pkce';
import { OAUTH_CONFIG, assertOAuthConfig } from '@/lib/auth/config';

export const runtime = 'nodejs';

const resolveReturnTo = (request: NextRequest, returnToParam: string | null) => {
  const fallback = new URL('/chat', request.nextUrl.origin).toString();
  if (!returnToParam) {
    return fallback;
  }
  try {
    const url = new URL(returnToParam, request.nextUrl.origin);
    if (url.origin !== request.nextUrl.origin) {
      return fallback;
    }
    return url.toString();
  } catch {
    return fallback;
  }
};

export async function GET(request: NextRequest) {
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
}
