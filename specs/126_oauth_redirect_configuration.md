# Spec 126: OAuth Redirect URL Configuration

## Status: TODO

**Priority:** High
**Complexity:** Low
**Prerequisites:** None

---

## Problem Statement

"Sign in with Chutes" OAuth flow may not work correctly on deployed instances (Render, janus.rodeo) because:

1. Redirect URLs might not be properly configured for all deployment targets
2. The Chutes IDP OAuth app may only have localhost registered as valid redirect URI
3. Environment variables may not be set correctly in Render deployment

**Affected Deployments:**
- https://janus.rodeo
- Render deployment (janus-ui service)

---

## Current State

Based on code analysis:
- OAuth config is in `ui/src/lib/auth/config.ts`
- Redirect URI comes from `CHUTES_OAUTH_REDIRECT_URI` env var
- The code supports any redirect URI, it's not hardcoded

**The issue is likely:**
1. Missing env var in Render deployment
2. Chutes IDP OAuth app needs redirect URIs registered

---

## Implementation

### 1. Verify Render Environment Variables

Check that these are set in Render dashboard for the `janus-ui` service:

```bash
CHUTES_OAUTH_CLIENT_ID=<your-client-id>
CHUTES_OAUTH_CLIENT_SECRET=<your-client-secret>
CHUTES_OAUTH_REDIRECT_URI=https://janus.rodeo/api/auth/callback
```

### 2. Register Redirect URIs with Chutes IDP

Contact Chutes team or use IDP admin to register these redirect URIs:

```
https://janus.rodeo/api/auth/callback
https://janus-ui.onrender.com/api/auth/callback
http://localhost:3000/api/auth/callback  (for development)
```

### 3. Add Configuration Validation

**File: `ui/src/lib/auth/config.ts`**

Add startup validation:

```typescript
export const OAUTH_CONFIG = {
  clientId: process.env.CHUTES_OAUTH_CLIENT_ID || '',
  clientSecret: process.env.CHUTES_OAUTH_CLIENT_SECRET || '',
  redirectUri: process.env.CHUTES_OAUTH_REDIRECT_URI || '',
  authorizationEndpoint: 'https://api.chutes.ai/idp/authorize',
  tokenEndpoint: 'https://api.chutes.ai/idp/token',
  userInfoEndpoint: 'https://api.chutes.ai/idp/userinfo',
  scopes: ['openid', 'profile', 'chutes:invoke'],
};

// Validate on import
if (typeof window === 'undefined') {
  // Server-side only
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
```

### 4. Add Dynamic Redirect URI (Optional Enhancement)

If we want to support any deployment without explicit configuration:

**File: `ui/src/app/api/auth/login/route.ts`**

```typescript
import { headers } from 'next/headers';

export async function GET(request: NextRequest) {
  // Get host from request if redirect URI not explicitly set
  let redirectUri = OAUTH_CONFIG.redirectUri;

  if (!redirectUri) {
    const headersList = headers();
    const host = headersList.get('host');
    const protocol = headersList.get('x-forwarded-proto') || 'https';
    redirectUri = `${protocol}://${host}/api/auth/callback`;

    console.log(`[OAuth] Using dynamic redirect URI: ${redirectUri}`);
  }

  // ... rest of login logic using redirectUri
}
```

**Note:** Dynamic redirect URIs still need to be registered with the IDP.

### 5. Add Health Check Endpoint

**File: `ui/src/app/api/auth/health/route.ts`**

```typescript
import { NextResponse } from 'next/server';
import { OAUTH_CONFIG } from '@/lib/auth/config';

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
```

Access via: `https://janus.rodeo/api/auth/health`

---

## Deployment Checklist

### Render Dashboard (janus-ui service)

1. Go to Environment tab
2. Add/verify these variables:
   - `CHUTES_OAUTH_CLIENT_ID`
   - `CHUTES_OAUTH_CLIENT_SECRET`
   - `CHUTES_OAUTH_REDIRECT_URI=https://janus.rodeo/api/auth/callback`
3. Trigger redeploy

### Chutes IDP Registration

1. Register OAuth application (if not done)
2. Add redirect URIs:
   - `https://janus.rodeo/api/auth/callback`
   - `https://janus-ui.onrender.com/api/auth/callback`

---

## Acceptance Criteria

- [ ] Sign in with Chutes works on https://janus.rodeo
- [ ] Sign in with Chutes works on Render deployment
- [ ] Sign in with Chutes works on localhost:3000
- [ ] Health endpoint shows correct configuration
- [ ] Missing config logs warning at startup

---

## Testing

1. Visit https://janus.rodeo/api/auth/health - verify OAuth configured
2. Click "Sign in with Chutes" - should redirect to Chutes IDP
3. Complete login - should redirect back to janus.rodeo
4. Verify user session is established
5. Repeat for Render deployment URL
