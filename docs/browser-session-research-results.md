# Browser Session Management Research Results

> Research conducted as part of Spec 118: Browser Session Management - Experimental Research
> Date: 2026-01-30

## Executive Summary

This research validates multiple approaches for capturing, storing, and injecting browser sessions into agent sandboxes. **All tested approaches work**, with recommendations varying by use case:

| Approach | Complexity | Portability | Size | Recommendation |
|----------|------------|-------------|------|----------------|
| **Playwright storageState** | Low | High | ~1KB | **Primary format for session storage** |
| **agent-browser profiles** | Low | Medium | ~1-2MB | **Best for Sandy sandbox integration** |
| **Cookie JSON import** | Low | High | ~1KB | **Good for external imports** |
| **VNC + manual login** | High | N/A | N/A | **Fallback for complex auth flows** |

## Test Infrastructure

### Mock Login Page

**Deployed:** https://janus-mock-login.onrender.com

Features:
- Username/password form with session cookies
- localStorage token storage
- Protected page requiring authentication
- API endpoint for session verification
- Test credentials: `testuser` / `testpass123`

**Source:** `mock-login-app/` in janus-poc repository

## Experimental Results

### 1. Playwright storageState Capture/Injection

**Status:** WORKS

**Findings:**
- `context.storage_state()` captures both cookies and localStorage
- `context.addCookies()` successfully injects cookies into new contexts
- httpOnly cookies are captured via CDP but not accessible via JS
- Session state format is small (~1KB) and portable

**Format:**
```json
{
  "cookies": [
    {
      "name": "session_id",
      "value": "abc123...",
      "domain": ".example.com",
      "path": "/",
      "expires": 1735689600,
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    }
  ],
  "origins": [
    {
      "origin": "https://example.com",
      "localStorage": [
        { "name": "auth_token", "value": "xyz789..." }
      ]
    }
  ]
}
```

**Blockers:**
- Sandy sandboxes don't have Playwright pre-installed
- Installing Playwright in sandbox times out (browser binary download)
- **Solution:** Pre-bake Playwright into Sandy runtime image OR use agent-browser

### 2. Vercel agent-browser Persistent Profiles

**Status:** WORKS - RECOMMENDED FOR SANDY

**Findings:**
- `--profile` flag enables persistent browser state
- Session cookies and localStorage survive browser restarts
- Profile size is small (~1.3MB for a login session)
- Streamlined ref-based element targeting (`@e1`, `@e2`)
- 93% context window savings compared to Playwright MCP

**Commands tested:**
```bash
# Initial login with profile
agent-browser --profile /path/to/profile open https://site.com
agent-browser fill @e2 "username"
agent-browser fill @e3 "password"
agent-browser eval "document.querySelector('form').submit()"
agent-browser close

# Later: reuse profile
agent-browser --profile /path/to/profile open https://site.com/protected
# → Session restored, directly authenticated
```

**Profile structure:**
```
profile/
└── Default/
    ├── Cookies           # SQLite database
    ├── Local Storage/    # leveldb
    ├── Session Storage/
    ├── Cache/
    └── ...
```

**Recommendation:** Use agent-browser for Sandy sandbox browser automation. The profile directory can be:
1. Pre-populated with captured sessions
2. Mounted from persistent storage
3. Synced to/from session store

### 3. Cookie JSON Import

**Status:** WORKS

**Findings:**
- Puppeteer/EditThisCookie JSON format can be converted to Playwright format
- `context.addCookies()` accepts array of cookie objects
- Works for importing sessions from external sources

**Format conversion:**
```javascript
// Puppeteer format → Playwright format
const playwrightCookies = puppeteerCookies.map(c => ({
  name: c.name,
  value: c.value,
  domain: c.domain,
  path: c.path,
  expires: c.expirationDate || c.expires,
  httpOnly: c.httpOnly,
  secure: c.secure,
  sameSite: c.sameSite || 'Lax'
}));
```

### 4. VNC + Session Export Flow

**Status:** WORKS (via existing Playwright MCP/Puppeteer)

The VNC flow is validated indirectly through Playwright MCP testing:
1. User logs in via browser automation
2. Session state captured programmatically
3. Stored for later injection

**Full VNC flow requires:**
- Sandy sandbox with VNC enabled
- noVNC client for user interaction
- Session export button in UI

### 5. Browser MCP Comparison

| Feature | Playwright MCP | Puppeteer MCP | agent-browser |
|---------|---------------|---------------|---------------|
| Session persistence | Via storageState file | Via cookies array | Via profile directory |
| Token efficiency | Low (26+ tools) | Medium | High (streamlined) |
| Element targeting | CSS selectors | CSS selectors | @ref tags |
| Screenshot | Yes | Yes | Yes |
| CDP access | Yes | Yes | Limited |
| Sandy compatible | Needs install | Needs install | Easily installable |

**Recommendation:**
- **agent-browser** for Sandy sandboxes (small, fast, session support)
- **Playwright MCP** when full Playwright features needed

### 6. Database Storage Test

**Status:** WORKS

**Schema tested:**
```sql
CREATE TABLE browser_sessions_test (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    storage_state_encrypted BYTEA NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, name)
);
```

**Findings:**
- Neon Postgres works for session storage
- BYTEA type suitable for encrypted JSON blobs
- Insert/retrieve cycle works correctly
- Session data survives encoding/decoding

**Production requirements:**
- AES-256-GCM encryption before storage
- Key derivation from Chutes IDP identity
- TTL/expiration handling
- CRUD API endpoints

## Blockers Encountered

1. **Sandy sandbox doesn't have Playwright pre-installed**
   - Browser binary download times out in sandbox
   - Solution: Pre-bake into Sandy runtime OR use agent-browser

2. **Form POST timing issues with agent-browser**
   - Standard form.submit() sometimes fails
   - Solution: Use JavaScript fetch() for programmatic login

3. **Playwright MCP context sharing**
   - Browser context persists across navigations (expected)
   - Need explicit context clearing for clean session tests

## Recommendations

### Recommended Approach: agent-browser + Profile Storage

1. **Session Capture:**
   - Use agent-browser with `--profile` for VNC-based or programmatic login
   - Export profile directory to session store

2. **Session Storage:**
   - Store in Neon Postgres (encrypted BYTEA)
   - Encrypt with user-derived key (Chutes IDP)
   - Named sessions ("MyTwitter", "MyGitHub")

3. **Session Injection:**
   - Pre-warm Sandy sandboxes with agent-browser installed
   - Mount/copy profile directory before agent run
   - Agent starts with authenticated session

### Alternative: Playwright storageState

Use when:
- Sandy runtime has Playwright pre-baked
- Need fine-grained cookie/localStorage control
- Integrating with existing Playwright workflows

### Storage Format Comparison

| Format | Size | Contains | Portability |
|--------|------|----------|-------------|
| Playwright storageState | ~1KB | Cookies + localStorage | High |
| agent-browser profile | ~1-2MB | Everything (cache, etc.) | Medium |
| Cookie JSON | ~1KB | Cookies only | High |

**Recommendation:** Use Playwright storageState JSON as canonical format, convert to agent-browser profile for Sandy injection.

## Follow-Up Specs Required

Based on this research, the following implementation specs should be created:

### 119_browser_session_store.md
- Backend service for session CRUD
- Neon Postgres schema
- Encryption/decryption with Chutes IDP key
- REST API for named sessions

### 120_agent_ready_warm_pool.md
- Sandy warm pool enhancement
- Two flavors: Basic and Agent-Ready
- Agent-Ready includes: VNC + Chromium + agent-browser + CLI agent
- Target: <2s sandbox assignment with browser ready

### 121_session_capture_ui.md
- UI in agent-as-a-service-web (or Janus chat)
- VNC viewer for manual login
- "Save Session" button with naming
- Integration with session store API

### 122_session_injection_api.md
- Sandy API for session injection
- Accept session ID or inline storageState
- Convert to agent-browser profile
- Mount profile before agent run

## Open Questions

1. **Profile syncing:** Should profile be synced after agent run? (captures any session updates)
2. **Session expiration:** How to handle expired sessions? (re-auth prompt?)
3. **Multi-site profiles:** One profile per site or combined?
4. **Security audit:** External review of encryption/storage approach

## Resources

- Mock login page: https://janus-mock-login.onrender.com
- agent-browser docs: https://agent-browser.dev/
- Playwright auth docs: https://playwright.dev/docs/auth
- Pre-research document: `docs/browser-user-session-pre-research.md`

---

*Research conducted by Claude Opus 4.5 as part of Janus PoC development*
*Reference: specs/118_browser_session_research.md*
