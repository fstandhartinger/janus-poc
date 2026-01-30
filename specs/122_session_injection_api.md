# Spec 122: Browser Session Injection API

## Status: COMPLETE

## Priority: HIGH

## Context / Why

Based on research in spec 118, Sandy needs an API for injecting browser sessions into agent sandboxes. This enables agents to start with authenticated browser state without manual login.

**Reference:** `docs/browser-user-session-pre-research.md` and `docs/browser-session-research-results.md`

## Goals

1. Create Sandy API for session injection
2. Convert storageState to agent-browser profile
3. Support inline session data or session store reference
4. Update baseline agents to use injected sessions

## Non-Goals

- Session storage (that's spec 119)
- Session capture (that's spec 121)
- VNC interaction

## Functional Requirements

### FR-1: Sandy API Enhancement

Add session injection to sandbox creation:

```json
POST /api/sandboxes
{
  "flavor": "agent-ready",
  "enableVnc": true,
  "browserSession": {
    "type": "inline",
    "storageState": {
      "cookies": [...],
      "origins": [...]
    }
  }
}
```

Or reference stored session:

```json
POST /api/sandboxes
{
  "flavor": "agent-ready",
  "enableVnc": true,
  "browserSession": {
    "type": "reference",
    "sessionId": "uuid-from-session-store",
    "sessionServiceUrl": "https://session-service.../sessions"
  }
}
```

### FR-2: Profile Conversion

Convert Playwright storageState to agent-browser profile:

```python
async def create_browser_profile(storage_state: dict, profile_path: str):
    """Create agent-browser profile from storageState."""
    # Create profile directory structure
    os.makedirs(f"{profile_path}/Default", exist_ok=True)

    # Write cookies to SQLite database
    cookies_db = f"{profile_path}/Default/Cookies"
    await write_cookies_db(cookies_db, storage_state.get("cookies", []))

    # Write localStorage to LevelDB
    for origin in storage_state.get("origins", []):
        ls_path = f"{profile_path}/Default/Local Storage/leveldb"
        await write_localstorage_leveldb(ls_path, origin)
```

### FR-3: Session Injection at Sandbox Start

When sandbox starts with browserSession:

1. Fetch session (inline or from store)
2. Convert to agent-browser profile
3. Write profile to `/workspace/.browser-profile`
4. Set `AGENT_BROWSER_PROFILE=/workspace/.browser-profile`
5. Agent can now use authenticated browser

### FR-4: Janus Gateway Integration

Add session parameter to chat requests:

```json
POST /v1/chat/completions
{
  "model": "baseline-cli-agent",
  "messages": [...],
  "browser_session_id": "uuid"  // Optional
}
```

Gateway passes session to baseline agent → Sandy.

### FR-5: Baseline Agent Updates

Update system prompt to inform agent about available session:

```markdown
## Browser Session

You have an authenticated browser session available for the following domains:
- twitter.com
- x.com

To use this session, run agent-browser commands without manual login:
```bash
agent-browser open https://twitter.com
# You should already be logged in
```
```

### FR-6: Session Validation

Before injection, validate:
- Session not expired
- User owns the session
- Session domains match requested task (optional)

## Technical Approach

### Sandy Changes

1. **Sandbox creation:**
   - Accept `browserSession` in create request
   - Fetch/convert/inject before container start

2. **Profile injection:**
   - Use Sandy file write API to create profile
   - Set environment variable for agent-browser

3. **Cleanup:**
   - Profile is ephemeral (in sandbox)
   - No persistence needed

### Profile Format

agent-browser uses Chrome user data directory format:

```
.browser-profile/
├── Default/
│   ├── Cookies        # SQLite database
│   ├── Local Storage/
│   │   └── leveldb/   # LevelDB for localStorage
│   └── Preferences    # JSON config
```

### Cookie SQLite Schema

```sql
CREATE TABLE cookies (
    creation_utc INTEGER NOT NULL,
    host_key TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    path TEXT NOT NULL,
    expires_utc INTEGER NOT NULL,
    is_secure INTEGER NOT NULL,
    is_httponly INTEGER NOT NULL,
    last_access_utc INTEGER NOT NULL,
    has_expires INTEGER NOT NULL DEFAULT 1,
    is_persistent INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 1,
    encrypted_value BLOB DEFAULT '',
    samesite INTEGER NOT NULL DEFAULT -1,
    source_scheme INTEGER NOT NULL DEFAULT 0,
    source_port INTEGER NOT NULL DEFAULT -1,
    is_same_party INTEGER NOT NULL DEFAULT 0,
    last_update_utc INTEGER NOT NULL DEFAULT 0
);
```

## Acceptance Criteria

- [ ] Sandy accepts browserSession in create request
- [ ] Inline storageState injection works
- [ ] Session store reference injection works
- [ ] agent-browser uses injected profile
- [ ] Baseline agent receives session info in prompt
- [ ] Janus gateway passes session_id to baseline
- [ ] Session validation prevents unauthorized use
- [ ] Unit tests for profile conversion
- [ ] Integration test for full flow

## API Examples

### Create Sandbox with Session

```bash
curl -X POST https://sandy.../api/sandboxes \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "flavor": "agent-ready",
    "browserSession": {
      "type": "inline",
      "storageState": {
        "cookies": [
          {"name": "session", "value": "abc", "domain": ".twitter.com", ...}
        ],
        "origins": []
      }
    }
  }'
```

### Agent Using Session

```bash
# Inside sandbox
agent-browser open https://twitter.com
# → Automatically logged in due to injected cookies

agent-browser snapshot
# → Shows authenticated view
```

## Notes

- Profile conversion should be fast (<1s)
- Consider caching converted profiles
- Consider profile compression for large sessions
- Security: sessions should be user-scoped

---

*Reference: docs/browser-user-session-pre-research.md*
*Depends on: Spec 119 (session store), Spec 120 (agent-ready sandbox)*
