import { OAuthConfigError } from './errors';

export const OAUTH_CONFIG = {
  clientId: process.env.CHUTES_OAUTH_CLIENT_ID || '',
  clientSecret: process.env.CHUTES_OAUTH_CLIENT_SECRET || '',
  redirectUri: process.env.CHUTES_OAUTH_REDIRECT_URI || '',
  authorizationEndpoint: 'https://api.chutes.ai/idp/authorize',
  tokenEndpoint: 'https://api.chutes.ai/idp/token',
  userInfoEndpoint: 'https://api.chutes.ai/idp/userinfo',
  scopes: ['openid', 'profile', 'chutes:invoke'],
};

// Validate configuration on server-side import and log warnings
if (typeof window === 'undefined') {
  const missing: string[] = [];

  if (!OAUTH_CONFIG.clientId) missing.push('CHUTES_OAUTH_CLIENT_ID');
  if (!OAUTH_CONFIG.clientSecret) missing.push('CHUTES_OAUTH_CLIENT_SECRET');
  if (!OAUTH_CONFIG.redirectUri) missing.push('CHUTES_OAUTH_REDIRECT_URI');

  if (missing.length > 0) {
    console.warn(
      `[OAuth] Missing environment variables: ${missing.join(', ')}. ` +
        `Sign in with Chutes will not work.`
    );
  } else {
    console.log(`[OAuth] Configured for redirect: ${OAUTH_CONFIG.redirectUri}`);
  }
}

export const assertOAuthConfig = (
  options: { requireRedirectUri?: boolean; requireClientSecret?: boolean } = {}
) => {
  if (!OAUTH_CONFIG.clientId) {
    throw new OAuthConfigError('CHUTES_OAUTH_CLIENT_ID', 'OAuth client ID is not configured');
  }
  if (options.requireRedirectUri !== false && !OAUTH_CONFIG.redirectUri) {
    throw new OAuthConfigError('CHUTES_OAUTH_REDIRECT_URI', 'OAuth redirect URI is not configured');
  }
  if (options.requireClientSecret && !OAUTH_CONFIG.clientSecret) {
    throw new OAuthConfigError('CHUTES_OAUTH_CLIENT_SECRET', 'OAuth client secret is not configured');
  }
};
