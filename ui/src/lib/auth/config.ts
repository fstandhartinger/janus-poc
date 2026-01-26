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
