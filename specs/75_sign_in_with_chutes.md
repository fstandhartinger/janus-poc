# Spec 75: Sign in with Chutes

**Status:** COMPLETE
**Priority:** High
**Complexity:** High
**Prerequisites:** Spec 74 (Memory Feature UI)

---

## Overview

Implement "Sign in with Chutes" authentication for the Janus UI, similar to the chutes-search implementation. Features:

1. **5 free chats per day** without sign-in
2. **Sign-in dialog** appears after 5th chat attempt
3. **OAuth2/PKCE flow** with Chutes IDP
4. **IP-based rate limiting** server-side to prevent incognito abuse
5. **User ID from Chutes** replaces localStorage-generated ID
6. **Optional: Use user's Chutes API key** for inference

---

## Functional Requirements

### FR-1: Free Chat Limit (5 per day)

**Client-Side Tracking:**

```typescript
// lib/freeChat.ts
const FREE_CHAT_STORAGE_KEY = 'janus_free_chats_v1';
const FREE_CHAT_LIMIT = 5;

interface FreeChatState {
  date: string;  // YYYY-MM-DD
  count: number;
}

export function readFreeChatState(): FreeChatState {
  const stored = localStorage.getItem(FREE_CHAT_STORAGE_KEY);
  const today = new Date().toISOString().split('T')[0];

  if (!stored) {
    return { date: today, count: 0 };
  }

  try {
    const state = JSON.parse(stored) as FreeChatState;
    // Reset if different day
    if (state.date !== today) {
      return { date: today, count: 0 };
    }
    return state;
  } catch {
    return { date: today, count: 0 };
  }
}

export function incrementFreeChatCount(): void {
  const state = readFreeChatState();
  state.count += 1;
  localStorage.setItem(FREE_CHAT_STORAGE_KEY, JSON.stringify(state));
}

export function remainingFreeChats(): number {
  const state = readFreeChatState();
  return Math.max(0, FREE_CHAT_LIMIT - state.count);
}

export function hasFreeChatRemaining(): boolean {
  return remainingFreeChats() > 0;
}
```

### FR-2: Sign-In Gate Dialog

When user attempts chat #6 (or when IP rate limit hit), show sign-in dialog.

**Component:** `components/auth/SignInGateDialog.tsx`

```tsx
interface SignInGateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  usedCount: number;
  limit: number;
  pendingMessage?: string;
}

export function SignInGateDialog({
  open,
  onOpenChange,
  usedCount,
  limit,
  pendingMessage,
}: SignInGateDialogProps) {
  const handleSignIn = () => {
    // Build return URL with pending message
    const returnTo = new URL(window.location.href);
    if (pendingMessage) {
      returnTo.searchParams.set('q', pendingMessage);
    }
    window.location.href = `/api/auth/login?returnTo=${encodeURIComponent(returnTo.toString())}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-moss-500" />
            Sign in to keep chatting
          </DialogTitle>
          <DialogDescription>
            You've used {usedCount}/{limit} free chats today.
            Sign in with your Chutes account to continue.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <Button
            onClick={handleSignIn}
            className="w-full bg-moss-500 hover:bg-moss-600"
          >
            <LogIn className="w-4 h-4 mr-2" />
            Sign in with Chutes
          </Button>

          <p className="text-xs text-gray-400 text-center">
            Don't have an account?{' '}
            <a
              href="https://chutes.ai/signup"
              target="_blank"
              rel="noopener noreferrer"
              className="text-moss-500 hover:underline"
            >
              Create one for free
            </a>
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### FR-3: OAuth2 Login Flow

**Endpoints:**

1. **GET `/api/auth/login`** - Initiates OAuth flow
2. **GET `/api/auth/callback`** - Handles OAuth callback
3. **GET `/api/auth/me`** - Returns current user info
4. **POST `/api/auth/logout`** - Logs out user

**Login Route:** `app/api/auth/login/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { generatePKCE, generateState, sealState } from '@/lib/auth/pkce';
import { OAUTH_CONFIG } from '@/lib/auth/config';

export async function GET(request: NextRequest) {
  const returnTo = request.nextUrl.searchParams.get('returnTo') || '/chat';

  // Generate PKCE pair
  const { codeVerifier, codeChallenge } = await generatePKCE();
  const state = generateState();

  // Seal state + codeVerifier in httpOnly cookie (10 min TTL)
  const sealedState = await sealState({
    state,
    codeVerifier,
    returnTo,
  });

  const response = NextResponse.redirect(
    `${OAUTH_CONFIG.authorizationEndpoint}?` +
    new URLSearchParams({
      response_type: 'code',
      client_id: OAUTH_CONFIG.clientId,
      redirect_uri: OAUTH_CONFIG.redirectUri,
      scope: 'openid profile chutes:invoke',
      state,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
    })
  );

  response.cookies.set('oauth_state', sealedState, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 600,  // 10 minutes
  });

  return response;
}
```

**Callback Route:** `app/api/auth/callback/route.ts`

```typescript
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get('code');
  const state = searchParams.get('state');

  // Validate state and get stored values
  const sealedState = request.cookies.get('oauth_state')?.value;
  const { state: storedState, codeVerifier, returnTo } = await unsealState(sealedState);

  if (state !== storedState) {
    return NextResponse.redirect('/auth/error?error=invalid_state');
  }

  // Exchange code for tokens
  const tokenResponse = await fetch(OAUTH_CONFIG.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: OAUTH_CONFIG.redirectUri,
      client_id: OAUTH_CONFIG.clientId,
      client_secret: OAUTH_CONFIG.clientSecret,
      code_verifier: codeVerifier,
    }),
  });

  const tokens = await tokenResponse.json();

  // Fetch user info
  const userInfoResponse = await fetch(OAUTH_CONFIG.userInfoEndpoint, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const userInfo = await userInfoResponse.json();

  // Create session
  const session = await createAuthSession({
    userId: userInfo.sub,
    username: userInfo.username,
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    expiresAt: Date.now() + tokens.expires_in * 1000,
  });

  // Clear oauth state cookie, set session cookie
  const response = NextResponse.redirect(returnTo || '/chat');
  response.cookies.delete('oauth_state');
  response.cookies.set('auth_session', session.id, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 30 * 24 * 60 * 60,  // 30 days
  });

  return response;
}
```

### FR-4: IP-Based Rate Limiting (Server-Side)

Prevent incognito mode abuse by tracking IP addresses.

**Database Table:**

```sql
CREATE TABLE ip_chat_limits (
  id SERIAL PRIMARY KEY,
  ip_address VARCHAR(45) NOT NULL,  -- IPv6 can be 45 chars
  chat_date DATE NOT NULL,
  chat_count INTEGER NOT NULL DEFAULT 0,
  UNIQUE(ip_address, chat_date)
);
```

**Rate Limit Check:** `lib/rateLimit.ts`

```typescript
export async function checkIpRateLimit(
  ipAddress: string,
  limit: number = 5,
): Promise<{ allowed: boolean; remaining: number; used: number }> {
  const today = new Date().toISOString().split('T')[0];

  // Get or create today's record
  const record = await db.query.ipChatLimits.findFirst({
    where: and(
      eq(ipChatLimits.ipAddress, ipAddress),
      eq(ipChatLimits.chatDate, today),
    ),
  });

  const used = record?.chatCount ?? 0;
  const remaining = Math.max(0, limit - used);
  const allowed = used < limit;

  return { allowed, remaining, used };
}

export async function incrementIpChatCount(ipAddress: string): Promise<void> {
  const today = new Date().toISOString().split('T')[0];

  await db
    .insert(ipChatLimits)
    .values({ ipAddress, chatDate: today, chatCount: 1 })
    .onConflictDoUpdate({
      target: [ipChatLimits.ipAddress, ipChatLimits.chatDate],
      set: { chatCount: sql`chat_count + 1` },
    });
}

export function getClientIp(request: NextRequest): string {
  return (
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-real-ip') ||
    request.headers.get('cf-connecting-ip') ||
    'unknown'
  );
}
```

### FR-5: Chat Route with Rate Limiting

**Modify:** `app/api/chat/route.ts`

```typescript
export async function POST(request: NextRequest) {
  // Check if user is authenticated
  const session = await getAuthSession(request);
  const isAuthenticated = !!session;

  // If NOT authenticated, enforce IP rate limit
  if (!isAuthenticated) {
    const clientIp = getClientIp(request);
    const { allowed, remaining, used } = await checkIpRateLimit(clientIp);

    if (!allowed) {
      return NextResponse.json(
        {
          error: 'RATE_LIMIT_EXCEEDED',
          message: 'Free chat limit reached',
          details: {
            used,
            remaining,
            limit: 5,
            requiresLogin: true,
          },
        },
        { status: 429 }
      );
    }

    // Increment BEFORE processing (prevents abuse)
    await incrementIpChatCount(clientIp);
  }

  // Continue with chat processing...
  const body = await request.json();

  // If authenticated, use user's ID from session
  if (session) {
    body.user_id = session.userId;
  }

  // Forward to baseline...
}
```

### FR-6: User ID from Authenticated Session

When user is signed in, use their Chutes user ID (`sub`) instead of localStorage ID.

```typescript
// lib/userId.ts (updated)
export function getUserId(session: AuthSession | null): string {
  // If signed in, use Chutes user ID
  if (session?.userId) {
    return session.userId;
  }

  // Fallback to localStorage ID for anonymous users
  return getLocalUserId();
}
```

### FR-7: Forward User's Chutes API Token (Optional)

If user grants `chutes:invoke` scope, their access token can be used for inference.

```typescript
// When calling baseline
const chatRequest = {
  model: selectedModel,
  messages: formattedMessages,
  stream: true,
  user_id: getUserId(session),
  enable_memory: isMemoryEnabled(),
  // If user is signed in with chutes:invoke scope, include their token
  chutes_access_token: session?.accessToken,
};
```

The baseline can then use this token instead of its own API key:
```python
# In baseline
auth_header = request.chutes_access_token or settings.chutes_api_key
```

---

## Technical Requirements

### TR-1: OAuth Configuration

```typescript
// lib/auth/config.ts
export const OAUTH_CONFIG = {
  clientId: process.env.CHUTES_OAUTH_CLIENT_ID!,
  clientSecret: process.env.CHUTES_OAUTH_CLIENT_SECRET!,
  redirectUri: process.env.CHUTES_OAUTH_REDIRECT_URI!,
  authorizationEndpoint: 'https://api.chutes.ai/idp/authorize',
  tokenEndpoint: 'https://api.chutes.ai/idp/token',
  userInfoEndpoint: 'https://api.chutes.ai/idp/userinfo',
  scopes: ['openid', 'profile', 'chutes:invoke'],
};
```

### TR-2: Environment Variables

```bash
# .env.local
CHUTES_OAUTH_CLIENT_ID=your-client-id
CHUTES_OAUTH_CLIENT_SECRET=your-client-secret
CHUTES_OAUTH_REDIRECT_URI=http://localhost:3000/api/auth/callback

# Production
CHUTES_OAUTH_REDIRECT_URI=https://janus.rodeo/api/auth/callback
```

### TR-3: Session Storage

Store sessions server-side (database or encrypted cookie).

**Option A: Database (Recommended)**
```sql
CREATE TABLE auth_sessions (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  username VARCHAR(255),
  access_token_enc TEXT NOT NULL,  -- Encrypted
  refresh_token_enc TEXT,
  expires_at BIGINT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**Option B: Encrypted Cookie**
- Use iron-session or similar
- Store encrypted session data in httpOnly cookie

---

## Files to Create

| File | Purpose |
|------|---------|
| `ui/src/lib/auth/config.ts` | OAuth configuration |
| `ui/src/lib/auth/pkce.ts` | PKCE generation utilities |
| `ui/src/lib/auth/session.ts` | Session management |
| `ui/src/lib/freeChat.ts` | Free chat limit tracking |
| `ui/src/lib/rateLimit.ts` | IP rate limiting |
| `ui/src/app/api/auth/login/route.ts` | OAuth login initiation |
| `ui/src/app/api/auth/callback/route.ts` | OAuth callback handler |
| `ui/src/app/api/auth/me/route.ts` | Get current user |
| `ui/src/app/api/auth/logout/route.ts` | Logout handler |
| `ui/src/components/auth/SignInGateDialog.tsx` | Sign-in gate modal |
| `ui/src/components/auth/UserMenu.tsx` | User menu (when signed in) |
| `ui/src/hooks/useAuth.ts` | Auth state hook |

## Files to Modify

| File | Changes |
|------|---------|
| `ui/src/app/api/chat/route.ts` | Add rate limiting |
| `ui/src/hooks/useChat.ts` | Check limits before sending |
| `ui/src/components/ChatArea.tsx` | Show user menu / sign-in button |
| `ui/src/lib/userId.ts` | Use session user ID when available |

---

## UI/UX Design

### Header States

**Anonymous User:**
- "Sign in" button (text link or small button)
- Shows remaining free chats: "4/5 free chats remaining"

**Signed In User:**
- User avatar/icon
- Username dropdown with:
  - "Signed in as @username"
  - "Sign out" option

### Sign-In Gate Dialog

- Glass card modal
- Title: "Sign in to keep chatting"
- Subtitle: "You've used 5/5 free chats today"
- Primary button: "Sign in with Chutes" (moss green)
- Link: "Don't have an account? Create one for free"

### Rate Limit Error Toast

When IP rate limit is hit:
- Toast notification
- Message: "Daily limit reached. Sign in to continue."
- Action button: "Sign in"

---

## Acceptance Criteria

- [ ] Users get 5 free chats per day without signing in
- [ ] Sign-in dialog appears after 5th chat attempt
- [ ] OAuth flow completes successfully
- [ ] User info is fetched and stored in session
- [ ] Subsequent requests use user's ID from session
- [ ] IP rate limiting prevents incognito abuse
- [ ] Pending message is sent after sign-in completes
- [ ] User can sign out
- [ ] Session persists across browser sessions (30 days)

---

## Testing Checklist

- [ ] First 5 chats work without sign-in
- [ ] 6th chat triggers sign-in dialog
- [ ] Sign-in flow redirects to Chutes IDP
- [ ] Callback properly exchanges code for tokens
- [ ] User info is displayed in UI
- [ ] After sign-in, pending message is sent automatically
- [ ] IP rate limiting tracks correctly across incognito sessions
- [ ] Rate limit resets at midnight
- [ ] Sign out clears session
- [ ] Refresh token renews expired access tokens

---

## Security Considerations

1. **PKCE (S256)** - Required for OAuth security
2. **State parameter** - Prevents CSRF attacks
3. **httpOnly cookies** - Tokens never exposed to JavaScript
4. **Secure cookies** - HTTPS only in production
5. **Token encryption** - Tokens encrypted at rest in database
6. **Client secret** - Never exposed client-side
7. **Redirect URI validation** - Only registered URIs accepted

---

## Notes

- This replaces the localStorage-only user ID with authenticated identity
- Memory feature (Spec 74) will use the authenticated user ID when available
- The `chutes:invoke` scope is optional - app works without it
- IP rate limiting is a backup; client-side limit is primary UX
- Sessions last 30 days; access tokens are refreshed as needed

NR_OF_TRIES: 1
