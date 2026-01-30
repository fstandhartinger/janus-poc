# Janus Browser Session Service

Secure storage and management of browser sessions for Janus agents. This service allows users to save authenticated browser sessions that can be injected into agent sandboxes for browser automation tasks.

## Features

- **Secure Storage**: Sessions encrypted with AES-256-GCM using per-user derived keys
- **Chutes IDP Authentication**: JWT-based authentication with Chutes identity provider
- **RESTful API**: Full CRUD operations for browser sessions
- **Playwright Compatible**: Storage state format compatible with Playwright

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions` | Create a new session |
| GET | `/sessions` | List all sessions (metadata only) |
| GET | `/sessions/{id}` | Get session details |
| GET | `/sessions/{id}/state` | Get decrypted storage state |
| PUT | `/sessions/{id}` | Update session |
| DELETE | `/sessions/{id}` | Delete session |
| GET | `/sessions/by-name/{name}` | Get session by name |
| GET | `/health` | Health check |

## Storage State Format

Sessions store Playwright-compatible storage state:

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
        {"name": "auth_token", "value": "xyz789"}
      ]
    }
  ]
}
```

## Security

- Sessions are encrypted using AES-256-GCM
- Per-user encryption keys derived via HKDF from server secret + user ID
- Only authenticated users can access their own sessions
- Storage state never logged or exposed without decryption

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | sqlite (dev only) |
| `SESSION_ENCRYPTION_SECRET` | Base64-encoded 32-byte secret | Required |
| `CHUTES_IDP_JWKS_URL` | Chutes IDP JWKS endpoint | https://idp.chutes.ai/.well-known/jwks.json |
| `CHUTES_IDP_ISSUER` | Expected JWT issuer | https://idp.chutes.ai |
| `CHUTES_IDP_AUDIENCE` | Expected JWT audience | janus |
| `SESSION_INIT_DB` | Initialize database tables on startup | false |
| `SESSION_LOG_LEVEL` | Logging level | INFO |

## Development

```bash
# Install dependencies
cd browser-session-service
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Generate encryption secret
python -c "from browser_session_service.crypto import generate_secret; print(generate_secret())"

# Run tests
pytest -v

# Run locally
SESSION_ENCRYPTION_SECRET="..." SESSION_INIT_DB=true uvicorn browser_session_service.main:app --reload
```

## Deployment

The service is deployed to Render as part of the Janus platform. See `render.yaml` for configuration.

## References

- [Spec 119: Browser Session Storage Service](../specs/119_browser_session_store.md)
- [Browser Session Research Results](../docs/browser-session-research-results.md)
