# Spec 119: Browser Session Storage Service

## Status: TODO

## Priority: HIGH

## Context / Why

Based on research in spec 118, we need a backend service to store and manage browser sessions for Janus agents. Users should be able to save named sessions ("MyTwitter", "MyGitHub") that can be injected into agent sandboxes for authenticated browser automation.

**Reference:** `docs/browser-user-session-pre-research.md` and `docs/browser-session-research-results.md`

## Goals

1. Create a FastAPI backend service for browser session CRUD
2. Store sessions encrypted in Neon Postgres
3. Integrate with Chutes IDP for user authentication
4. Provide REST API for session management

## Non-Goals

- Session capture UI (that's spec 121)
- Sandy integration (that's spec 122)
- VNC viewer components

## Functional Requirements

### FR-1: Database Schema

```sql
CREATE TABLE browser_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,           -- Chutes IDP user ID (from JWT sub)
    name TEXT NOT NULL,              -- User-provided name
    description TEXT,                -- Optional description
    domains TEXT[] NOT NULL,         -- Domains covered by this session
    storage_state_encrypted BYTEA NOT NULL,  -- AES-256-GCM encrypted JSON
    iv BYTEA NOT NULL,               -- Initialization vector for encryption
    expires_at TIMESTAMPTZ,          -- Optional expiration
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX idx_browser_sessions_user_id ON browser_sessions(user_id);
```

### FR-2: Encryption

- Use AES-256-GCM for storage_state encryption
- Derive key from user's Chutes IDP identity + server secret
- Store IV alongside encrypted data
- Key derivation: `HKDF(server_secret, user_id, "browser-session")`

### FR-3: REST API Endpoints

```
POST /sessions
  - Create new session
  - Body: { name, description?, domains, storage_state }
  - Encrypts and stores

GET /sessions
  - List user's sessions
  - Returns: [{ id, name, description, domains, created_at }]
  - Does NOT return storage_state

GET /sessions/{id}
  - Get session details (no storage_state)

GET /sessions/{id}/state
  - Get decrypted storage_state
  - Returns: { cookies: [...], origins: [...] }

PUT /sessions/{id}
  - Update session (name, description, storage_state)

DELETE /sessions/{id}
  - Delete session

GET /sessions/by-name/{name}
  - Get session by name for current user
```

### FR-4: Authentication

- Require valid Chutes IDP JWT token
- Extract user_id from JWT sub claim
- Validate token signature and expiration

### FR-5: Validation

- Session name: alphanumeric + dashes, max 50 chars
- Description: max 500 chars
- Domains: valid domain format, max 10 domains
- Storage state: valid JSON, max 1MB

## Technical Approach

### Project Structure

```
browser-session-service/
├── pyproject.toml
├── browser_session_service/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── auth.py              # JWT validation
│   ├── crypto.py            # Encryption/decryption
│   ├── models.py            # Pydantic models
│   ├── db.py                # Database operations
│   └── routes/
│       └── sessions.py      # Session CRUD routes
└── tests/
    ├── test_crypto.py
    ├── test_sessions.py
    └── conftest.py
```

### Dependencies

- FastAPI + uvicorn
- asyncpg (async Postgres)
- python-jose (JWT)
- cryptography (AES-GCM)
- pydantic

### Environment Variables

```
DATABASE_URL=postgres://...
SESSION_ENCRYPTION_SECRET=... (32 bytes, base64)
CHUTES_IDP_JWKS_URL=https://idp.chutes.ai/.well-known/jwks.json
```

## Acceptance Criteria

- [ ] FastAPI service with session CRUD endpoints
- [ ] Neon Postgres schema deployed
- [ ] AES-256-GCM encryption/decryption working
- [ ] JWT authentication with Chutes IDP
- [ ] Unit tests for crypto and API
- [ ] Deployed on Render
- [ ] Health check endpoint `/health`

## API Examples

### Create Session

```bash
curl -X POST https://session-service/sessions \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyTwitter",
    "description": "Personal Twitter account",
    "domains": ["twitter.com", "x.com"],
    "storage_state": {
      "cookies": [...],
      "origins": [...]
    }
  }'
```

### Get Session State (for injection)

```bash
curl https://session-service/sessions/{id}/state \
  -H "Authorization: Bearer $JWT"
```

## Notes

- Consider adding rate limiting
- Consider session sharing between users (future)
- Consider audit logging for security

---

*Reference: docs/browser-user-session-pre-research.md*
*Depends on: Spec 118 research results*
