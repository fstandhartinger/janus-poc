import { NextRequest, NextResponse } from 'next/server';
import { OAUTH_CONFIG, assertOAuthConfig } from '@/lib/auth/config';
import { unsealState } from '@/lib/auth/pkce';
import { isOAuthConfigError, toOAuthConfigErrorResponse } from '@/lib/auth/errors';
import { createAuthSession, getSessionCookieOptions } from '@/lib/auth/session';

export const runtime = 'nodejs';

type TokenResponse = {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
};

type UserInfoResponse = {
  sub?: string;
  username?: string;
  preferred_username?: string;
};

const redirectToError = (request: NextRequest, error: string) =>
  NextResponse.redirect(new URL(`/auth/error?error=${encodeURIComponent(error)}`, request.nextUrl.origin));

export async function GET(request: NextRequest) {
  try {
    assertOAuthConfig();
  } catch (error) {
    if (isOAuthConfigError(error)) {
      return NextResponse.json(toOAuthConfigErrorResponse(error), { status: 500 });
    }
    return NextResponse.json(
      { error: 'OAUTH_CALLBACK_FAILED', message: 'OAuth configuration is invalid' },
      { status: 500 }
    );
  }

  const { searchParams } = request.nextUrl;
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');

  if (error) {
    return redirectToError(request, error);
  }

  if (!code || !state) {
    return redirectToError(request, 'missing_code');
  }

  const sealedState = request.cookies.get('oauth_state')?.value;

  let storedState: Awaited<ReturnType<typeof unsealState>>;
  try {
    storedState = await unsealState(sealedState);
  } catch (error) {
    if (isOAuthConfigError(error)) {
      return NextResponse.json(toOAuthConfigErrorResponse(error), { status: 500 });
    }
    return redirectToError(request, 'invalid_state');
  }

  if (state !== storedState.state) {
    return redirectToError(request, 'invalid_state');
  }

  const tokenBody = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    redirect_uri: OAUTH_CONFIG.redirectUri,
    client_id: OAUTH_CONFIG.clientId,
    code_verifier: storedState.codeVerifier,
  });
  if (OAUTH_CONFIG.clientSecret) {
    tokenBody.set('client_secret', OAUTH_CONFIG.clientSecret);
  }

  const tokenResponse = await fetch(OAUTH_CONFIG.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: tokenBody,
  });

  if (!tokenResponse.ok) {
    return redirectToError(request, 'token_exchange_failed');
  }

  const tokens = (await tokenResponse.json()) as TokenResponse;
  if (!tokens.access_token || !tokens.expires_in) {
    return redirectToError(request, 'token_payload_invalid');
  }

  const userInfoResponse = await fetch(OAUTH_CONFIG.userInfoEndpoint, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });

  if (!userInfoResponse.ok) {
    return redirectToError(request, 'userinfo_failed');
  }

  const userInfo = (await userInfoResponse.json()) as UserInfoResponse;
  if (!userInfo.sub) {
    return redirectToError(request, 'userinfo_invalid');
  }

  let cookieValue: string;
  try {
    ({ cookieValue } = createAuthSession({
      userId: userInfo.sub,
      username: userInfo.username || userInfo.preferred_username,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      expiresAt: Date.now() + tokens.expires_in * 1000,
    }));
  } catch (error) {
    if (isOAuthConfigError(error)) {
      return NextResponse.json(toOAuthConfigErrorResponse(error), { status: 500 });
    }
    return redirectToError(request, 'session_failed');
  }

  const response = NextResponse.redirect(storedState.returnTo || '/chat');
  response.cookies.delete('oauth_state');
  response.cookies.set('auth_session', cookieValue, getSessionCookieOptions());

  return response;
}
