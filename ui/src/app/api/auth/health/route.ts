import { NextResponse } from 'next/server';
import { OAUTH_CONFIG } from '@/lib/auth/config';

export const runtime = 'nodejs';

export async function GET() {
  const configured = !!(
    OAUTH_CONFIG.clientId &&
    OAUTH_CONFIG.clientSecret &&
    OAUTH_CONFIG.redirectUri
  );

  return NextResponse.json({
    oauth_configured: configured,
    redirect_uri: OAUTH_CONFIG.redirectUri || 'NOT SET',
    idp_endpoint: OAUTH_CONFIG.authorizationEndpoint,
  });
}
