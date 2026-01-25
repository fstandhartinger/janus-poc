export const OAUTH_CONFIG = {
  clientId: process.env.CHUTES_OAUTH_CLIENT_ID || '',
  clientSecret: process.env.CHUTES_OAUTH_CLIENT_SECRET || '',
  redirectUri: process.env.CHUTES_OAUTH_REDIRECT_URI || '',
  authorizationEndpoint: 'https://api.chutes.ai/idp/authorize',
  tokenEndpoint: 'https://api.chutes.ai/idp/token',
  userInfoEndpoint: 'https://api.chutes.ai/idp/userinfo',
  scopes: ['openid', 'profile', 'chutes:invoke'],
};

export const assertOAuthConfig = () => {
  if (!OAUTH_CONFIG.clientId || !OAUTH_CONFIG.clientSecret || !OAUTH_CONFIG.redirectUri) {
    throw new Error('Chutes OAuth configuration is incomplete');
  }
};
