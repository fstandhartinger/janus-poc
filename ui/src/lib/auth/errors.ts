export type OAuthConfigErrorResponse = {
  error: 'OAUTH_CONFIG_MISSING';
  message: string;
  field: string;
};

export class OAuthConfigError extends Error {
  field: string;

  constructor(field: string, message: string) {
    super(message);
    this.name = 'OAuthConfigError';
    this.field = field;
  }
}

export const isOAuthConfigError = (error: unknown): error is OAuthConfigError =>
  error instanceof OAuthConfigError;

export const toOAuthConfigErrorResponse = (
  error: OAuthConfigError
): OAuthConfigErrorResponse => ({
  error: 'OAUTH_CONFIG_MISSING',
  message: error.message,
  field: error.field,
});
