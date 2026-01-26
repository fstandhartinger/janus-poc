import { createCipheriv, createDecipheriv, createHash, randomBytes } from 'crypto';
import { OAuthConfigError } from './errors';

const TOKEN_VERSION = 'v1';

const toBase64Url = (value: Buffer): string =>
  value
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');

const fromBase64Url = (value: string): Buffer => {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/');
  const padLength = padded.length % 4;
  const padding = padLength ? '='.repeat(4 - padLength) : '';
  return Buffer.from(padded + padding, 'base64');
};

const deriveKey = (secret: string): Buffer => createHash('sha256').update(secret).digest();

export const getAuthSecret = (): string => {
  const secret =
    process.env.CHUTES_OAUTH_COOKIE_SECRET ||
    process.env.CHUTES_OAUTH_CLIENT_SECRET ||
    '';
  if (!secret) {
    throw new OAuthConfigError(
      'CHUTES_OAUTH_COOKIE_SECRET',
      'OAuth cookie secret is not configured'
    );
  }
  return secret;
};

export const encryptPayload = (payload: object, secret: string): string => {
  const iv = randomBytes(12);
  const key = deriveKey(secret);
  const cipher = createCipheriv('aes-256-gcm', key, iv);
  const plaintext = Buffer.from(JSON.stringify(payload), 'utf8');
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const tag = cipher.getAuthTag();
  const packed = Buffer.concat([iv, tag, ciphertext]);
  return `${TOKEN_VERSION}.${toBase64Url(packed)}`;
};

export const decryptPayload = <T>(token: string, secret: string): T | null => {
  const [version, data] = token.split('.');
  if (version !== TOKEN_VERSION || !data) {
    return null;
  }

  try {
    const packed = fromBase64Url(data);
    if (packed.length < 12 + 16) {
      return null;
    }
    const iv = packed.subarray(0, 12);
    const tag = packed.subarray(12, 28);
    const ciphertext = packed.subarray(28);
    const key = deriveKey(secret);
    const decipher = createDecipheriv('aes-256-gcm', key, iv);
    decipher.setAuthTag(tag);
    const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf8');
    return JSON.parse(plaintext) as T;
  } catch {
    return null;
  }
};
