# Spec 42: Sandbox File Serving & Public URLs

## Status: COMPLETE

## Context / Why

When the agent creates files (images, documents, code, etc.), users need to access them. Currently, there's no standardized way for the agent to serve files and generate accessible URLs. We need:

1. A webserver running in each sandbox to serve files
2. A way for the agent to know its public URL
3. URL patterns that work for both inline and downloadable content

## Goals

- Run HTTP server in sandbox for artifact serving
- Provide agent with its public sandbox URL
- Support multiple file access patterns
- Enable streaming of large files
- Maintain security (no directory traversal, etc.)

## Non-Goals

- Persistent file storage (handled by gateway artifacts)
- Authentication for file access (public within session)
- CDN or caching layer

## Functional Requirements

### FR-1: Sandbox HTTP Server

Each sandbox runs a lightweight HTTP server for file serving:

```python
# Sandy bootstrap script addition
# bootstrap.sh or equivalent

# Start artifact server on the Sandy runtime port (default 5173)
python3 -m http.server 5173 --directory /workspace/artifacts &
ARTIFACT_SERVER_PID=$!
echo "Artifact server started on port 5173 (PID: $ARTIFACT_SERVER_PID)"

# Or use a more robust server
cat > /workspace/serve_artifacts.py << 'EOF'
#!/usr/bin/env python3
"""Simple artifact server with CORS and proper MIME types."""

import os
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler

class ArtifactHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/workspace/artifacts", **kwargs)

    def end_headers(self):
        # Add CORS headers for frontend access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    os.makedirs("/workspace/artifacts", exist_ok=True)
    server = HTTPServer(("0.0.0.0", 5173), ArtifactHandler)
    print("Artifact server running on port 5173")
    server.serve_forever()
EOF

python3 /workspace/serve_artifacts.py &
```

### FR-2: Sandy Proxy Configuration

Sandy proxies only the sandbox runtime port (default 5173) behind the
`https://{sandbox_id}.sandy...` host. The artifact server must bind to that
runtime port so `/artifacts/*` is reachable via the public sandbox URL.

```yaml
# Sandy configuration (conceptual)
sandbox:
  runtime_port: 5173  # proxied behind sandbox subdomain
  url_pattern: "https://sandbox-{sandbox_id}.sandy.janus.rodeo"
  artifact_path: "/artifacts/*"

  # Full artifact URL:
  # https://sandbox-{sandbox_id}.sandy.janus.rodeo/artifacts/{filename}
```

### FR-3: Environment Variables for Agent

Provide the agent with its public URLs:

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py

async def _create_sandbox(self, client: httpx.AsyncClient) -> tuple[str, str]:
    """Create sandbox and return (sandbox_id, public_url)."""
    response = await client.post(
        f"{self._base_url}/api/sandboxes",
        json={
            "priority": "NORMAL",
            "ttl_seconds": self._timeout,
            # Sandy proxies the runtime port, so the artifact server binds there.
        },
        headers=self._get_headers(),
    )
    data = response.json()
    sandbox_id = data.get("sandbox_id") or data.get("id")

    # Sandy should return the public URL
    public_url = data.get("public_url") or f"{self._base_url}/sandbox/{sandbox_id}"

    return str(sandbox_id), public_url


def _build_agent_env(self, sandbox_id: str, public_url: str) -> dict:
    """Build environment with public URL info."""
    return {
        # ... existing vars ...

        # Sandbox public access
        "JANUS_SANDBOX_ID": sandbox_id,
        "JANUS_SANDBOX_PUBLIC_URL": public_url,
        "JANUS_ARTIFACT_URL_BASE": f"{public_url}/artifacts",

        # Directory paths
        "JANUS_ARTIFACTS_DIR": "/workspace/artifacts",
    }
```

### FR-4: Agent Helper Functions

Provide utility functions for the agent to create artifact URLs:

```python
# agent-pack/lib/artifacts.py (uploaded to sandbox)

import os
import base64
import mimetypes
from pathlib import Path

ARTIFACTS_DIR = Path(os.environ.get("JANUS_ARTIFACTS_DIR", "/workspace/artifacts"))
ARTIFACT_URL_BASE = os.environ.get("JANUS_ARTIFACT_URL_BASE", "/artifacts")


def save_artifact(filename: str, content: bytes | str, mime_type: str = None) -> str:
    """
    Save content as an artifact and return its URL.

    Args:
        filename: Name for the artifact file
        content: File content (bytes or string)
        mime_type: Optional MIME type (auto-detected if not provided)

    Returns:
        URL to access the artifact
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    filepath = ARTIFACTS_DIR / filename

    if isinstance(content, str):
        filepath.write_text(content)
    else:
        filepath.write_bytes(content)

    return f"{ARTIFACT_URL_BASE}/{filename}"


def artifact_to_base64(filepath: str) -> str:
    """
    Convert a file to a base64 data URL.

    Best for small files (< 500KB) that should be inline.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "application/octet-stream"

    content = path.read_bytes()
    b64 = base64.b64encode(content).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"


def create_download_link(filename: str, display_name: str = None) -> str:
    """
    Create a markdown download link for an artifact.

    Args:
        filename: Artifact filename
        display_name: Text to show (defaults to filename)

    Returns:
        Markdown link string
    """
    display = display_name or filename
    url = f"{ARTIFACT_URL_BASE}/{filename}"
    return f"[{display}]({url})"


def create_image_embed(filename: str, alt_text: str = "Image") -> str:
    """
    Create markdown image embed for an artifact.

    For small images, uses base64 inline. For larger, uses URL.
    """
    filepath = ARTIFACTS_DIR / filename

    # If small enough, inline it
    if filepath.stat().st_size < 500_000:  # 500KB
        data_url = artifact_to_base64(str(filepath))
        return f"![{alt_text}]({data_url})"
    else:
        url = f"{ARTIFACT_URL_BASE}/{filename}"
        return f"![{alt_text}]({url})"
```

### FR-5: Bootstrap Script Enhancement

Update the sandbox bootstrap to start the artifact server:

```bash
#!/bin/bash
# agent-pack/bootstrap.sh

set -e

echo "🚀 Bootstrapping Janus agent environment..."

# Create artifacts directory
mkdir -p /workspace/artifacts

# Start artifact server in background
echo "📦 Starting artifact server on port 5173..."
python3 << 'ARTIFACT_SERVER' &
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

class CORSHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/workspace/artifacts", **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs

os.makedirs("/workspace/artifacts", exist_ok=True)
HTTPServer(("0.0.0.0", 5173), CORSHandler).serve_forever()
ARTIFACT_SERVER

echo "✅ Artifact server running"

# Copy agent pack files
echo "📁 Setting up agent pack..."
cp -r /agent-pack/docs /workspace/docs 2>/dev/null || true
cp -r /agent-pack/lib /workspace/lib 2>/dev/null || true

# Install Python helpers
pip install -q httpx pillow 2>/dev/null || true

echo "✅ Bootstrap complete"
```

### FR-6: URL Resolution in Response Processing

The baseline needs to resolve relative artifact URLs to absolute:

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/response_processor.py

import re
from typing import Optional


def resolve_artifact_urls(
    content: str,
    artifact_base_url: str
) -> str:
    """
    Resolve relative /artifacts/ URLs to absolute URLs.

    Args:
        content: Response content with potential artifact references
        artifact_base_url: Base URL for artifacts (e.g., https://sandbox-xxx.sandy.janus.rodeo/artifacts)

    Returns:
        Content with resolved URLs
    """
    # Pattern for /artifacts/filename references
    pattern = r'(\[.*?\]\()/artifacts/([^)]+)\)'

    def replace_url(match):
        prefix = match.group(1)
        filename = match.group(2)
        return f'{prefix}{artifact_base_url}/{filename})'

    return re.sub(pattern, replace_url, content)


def process_agent_response(
    content: str,
    sandbox_url: str,
    gateway_url: str
) -> str:
    """
    Process agent response to resolve all URLs.
    """
    # Resolve artifact URLs
    content = resolve_artifact_urls(content, f"{sandbox_url}/artifacts")

    # Could also upload artifacts to gateway for persistence
    # content = upload_and_replace_artifacts(content, gateway_url)

    return content
```

## Non-Functional Requirements

### NFR-1: Performance

- Artifact server should handle concurrent requests
- Large files streamed, not loaded into memory
- Startup time < 2 seconds

### NFR-2: Security

- No directory traversal (chroot to artifacts dir)
- CORS headers for frontend access
- No execution of uploaded files

### NFR-3: Reliability

- Server auto-restarts if crashed
- Graceful handling of missing files (404)
- Proper MIME type detection

## Acceptance Criteria

- [ ] HTTP server runs on port 5173 in sandbox
- [ ] Agent can write files to /workspace/artifacts
- [ ] Files accessible via public URL
- [ ] CORS enabled for frontend access
- [ ] Helper functions available to agent
- [ ] URLs resolved in response processing
- [ ] Works with images, documents, code files

## Files to Create/Modify

```
baseline-agent-cli/
├── agent-pack/
│   ├── bootstrap.sh          # MODIFY - Start artifact server
│   └── lib/
│       └── artifacts.py      # NEW - Helper functions
├── janus_baseline_agent_cli/
│   └── services/
│       ├── sandy.py          # MODIFY - Pass public URL
│       └── response_processor.py  # NEW - URL resolution
```

## Related Specs

- `specs/41_enhanced_agent_system_prompt.md` - Agent capabilities
- `specs/43_agent_sandbox_management.md` - Sandbox creation

NR_OF_TRIES: 1
