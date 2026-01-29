# Spec 118: Browser Session Management - Experimental Research

## Status: TODO

## Priority: HIGH (Blocks follow-up implementation specs)

## Context / Why

Janus agents need to perform browser automation tasks on authenticated web pages. This requires:
1. Capturing user browser sessions (cookies, localStorage)
2. Storing them securely tied to user identity
3. Injecting them into agent sandbox browsers
4. Pre-warming sandboxes with browser/agent for fast startup

**Before implementing**, we need experimental validation of different approaches to determine the best technical path forward.

**Pre-Research Document:** `docs/browser-user-session-pre-research.md` contains all background context, existing infrastructure analysis, and solution options. **Read this document first.**

## Goals

1. **Create a test environment** with a mock login page to validate session capture/injection
2. **Experiment with multiple approaches** for browser session management
3. **Validate Sandy's VNC + Playwright capabilities** for session workflows
4. **Compare storage formats** (Playwright storageState vs userDataDir vs cookie JSON)
5. **Document findings** with concrete recommendations
6. **Write follow-up implementation specs** based on research results

## Non-Goals

- Full production implementation (that's for follow-up specs)
- UI polish or user-facing features
- Performance optimization (research first, optimize later)

## Deliverables

1. **Test Infrastructure:**
   - Deploy a mock login page (simple user/password form that sets cookies)
   - Accessible via public URL (deploy on Render)

2. **Experimental Validation:**
   - Test Playwright storageState capture/injection in Sandy sandbox
   - Test VNC-based manual login + session export
   - Test cookie JSON import (EditThisCookie/Puppeteer format)
   - Validate session persistence across sandbox restarts
   - **Test Vercel agent-browser** persistent profile mode
   - **Evaluate Browser MCPs** (agent-browser MCP, Browser MCP, Playwright MCP)

3. **Research Report:**
   - Written to `docs/browser-session-research-results.md`
   - Sent via Telegram (use `/notify-telegram` skill)
   - Include: what worked, what didn't, recommendations, blockers

4. **Follow-Up Specs:**
   - Create 3-4 implementation specs based on research findings
   - Each spec must reference `docs/browser-user-session-pre-research.md`
   - Expected specs (adjust based on findings):
     - `119_browser_session_store.md` - Session storage service
     - `120_agent_ready_warm_pool.md` - Sandy warm pool with browser/agent
     - `121_session_capture_ui.md` - VNC-based capture in agent-as-a-service-web
     - `122_session_injection_api.md` - Sandy API for session injection

## Functional Requirements

### FR-1: Mock Login Page

Create a simple test page with:
- Username/password form
- On successful login: set session cookie + localStorage token
- Protected page that checks for valid session
- Logout endpoint that clears session

```html
<!-- Example structure -->
<form action="/login" method="POST">
  <input name="username" placeholder="Username">
  <input name="password" type="password" placeholder="Password">
  <button type="submit">Login</button>
</form>
```

**Test credentials:** `testuser` / `testpass123`

**Deploy:** Use Render static site or simple Node/Python server

### FR-2: Playwright storageState Testing

Test in a Sandy sandbox:

```python
# Capture session after login
storage = await context.storage_state()
# Save to file
with open('/workspace/session.json', 'w') as f:
    json.dump(storage, f)

# Later: inject session into new context
context = await browser.new_context(storage_state='/workspace/session.json')
# Verify: navigate to protected page, should be logged in
```

**Validate:**
- [ ] Can capture cookies after VNC-based manual login
- [ ] Can inject storageState into new browser context
- [ ] Session survives sandbox restart (if file persisted)
- [ ] Works with Chromium in Sandy's Playwright runtime

### FR-3: VNC + Session Export Flow

Test the capture flow:

1. Create Sandy sandbox with VNC + browser enabled
2. Connect via noVNC (agent-as-a-service-web ops console or direct)
3. Navigate to mock login page in sandbox browser
4. Login manually
5. Export session via:
   - Playwright's `context.storage_state()` (programmatic)
   - Browser DevTools > Application > Cookies (manual)
   - Cookie extension if installed

**Validate:**
- [ ] VNC connection works reliably
- [ ] Can interact with browser via VNC
- [ ] Can extract session data after manual login

### FR-4: Cookie JSON Import

Test importing sessions from external sources:

```json
// Puppeteer/EditThisCookie format
[
  {
    "name": "session_id",
    "value": "abc123",
    "domain": ".example.com",
    "path": "/",
    "expires": 1735689600,
    "httpOnly": true,
    "secure": true
  }
]
```

**Validate:**
- [ ] Can convert Puppeteer format to Playwright storageState
- [ ] Can inject converted cookies into browser context
- [ ] Session works after injection

### FR-5: Storage Format Comparison

Compare storage options:

| Format | Size | Portability | What's Included |
|--------|------|-------------|-----------------|
| Playwright storageState | Small (KB) | High | Cookies + localStorage |
| Playwright userDataDir | Large (MB-GB) | Low | Everything (cache, history, etc.) |
| Cookie JSON (Puppeteer) | Small (KB) | High | Cookies only |

**Validate:**
- [ ] storageState sufficient for most auth flows
- [ ] userDataDir needed for complex cases (2FA remembered devices?)
- [ ] Cookie JSON can be converted reliably

### FR-6: Vercel Agent-Browser Testing

**Repository:** https://github.com/vercel-labs/agent-browser
**Website:** https://agent-browser.dev/

Test agent-browser's persistent profile feature for session management:

```bash
# Install agent-browser
npm install -g @anthropic-ai/agent-browser

# Open URL with persistent profile
agent-browser --profile /workspace/my-profile open https://mock-login.example.com

# Login manually or programmatically
agent-browser fill @username "testuser"
agent-browser fill @password "testpass123"
agent-browser click @submit

# Take snapshot to verify login
agent-browser snapshot -i

# Close and reopen - session should persist
agent-browser close
agent-browser --profile /workspace/my-profile open https://mock-login.example.com/protected
```

**Validate:**
- [ ] agent-browser installs and runs in Sandy sandbox
- [ ] Persistent profile preserves cookies/localStorage across restarts
- [ ] Profile directory size is reasonable (<100MB for typical sessions)
- [ ] Can use profile with agent-browser MCP server
- [ ] Context/token usage compared to Playwright MCP (expect 93% savings)

### FR-7: Browser MCP Comparison

Compare different browser automation MCPs:

| MCP | Session Support | Sandbox Compatible | Token Efficiency | Features |
|-----|----------------|-------------------|------------------|----------|
| Playwright MCP | storageState, userDataDir | Yes | Low (26+ tools) | Full-featured |
| agent-browser MCP | persistent profile | Yes | High (minimal tools) | AI-optimized |
| Browser MCP | Uses local browser | No (needs extension) | Medium | Stealth mode |
| Browserbase MCP | Contexts API | Cloud only | Medium | Managed service |

**Validate:**
- [ ] Test at least 2 MCPs in Sandy sandbox
- [ ] Compare token usage for same task
- [ ] Document which MCP is best for Janus use case
- [ ] Check if agent-browser MCP can be used with Sandy agents

### FR-8: Database Storage Test

Test storing/retrieving sessions from Postgres:

1. Create table in Neon (via Neon MCP) or Render Postgres
2. Store encrypted session JSON
3. Retrieve and decrypt
4. Inject into sandbox

**Schema:**
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

## Technical Approach

### Step 1: Deploy Mock Login Page

```bash
# Option A: Simple Python Flask app
# Option B: Simple Node Express app
# Deploy to Render as web service
```

### Step 2: Create Test Sandy Sandbox

```bash
curl -X POST https://sandy.65.109.64.180.nip.io/api/sandboxes \
  -H "Authorization: Bearer $SANDY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enableVnc": true,
    "enableBrowser": true,
    "timeout": 60
  }'
```

### Step 3: Run Experiments

Use Sandy's exec API or agent/run to execute test scripts:

```bash
curl -X POST https://sandy.65.109.64.180.nip.io/api/sandboxes/{id}/exec \
  -H "Authorization: Bearer $SANDY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python3 /workspace/test_session_capture.py"
  }'
```

### Step 4: Document Results

Write findings to `docs/browser-session-research-results.md` including:
- What worked
- What didn't work
- Blockers encountered
- Recommended approach
- Open questions

### Step 5: Create Follow-Up Specs

Based on research, create implementation specs with:
- Clear scope and acceptance criteria
- Reference to pre-research document
- Technical approach informed by experiments
- Realistic complexity estimates

## Acceptance Criteria

- [ ] Mock login page deployed and accessible
- [ ] Playwright storageState capture/injection tested in Sandy sandbox
- [ ] VNC-based session capture flow validated
- [ ] Cookie JSON import tested
- [ ] **Vercel agent-browser persistent profile tested**
- [ ] **Browser MCP comparison completed (at least 2 MCPs)**
- [ ] Storage format comparison documented
- [ ] Database storage proof-of-concept working
- [ ] Research report written to `docs/browser-session-research-results.md`
- [ ] Research report sent via Telegram (`/notify-telegram`)
- [ ] Follow-up specs created (3-4 specs) with proper context references
- [ ] All experiments documented with commands and results

## Expected Follow-Up Specs

Based on pre-research, expect to create these specs (adjust based on findings):

### 119_browser_session_store.md
- Session storage service (API + database)
- Encryption/decryption
- Chutes IDP integration
- CRUD operations for named sessions

### 120_agent_ready_warm_pool.md
- Sandy warm pool enhancement
- Two flavors: Basic and Agent-Ready
- Agent-Ready includes: VNC + Chromium + Playwright + agent CLI
- Target: <2s sandbox assignment

### 121_session_capture_ui.md
- UI in agent-as-a-service-web
- VNC viewer for manual login
- Session naming and saving
- Integration with session store

### 122_session_injection_api.md
- Sandy API enhancement for session injection
- baseline-agent-cli integration
- Janus gateway parameter passing
- System prompt updates for agent awareness

## System Prompt Updates

After research, review and update `baseline-agent-cli/agent-pack/prompts/system.md` to include:
- Browser automation capabilities
- How to request authenticated sessions
- Generative UI code fencing instructions
- File serving from sandbox
- Other Janus chat UI features

## Resources

- **Pre-Research Document:** `docs/browser-user-session-pre-research.md`
- **Sandy API:** https://sandy.65.109.64.180.nip.io
- **Sandy README:** `/home/flori/Dev/chutes/sandy/README.md`
- **agent-as-a-service-web:** `/home/flori/Dev/chutes/agent-as-a-service-web/`
- **Playwright Auth Docs:** https://playwright.dev/docs/auth
- **Neon MCP:** Available for database operations
- **Render MCP:** Available for deployment

### Browser Automation Tools to Evaluate
- **Vercel agent-browser:** https://github.com/vercel-labs/agent-browser
- **agent-browser MCP:** https://glama.ai/mcp/servers/@nocall-corp/agent-browser-mcp-server
- **Playwright MCP:** https://github.com/microsoft/playwright-mcp
- **Browser MCP:** https://github.com/BrowserMCP/mcp (Chrome extension-based)
- **Browserbase/Stagehand:** https://github.com/browserbase/stagehand

## Notes

- Use Render MCP to watch deployments until successful
- Send Telegram notifications for major findings
- Keep experiments reproducible (document all commands)
- If something doesn't work, document why and move on
- Research should inform implementation, not block it

---

*Reference: docs/browser-user-session-pre-research.md*
