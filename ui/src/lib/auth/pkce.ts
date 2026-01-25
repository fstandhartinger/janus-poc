import { createHash, randomBytes } from 'crypto';
import { decryptPayload, encryptPayload, getAuthSecret } from './crypto';

export type OAuthStatePayload = {
  state: string;
  codeVerifier: string;
  returnTo: string;
  createdAt: number;
};

export type OAuthStateInput = Omit<OAuthStatePayload, 'createdAt'>;

const toBase64Url = (value: Buffer): string =>
  value
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');

export const generateState = (): string => toBase64Url(randomBytes(16));

export const generatePKCE = async () => {
  const codeVerifier = toBase64Url(randomBytes(32));
  const codeChallenge = toBase64Url(createHash('sha256').update(codeVerifier).digest());
  return { codeVerifier, codeChallenge };
};

export const sealState = async (payload: OAuthStateInput): Promise<string> => {
  const secret = getAuthSecret();
  return encryptPayload({ ...payload, createdAt: Date.now() }, secret);
};

export const unsealState = async (token?: string | null): Promise<OAuthStatePayload> => {
  if (!token) {
    throw new Error('Missing OAuth state');
  }
  const secret = getAuthSecret();
  const payload = decryptPayload<OAuthStatePayload>(token, secret);
  if (!payload) {
    throw new Error('Invalid OAuth state');
  }
  if (Date.now() - payload.createdAt > 10 * 60 * 1000) {
    throw new Error('OAuth state expired');
  }
  return payload;
};
