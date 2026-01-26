import type { NextRequest } from 'next/server';
import { OAUTH_CONFIG, assertOAuthConfig } from './config';
import { decryptPayload, encryptPayload, getAuthSecret } from './crypto';

const SESSION_COOKIE = 'auth_session';
const SESSION_TTL_SECONDS = 30 * 24 * 60 * 60;
const REFRESH_WINDOW_MS = 60 * 1000;

export type AuthSession = {
  userId: string;
  username?: string;
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
  createdAt: number;
};

export type AuthSessionResult = {
  session: AuthSession | null;
  setCookie?: string;
  clearCookie?: boolean;
};

const isExpired = (session: AuthSession) => session.expiresAt <= Date.now() + REFRESH_WINDOW_MS;

const sealSession = (session: AuthSession): string => {
  const secret = getAuthSecret();
  return encryptPayload(session, secret);
};

const unsealSession = (token: string): AuthSession | null => {
  const secret = getAuthSecret();
  return decryptPayload<AuthSession>(token, secret);
};

export const createAuthSession = (payload: Omit<AuthSession, 'createdAt'>) => {
  const session: AuthSession = { ...payload, createdAt: Date.now() };
  return {
    session,
    cookieValue: sealSession(session),
  };
};

const refreshSession = async (session: AuthSession): Promise<AuthSession | null> => {
  if (!session.refreshToken) {
    return null;
  }

  try {
    assertOAuthConfig({ requireRedirectUri: false });
  } catch {
    return null;
  }

  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: session.refreshToken,
    client_id: OAUTH_CONFIG.clientId,
  });
  if (OAUTH_CONFIG.clientSecret) {
    body.set('client_secret', OAUTH_CONFIG.clientSecret);
  }

  const response = await fetch(OAUTH_CONFIG.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });

  if (!response.ok) {
    return null;
  }

  const tokens = (await response.json()) as {
    access_token?: string;
    refresh_token?: string;
    expires_in?: number;
  };

  if (!tokens.access_token || !tokens.expires_in) {
    return null;
  }

  return {
    ...session,
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token || session.refreshToken,
    expiresAt: Date.now() + tokens.expires_in * 1000,
  };
};

export const getAuthSession = async (request: NextRequest): Promise<AuthSessionResult> => {
  const raw = request.cookies.get(SESSION_COOKIE)?.value;
  if (!raw) {
    return { session: null };
  }

  let session: AuthSession | null = null;
  try {
    session = unsealSession(raw);
  } catch {
    return { session: null, clearCookie: true };
  }
  if (!session) {
    return { session: null, clearCookie: true };
  }

  if (!isExpired(session)) {
    return { session };
  }

  const refreshed = await refreshSession(session);
  if (!refreshed) {
    return { session: null, clearCookie: true };
  }

  return {
    session: refreshed,
    setCookie: buildSessionCookieHeader(sealSession(refreshed)),
  };
};

export const buildSessionCookieHeader = (value: string): string => {
  const secure = process.env.NODE_ENV === 'production';
  return `${SESSION_COOKIE}=${value}; Path=/; Max-Age=${SESSION_TTL_SECONDS}; HttpOnly; SameSite=Lax${
    secure ? '; Secure' : ''
  }`;
};

export const clearSessionCookieHeader = (): string => {
  const secure = process.env.NODE_ENV === 'production';
  return `${SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax${secure ? '; Secure' : ''}`;
};

export const getSessionCookieName = () => SESSION_COOKIE;
export const getSessionCookieOptions = () => ({
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
  maxAge: SESSION_TTL_SECONDS,
});
