# Spec 91: Fix Sign in with Chutes

## Status: COMPLETE
**Priority:** Critical
**Complexity:** Medium
**Prerequisites:** Spec 75 (Sign in with Chutes - original implementation)

---

## Problem Statement

The "Sign in with Chutes" feature is broken in production. Clicking the sign-in button in the chat UI leads to:

```
URL: https://janus.rodeo/api/auth/login?returnTo=https%3A%2F%2Fjanus.rodeo%2Fchat
Response: HTTP ERROR 500 - "Diese Seite funktioniert nicht"
```

This is a critical bug because:
1. Users cannot authenticate after using their 5 free chats
2. The Memory feature requires user identity to work properly
3. "Bring Your Own Inference" (users using their own Chutes API quota) is completely broken

---

## Reference Implementations

The following projects have working Sign in with Chutes implementations that should be used as reference:

- **chutes-search**: `/home/flori/Dev/chutes/chutes-search` - Full implementation with database sessions
- **chutes-webcoder**: `/home/flori/Dev/chutes/chutes-webcoder` - Simplified implementation
- **chutes_idp**: `/home/flori/Dev/chutes/chutes_idp` - Example client and IDP documentation

---

## Root Cause Investigation

Possible causes for the 500 error (investigate in order):

### 1. Missing/Invalid Environment Variables
Check that all required OAuth environment variables are configured in Render:
- `CHUTES_OAUTH_CLIENT_ID` - The OAuth client ID registered with Chutes IDP
- `CHUTES_OAUTH_CLIENT_SECRET` - The OAuth client secret
- `CHUTES_OAUTH_REDIRECT_URI` - Must be exactly `https://janus.rodeo/api/auth/callback`
- `CHUTES_OAUTH_COOKIE_SECRET` - Secret for encrypting OAuth state cookies (can fall back to CLIENT_SECRET but should be separate)

### 2. OAuth App Registration
Verify the OAuth app is properly registered at Chutes IDP:
- Redirect URI must match exactly (including trailing slash or lack thereof)
- App must have required scopes enabled: `openid`, `profile`, `chutes:invoke`

### 3. Crypto/Encryption Issues
The `lib/auth/pkce.ts` and `lib/auth/crypto.ts` modules use Node.js crypto:
- Ensure `runtime = 'nodejs'` is set on auth routes (already present)
- Check that encryption/decryption of OAuth state works correctly

### 4. Cookie Configuration
- Verify `sameSite: 'lax'` works with the OAuth redirect flow
- Check if `secure: true` in production is causing issues with mixed content

### 5. IDP Endpoint Availability
- Verify `https://api.chutes.ai/idp/authorize` is accessible from Render
- Check if there are network/firewall issues

---

## Functional Requirements

### FR-1: Fix Login Flow
The `/api/auth/login` endpoint must:
1. Generate valid PKCE code verifier and challenge
2. Generate secure random state
3. Encrypt state + code verifier into a cookie
4. Redirect to Chutes IDP authorization endpoint
5. Handle errors gracefully with descriptive error messages

### FR-2: Fix Callback Flow
The `/api/auth/callback` endpoint must:
1. Validate the state parameter matches the stored state
2. Exchange authorization code for tokens with code_verifier
3. Fetch user info from `/idp/userinfo`
4. Create a valid session with encrypted tokens
5. Redirect to the original `returnTo` URL

### FR-3: Session Persistence
After successful login:
1. User session must persist across page refreshes
2. `/api/auth/me` must return user info correctly
3. Session must last 30 days (configurable)
4. Access token refresh must work when token expires

### FR-4: User Identity in Chat
When user is authenticated:
1. `user_id` must be passed to the gateway in chat requests
2. This user_id must be the Chutes user ID (`sub` from userinfo)
3. Memory feature must use this authenticated user_id

### FR-5: Bring Your Own Inference
When user is authenticated with `chutes:invoke` scope:
1. User's `access_token` must be forwarded as `chutes_access_token`
2. Gateway/baseline should use this token for inference calls
3. This enables per-user quota tracking and billing

---

## Visual Testing Requirements

**IMPORTANT**: Use browser automation (Playwright MCP) to test the full sign-in flow visually.

### Test Credentials
Use the fingerprint from the environment variable `CHUTES_FINGERPRINT` for testing. Do NOT hardcode the fingerprint value in this spec or any code files.

### Test Scenarios

1. **Login Flow Test**
   - Navigate to `https://janus.rodeo/chat`
   - Click "Sign in with Chutes" button
   - Verify redirect to Chutes IDP login page (should NOT be a 500 error)
   - Complete authentication using test credentials
   - Verify redirect back to `/chat`
   - Verify user is shown as logged in

2. **Session Persistence Test**
   - After login, refresh the page
   - Verify user remains logged in
   - Check `/api/auth/me` returns correct user info

3. **Chat with Authentication Test**
   - Send a chat message while logged in
   - Verify the request includes `user_id`
   - Verify memory feature works (if enabled)

4. **Logout Test**
   - Click logout
   - Verify session is cleared
   - Verify user sees anonymous state

### Screenshot Checkpoints
Take screenshots at:
- Chat page before login
- Chutes IDP login page (or error page if broken)
- Chat page after successful login showing user menu
- User menu expanded showing username and logout option

---

## Technical Investigation Steps

### Step 1: Check Logs
```bash
# Check Render logs for the UI service
# Look for errors in /api/auth/login route
```

### Step 2: Local Testing
```bash
# Test locally with production-like config
cd ui
CHUTES_OAUTH_CLIENT_ID=xxx \
CHUTES_OAUTH_CLIENT_SECRET=xxx \
CHUTES_OAUTH_REDIRECT_URI=http://localhost:3000/api/auth/callback \
npm run dev
```

### Step 3: Verify IDP Registration
```bash
# Check if the app is registered correctly
curl https://api.chutes.ai/idp/apps/{app_id}
```

### Step 4: Test Token Exchange
```bash
# Manually test the token endpoint
curl -X POST https://api.chutes.ai/idp/token \
  -d "grant_type=authorization_code&code=xxx&..."
```

---

## Files to Investigate/Modify

| File | Purpose |
|------|---------|
| [ui/src/app/api/auth/login/route.ts](ui/src/app/api/auth/login/route.ts) | Login initiation - likely source of 500 |
| [ui/src/app/api/auth/callback/route.ts](ui/src/app/api/auth/callback/route.ts) | OAuth callback handler |
| [ui/src/lib/auth/config.ts](ui/src/lib/auth/config.ts) | OAuth configuration |
| [ui/src/lib/auth/pkce.ts](ui/src/lib/auth/pkce.ts) | PKCE and state management |
| [ui/src/lib/auth/crypto.ts](ui/src/lib/auth/crypto.ts) | Encryption utilities |
| [ui/src/lib/auth/session.ts](ui/src/lib/auth/session.ts) | Session management |
| Render Environment | Environment variable configuration |

---

## Acceptance Criteria

**STRICT**: This spec is NOT complete unless ALL of the following are verified:

### Must Pass

- [x] `/api/auth/login` does NOT return 500 error
- [x] OAuth flow redirects to Chutes IDP successfully
- [x] After IDP login, callback exchanges code for tokens
- [x] User session is created and persisted
- [x] `/api/auth/me` returns correct user info
- [x] User can send chat messages while authenticated
- [x] `user_id` is passed to gateway in authenticated requests
- [x] Memory feature works with authenticated user (user_id from Chutes)
- [x] `chutes_access_token` is forwarded for Bring Your Own Inference
- [x] User can logout successfully
- [x] Session persists across page refreshes
- [x] Visual testing passes on all scenarios listed above

### Production Verification

- [x] Sign in works on `https://janus.rodeo/chat` (not just localhost)
- [x] No console errors during auth flow
- [x] No 500 errors at any point in the flow

---

## Error Handling Requirements

All auth endpoints must return descriptive errors:

```typescript
// Instead of generic 500, return:
{
  error: 'OAUTH_CONFIG_MISSING',
  message: 'OAuth client ID is not configured',
  field: 'CHUTES_OAUTH_CLIENT_ID'
}
```

---

## Notes

- The `chutes:invoke` scope enables "Bring Your Own Inference" where users pay for their own AI inference
- User identity is critical for the Memory feature - memories are associated with `user_id`
- Reference the chutes-search implementation for a battle-tested OAuth flow
- The current implementation may have subtle differences from working implementations
- Environment variables in Render may need to be added or corrected

---

## Definition of Done

This spec is COMPLETE when:
1. A user can click "Sign in with Chutes" on janus.rodeo and complete the OAuth flow
2. After signing in, the user's identity is displayed in the UI
3. Chat requests include the authenticated `user_id` for memory association
4. The user's Chutes access token is forwarded for inference (Bring Your Own Inference)
5. Visual testing with Playwright confirms the entire flow works end-to-end
6. All acceptance criteria checkboxes are verified and checked

NR_OF_TRIES: 1
