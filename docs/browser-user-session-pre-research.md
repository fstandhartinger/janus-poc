# Browser User Session Management - Pre-Research Context

> This document captures all research and context gathered before the experimental research spec.
> All related specs should reference this document for background context.

## Problem Statement

Janus agents running in Sandy sandboxes need to perform browser automation tasks on behalf of users. Many valuable tasks require accessing authenticated web pages (e.g., Twitter, GitHub, internal dashboards). Currently, agents cannot access these pages because:

1. Each sandbox starts with a fresh browser profile (no cookies/sessions)
2. Users cannot easily transfer their authenticated sessions to sandbox browsers
3. There's no mechanism to persist browser state across sandbox instances

## Vision

Enable users to:
1. Capture their browser session state (cookies, localStorage, auth tokens) via a secure UI
2. Store named sessions ("MyTwitter", "MyGitHub") encrypted and tied to their Chutes IDP identity
3. Inject these sessions into agent sandboxes on-demand
4. Have agents perform authenticated browser tasks seamlessly

## Existing Infrastructure

### Sandy (Sandbox Service)

Sandy already provides significant infrastructure:

**Warm Pool (`SANDY_PREWARM_COUNT`):**
- Pre-creates N sandboxes for faster startup
- Currently does NOT support pre-warming with VNC/browser enabled
- Pool managed via `SandboxPool` class in `sandy/app.py`

**VNC Support:**
- `vnc_enabled` and `vnc_port` fields on `SandboxRecord`
- `SANDY_VNC_PORT` (default: 7900) - websockify port
- `SANDY_VNC_RFB_PORT` (default: 5900) - x11vnc port
- `SANDY_VNC_RESOLUTION` (default: 1280x720)
- WebSocket endpoint: `/vnc/{sandboxId}/websockify`

**Browser Support:**
- `browser_enabled` flag for Chromium/Playwright
- Playwright runtime image: `sandy-runtime:playwright` with pre-baked Chromium
- Build with: `docker build -t sandy-runtime:playwright --build-arg SANDY_ENABLE_PLAYWRIGHT=1 ./runtime`
- Exposes `SANDY_PLAYWRIGHT_READY=1` and `SANDY_PLAYWRIGHT_BROWSERS_PATH`

**Agent Integration:**
- `/api/sandboxes/{id}/agent/run` runs CLI agents (Claude Code, Codex, Aider, etc.)
- Supported agents: `claude-code`, `codex`, `aider`, `opencode`, `droid`, `openhands`
- SSE streaming output

**Sandy API Endpoints (Relevant):**
- `POST /api/sandboxes` - Create sandbox (supports `enableVnc`, `enableBrowser`)
- `GET /api/sandboxes/{id}/vnc` - Get VNC connection info
- `GET /vnc/{id}/websockify` - WebSocket for VNC
- `POST /api/sandboxes/{id}/files/write` - Write files to sandbox
- `GET /api/sandboxes/{id}/files/read` - Read files from sandbox

### agent-as-a-service-web

- Landing page at agent-as-a-service.online
- Ops console with VNC viewer integration (noVNC)
- Agent launching UI
- Chutes IDP login (PKCE)
- No browser session management yet

### Janus (This Project)

**baseline-agent-cli:**
- Uses Sandy for agent execution
- Agent pack with system prompts at `agent-pack/prompts/system.md`
- Supports Claude Code and other agents

**Chat UI:**
- Generative UI code fencing
- File serving from sandbox
- SSE streaming responses

## External Solutions Research

### 1. Playwright MCP (microsoft/playwright-mcp)

**Repository:** https://github.com/microsoft/playwright-mcp

**Session Modes:**
1. **Persistent Profile Mode (default)** - Uses `--user-data-dir` to persist cookies/auth across sessions
2. **Isolated Mode** - Ephemeral contexts, can load from `--storage-state` JSON file
3. **Extension Mode** - Connects to existing browser via Chrome DevTools Protocol (CDP)

**Relevant Configuration:**
```bash
# Persistent profile
npx playwright-mcp --user-data-dir=/path/to/profile

# Load storage state (cookies/localStorage from JSON)
npx playwright-mcp --storage-state=/path/to/state.json
```

**Storage State Format (Playwright):**
```json
{
  "cookies": [
    {
      "name": "session_id",
      "value": "abc123",
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
        { "name": "token", "value": "xyz789" }
      ]
    }
  ]
}
```

**Feature Request:** https://github.com/microsoft/playwright-mcp/issues/403 - Cookie attachment support

**Pros:**
- Native Playwright support
- Well-documented storage state format
- Can use existing browser profiles

**Cons:**
- userDataDir can be large (hundreds of MB)
- Session cookies may not persist in Contexts API

### 2. Browserbase/Stagehand

**Website:** https://www.browserbase.com
**Repository:** https://github.com/browserbase/stagehand

**Features:**
- **Contexts API** - Persists cookies across multiple sessions
- Scales to 1000s of browsers in milliseconds
- Managed CAPTCHA solving, residential proxies
- SOC-2 Type 1 and HIPAA compliant

**MCP Server:** https://github.com/browserbase/mcp-server-browserbase

**Limitations:**
- Works best with persistent cookies, not session cookies
- Requires Browserbase subscription for full features

### 3. Browser-Use Framework

**Repository:** https://github.com/browser-use/browser-use

**Features:**
- Handles agents, browsers, persistence, auth, cookies, and LLMs
- Profile sync scripts for remote browsers
- CAPTCHA handling with stealth browsers

**Security Concerns (from research paper https://arxiv.org/html/2505.13076v1):**
- Prompt injection risks
- Credential storage/misuse concerns
- Session token vulnerabilities

### 4. Cookie Export Chrome Extensions

**Export Cookie JSON for Puppeteer:**
- Chrome Web Store: https://chromewebstore.google.com/detail/nmckokihipjgplolmcmjakknndddifde
- GitHub: https://github.com/ktty1220/export-cookie-for-puppeteer
- Exports to Puppeteer-compatible `setCookie()` format

**Cookie Editor:**
- Chrome Web Store: https://chromewebstore.google.com/detail/dhdfnoenjedcedipmdoeibpnmpojjpce
- Supports JSON export and Netscape HTTP Cookie File format
- Cookie profiles and session management

**EditThisCookie:**
- Website: https://www.editthiscookie.com/
- Popular import/export in JSON format

### 5. noVNC

**Repository:** https://github.com/novnc/noVNC

**Features:**
- HTML5 VNC client, works in any modern browser including mobile
- Requires WebSocket proxy (websockify) - Sandy already has this
- Supports multiple auth methods
- Used by OpenStack, OpenNebula, LibVNCServer, ThinLinc

**Sandy Integration:**
- Already integrated via `/vnc/{sandboxId}/websockify` endpoint
- Uses websockify for WebSocket-to-TCP bridging

### 6. Vercel Agent-Browser

**Repository:** https://github.com/vercel-labs/agent-browser
**Website:** https://agent-browser.dev/

Agent-browser is a browser automation CLI specifically designed for AI agents by Vercel Labs.

**Key Features:**
- **93% context reduction** - Streamlined data structure provides only key DOM info and actionable elements
- **Snapshot + Refs workflow** - Uses `@e1`, `@e2` element references instead of complex selectors
- **Fast Rust CLI** with Node.js fallback for cross-platform compatibility
- **Chromium-powered** via Playwright under the hood

**Architecture:**
- Rust CLI for fast command parsing and daemon communication
- Node.js Daemon for Playwright browser lifecycle management
- Accessibility-first design with semantic element locators

**Session & Authentication Management:**
- **Multiple isolated sessions** via `--session` flag or `AGENT_BROWSER_SESSION` env var
- **Persistent profiles** via `--profile` flag - preserves cookies, localStorage, IndexedDB, service workers, login sessions across restarts
- Cookie and localStorage management built-in

**Commands:**
```bash
agent-browser open <url>           # Navigate
agent-browser snapshot -i          # Get interactive elements with refs
agent-browser click @e1            # Click by ref
agent-browser fill @e2 "text"      # Fill input by ref
agent-browser screenshot page.png  # Screenshot
agent-browser close                # Close browser
```

**Comparison to Playwright MCP:**
- Playwright MCP exposes 26+ tools → agent-browser uses streamlined command set
- Playwright can have massive accessibility trees → agent-browser reduces context
- agent-browser uses fewer tokens per cycle with ref-based approach
- Playwright MCP still better for: network interception, multi-tab, PDF generation, complex waiting logic

**MCP Integration:**
- Agent Browser MCP Server available: https://glama.ai/mcp/servers/@nocall-corp/agent-browser-mcp-server
- Compatible with Claude Code, Gemini, Cursor, GitHub Copilot, Codex, opencode

**Pros:**
- Purpose-built for AI agents (not general automation)
- Dramatic context/token savings
- Persistent profile support for authenticated sessions
- Fast startup

**Cons:**
- Newer project, less battle-tested
- Fewer advanced features than Playwright MCP

### 7. Browser MCP (Chrome Extension)

**Repository:** https://github.com/BrowserMCP/mcp
**Website:** https://browsermcp.io/
**Chrome Extension:** https://chromewebstore.google.com/detail/bjfgambnhccakkhmkepdoekmckoijdlc

Browser MCP is an MCP server + Chrome extension for controlling your actual browser.

**Key Features:**
- **Uses existing browser profile** - Already logged into all your services
- **Local execution** - Fast, no network latency, private
- **Stealth mode** - Uses real browser fingerprint, avoids bot detection/CAPTCHAs
- **Works with VS Code, Claude, Cursor, Windsurf**

**Architecture:**
- MCP Client (Cursor, Claude Desktop) sends instructions
- Node.js MCP Server translates to browser commands
- Chrome Extension executes commands in actual browser session

**Use Cases:**
- Web navigation and form filling
- Data extraction from structured content
- LLM-driven automated testing
- Workflow automation

**Pros:**
- Uses YOUR browser with YOUR sessions already active
- No session transfer needed - just control existing browser
- 4.9 rating on Chrome Web Store

**Cons:**
- Requires Chrome extension installation
- Only works with user's local browser (not sandbox)
- Not suitable for Sandy sandboxes (different architecture)

### 8. Chrome DevTools MCP

**Blog:** https://developer.chrome.com/blog/chrome-devtools-mcp

Official Google Chrome DevTools MCP server (public preview).

**Features:**
- AI coding assistants can debug web pages directly in Chrome
- Access to DevTools debugging capabilities
- Performance insights

**Use Case:** More for debugging than automation, but shows Google's investment in MCP ecosystem.

### 9. Warm Pool Approaches

**AWS EC2 Warm Pools:**
- Pre-warmed nodes in stopped/hibernated state
- Reduces readiness time from 5 minutes to ~70 seconds
- Cost-effective (stopped instances are free)

**Kubernetes Agent Sandbox (pacoxu):**
- SandboxWarmPool CRD for pre-warmed sandbox pods
- gVisor and Kata Containers support

**Sandy's Current Implementation:**
- `SANDY_PREWARM_COUNT` env var
- `SandboxPool` class manages pool
- Currently only pre-warms basic sandboxes (no VNC/browser)

## Proposed Architecture

### Warm Pool Flavors

1. **Basic** - Current behavior, no VNC/browser
2. **Agent-Ready** - VNC + Chromium + Playwright + Agent CLI pre-configured

### Session Storage

**Database:** Neon Postgres (via Neon MCP) or Render Postgres (via Render MCP)

**Schema Concept:**
```sql
CREATE TABLE browser_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,           -- Chutes IDP user ID
    name TEXT NOT NULL,              -- User-provided name ("MyTwitter")
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Encrypted storage state (Playwright format)
    storage_state_encrypted BYTEA NOT NULL,

    -- Metadata (not encrypted)
    domains TEXT[],                  -- Domains this session covers
    expires_at TIMESTAMPTZ,          -- Optional expiration

    UNIQUE(user_id, name)
);
```

**Encryption:**
- Key derived from user's Chutes IDP identity
- AES-256-GCM or similar
- Server-side encryption/decryption

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Browser Session Flow                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CAPTURE FLOW:                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐   │
│  │   User via   │────▶│  Sandy VNC   │────▶│ Session Capture  │   │
│  │   noVNC UI   │     │  Sandbox     │     │   (cookies/LS)   │   │
│  └──────────────┘     └──────────────┘     └────────┬─────────┘   │
│                                                      │              │
│                                                      ▼              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐   │
│  │  Encrypted   │◀────│ Session Store│◀────│ User names it    │   │
│  │   Storage    │     │  (Postgres)  │     │ "MyTwitter"      │   │
│  └──────────────┘     └──────────────┘     └──────────────────┘   │
│                                                                     │
│  INJECTION FLOW:                                                    │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐   │
│  │ Janus Chat   │────▶│   Gateway    │────▶│ baseline-agent   │   │
│  │ (user req)   │     │              │     │ (session param)  │   │
│  └──────────────┘     └──────────────┘     └────────┬─────────┘   │
│                                                      │              │
│                                                      ▼              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐   │
│  │ Agent Sandbox│◀────│ Sandy API    │◀────│ Inject session   │   │
│  │ (pre-warmed) │     │ file write   │     │ into browser     │   │
│  └──────────────┘     └──────────────┘     └──────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Options Comparison

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A: VNC + Manual Capture** | Most flexible, works with all sites, handles 2FA | Requires user interaction | Primary for complex auth |
| **B: Cookie Extension JSON** | Simple, widely supported format | User must install extension, export manually | Good import option |
| **C: 2FA Callback to UI** | Fully automated except OTP | Complex SSE callback chain | Nice-to-have later |
| **D: Playwright userDataDir** | Native Playwright support | Only works with Playwright, can be large | Primary storage format |
| **E: Playwright storageState** | Small JSON, portable | May miss some session data | Good for simple cases |

**Recommended Approach:** Combine A + B + D/E:
1. Use **Playwright's storageState JSON** as the canonical storage format (smaller than userDataDir)
2. Allow **VNC capture** for complex login flows
3. Support **cookie JSON import** for users who prefer extension export
4. Store encrypted in **Postgres DB** tied to Chutes IDP

## Priority Order

1. **Research Spec** - Experimental validation of approaches
2. **Session Persistence** - Store, retrieve, inject sessions
3. **Fast Sandbox Startup** - Agent-ready warm pool
4. **Capture UI** - VNC-based session capture in agent-as-a-service-web
5. **Callback to UI** - 2FA/OTP flow (optional enhancement)

## Related Files

**Sandy:**
- `/home/flori/Dev/chutes/sandy/README.md` - Full Sandy documentation
- `/home/flori/Dev/chutes/sandy/sandy/app.py` - SandboxPool, VNC endpoints
- `/home/flori/Dev/chutes/sandy/sandy/store.py` - SandboxRecord with vnc_enabled, browser_enabled
- `/home/flori/Dev/chutes/sandy/sandy/runtime.py` - Container creation with VNC support

**agent-as-a-service-web:**
- `/home/flori/Dev/chutes/agent-as-a-service-web/` - Landing page and ops console

**Janus:**
- `baseline-agent-cli/agent-pack/prompts/system.md` - Agent system prompt (may need updates)
- `gateway/` - API gateway
- `ui/` - Chat UI with generative UI support

## References

### Browser Automation Tools
- Playwright MCP: https://github.com/microsoft/playwright-mcp
- Playwright Auth Docs: https://playwright.dev/docs/auth
- Playwright BrowserContext: https://playwright.dev/docs/api/class-browsercontext
- Vercel Agent-Browser: https://github.com/vercel-labs/agent-browser
- Agent-Browser Website: https://agent-browser.dev/
- Agent-Browser MCP Server: https://glama.ai/mcp/servers/@nocall-corp/agent-browser-mcp-server
- Browserbase: https://www.browserbase.com
- Stagehand: https://github.com/browserbase/stagehand
- Browser-Use: https://github.com/browser-use/browser-use

### MCP Servers for Browser Control
- Browser MCP (Chrome Extension): https://github.com/BrowserMCP/mcp
- Browser MCP Website: https://browsermcp.io/
- Chrome MCP Server: https://github.com/hangwin/mcp-chrome
- Chrome DevTools MCP: https://developer.chrome.com/blog/chrome-devtools-mcp
- Browserbase MCP: https://www.browserbase.com/mcp

### Session Management
- noVNC: https://github.com/novnc/noVNC
- Cookie Editor Extension: https://chromewebstore.google.com/detail/dhdfnoenjedcedipmdoeibpnmpojjpce
- Export Cookie for Puppeteer: https://github.com/ktty1220/export-cookie-for-puppeteer

### Research & Analysis
- Security Risks Paper: https://arxiv.org/html/2505.13076v1
- Agent-Browser Context Savings: https://medium.com/@richardhightower/agent-browser-ai-first-browser-automation-that-saves-93-of-your-context-window-7a2c52562f8c
- Ralph Wiggum + Agent-Browser: https://www.pulumi.com/blog/self-verifying-ai-agents-vercels-agent-browser-in-the-ralph-wiggum-loop/

---

*Last updated: 2026-01-29*
*Related specs: 118_browser_session_research.md (and follow-up specs to be created)*
