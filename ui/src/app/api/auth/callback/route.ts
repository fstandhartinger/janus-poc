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

const resolveAppOrigin = (request: NextRequest): string => {
  // Match the origin resolution used in the login route so callbacks that
  // redirect back into the app always land on the public hostname rather than
  // the internal Render bind address (e.g. `https://localhost:10000`).
  const forwardedHost =
    request.headers.get('x-forwarded-host') || request.headers.get('host') || '';
  const forwardedProto = request.headers.get('x-forwarded-proto') || 'https';
  if (forwardedHost && !forwardedHost.startsWith('localhost')) {
    try {
      return new URL(`${forwardedProto}://${forwardedHost}`).origin;
    } catch {
      // ignore and fall through
    }
  }
  if (OAUTH_CONFIG.redirectUri) {
    try {
      return new URL(OAUTH_CONFIG.redirectUri).origin;
    } catch {
      // ignore and fall through
    }
  }
  return request.nextUrl.origin;
};

const redirectToError = (request: NextRequest, error: string) =>
  NextResponse.redirect(
    new URL(`/auth/error?error=${encodeURIComponent(error)}`, resolveAppOrigin(request))
  );

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

  const appOrigin = resolveAppOrigin(request);
  const returnToTarget = (() => {
    if (!storedState.returnTo) {
      return new URL('/chat', appOrigin).toString();
    }
    try {
      const url = new URL(storedState.returnTo, appOrigin);
      const hostname = url.hostname.toLowerCase();
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        // Sealed state was created before the origin fix — rewrite onto the
        // current public origin so we never bounce users into the Render
        // container address.
        return new URL(url.pathname + url.search + url.hash, appOrigin).toString();
      }
      return url.toString();
    } catch {
      return new URL('/chat', appOrigin).toString();
    }
  })();
  const response = NextResponse.redirect(returnToTarget);
  response.cookies.delete('oauth_state');
  response.cookies.set('auth_session', cookieValue, getSessionCookieOptions());

  return response;
}
