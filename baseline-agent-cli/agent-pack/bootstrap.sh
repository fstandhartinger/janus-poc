#!/bin/bash
# Bootstrap script run when agent starts in sandbox

set -e  # Exit on error

echo "=== Janus Agent Pack Bootstrap ==="
echo "Starting at: $(date)"

# Create docs directory structure
mkdir -p /workspace/docs/models

# Copy reference documentation
cp /agent-pack/models/*.md /workspace/docs/models/

# Copy helper libraries
if [ -d /agent-pack/lib ]; then
  mkdir -p /workspace/lib
  cp -r /agent-pack/lib/* /workspace/lib/ 2>/dev/null || true
fi

# Ensure agent binaries are executable
if [ -d /agent-pack/bin ]; then
  chmod +x /agent-pack/bin/* 2>/dev/null || true
fi

# Start artifact server
export JANUS_ARTIFACTS_DIR="${JANUS_ARTIFACTS_DIR:-/workspace/artifacts}"
export JANUS_ARTIFACT_PORT="${JANUS_ARTIFACT_PORT:-8787}"
mkdir -p "$JANUS_ARTIFACTS_DIR"
mkdir -p "${JANUS_SCREENSHOT_DIR:-/workspace/artifacts/screenshots}"

# Helper function to install pip packages with fallbacks for externally-managed-environment
pip_install() {
  echo "Installing: $*"
  pip install --user "$@" 2>/dev/null || \
    pip install --break-system-packages "$@" 2>/dev/null || \
    pip install "$@"
}

# Install Playwright for browser automation
echo "=== Installing Playwright ==="
if ! python3 - <<'PY' >/dev/null 2>&1
import playwright  # noqa: F401
PY
then
  pip_install playwright
fi
python3 -m playwright install chromium 2>/dev/null || echo "Playwright chromium install skipped"

# Install aider-chat for intelligent CLI agent capabilities
echo "=== Installing aider-chat ==="
if ! command -v aider >/dev/null 2>&1; then
  pip_install aider-chat
  # Ensure ~/.local/bin is in PATH (where pip --user installs to)
  export PATH="$HOME/.local/bin:/root/.local/bin:$PATH"
fi

# Verify aider installation
echo "=== Verifying agent installations ==="
echo "PATH=$PATH"

if command -v aider >/dev/null 2>&1; then
  AIDER_PATH=$(which aider)
  echo "aider found at: $AIDER_PATH"
  # Verify it's the real aider, not a wrapper
  if file "$AIDER_PATH" 2>/dev/null | grep -q "Python script"; then
    echo "aider is a Python script (real installation)"
  elif file "$AIDER_PATH" 2>/dev/null | grep -q "shell script"; then
    echo "WARNING: aider appears to be a shell script wrapper"
  fi
else
  echo "WARNING: aider not found in PATH after installation"
  echo "Searching for aider..."
  find /root/.local -name "aider" -type f 2>/dev/null | head -5
  find /usr/local -name "aider" -type f 2>/dev/null | head -5
fi

# Check for Claude Code
if command -v claude >/dev/null 2>&1; then
  echo "claude (Claude Code) found at: $(which claude)"
else
  echo "claude (Claude Code) not installed"
fi

# Check for other agents
for agent in opencode openhands; do
  if command -v "$agent" >/dev/null 2>&1; then
    echo "$agent found at: $(which $agent)"
  else
    echo "$agent not installed"
  fi
done

start_artifact_server() {
  python3 - <<'PY'
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

directory = os.environ.get("JANUS_ARTIFACTS_DIR", "/workspace/artifacts")
port = int(os.environ.get("JANUS_ARTIFACT_PORT", "8787"))


class CORSHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return


os.makedirs(directory, exist_ok=True)
HTTPServer(("0.0.0.0", port), CORSHandler).serve_forever()
PY
}

(
  while true; do
    start_artifact_server
    sleep 1
  done
) >/workspace/artifact_server.log 2>&1 &

# Install router dependencies
echo "=== Installing Router Dependencies ==="
pip_install httpx structlog fastapi uvicorn pydantic

# Start the model router in the background
echo "=== Starting Janus Model Router ==="
cd /agent-pack/router && python3 -c "import uvicorn; uvicorn.run('server:app', host='0.0.0.0', port=8000, log_level='info')" >/workspace/router.log 2>&1 &
ROUTER_PID=$!
cd /workspace

# Wait for router to be ready
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "Router ready!"
    break
  fi
  sleep 0.5
done

# Configure agents to use local router
# OpenAI-compatible agents (Aider, Codex, etc.)
export OPENAI_API_BASE="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="${CHUTES_API_KEY}"
export OPENAI_MODEL="janus-router"

# Anthropic-compatible agents (Claude Code)
export ANTHROPIC_BASE_URL="http://127.0.0.1:8000"
export ANTHROPIC_API_KEY="${CHUTES_API_KEY}"

# Configure Claude Code settings for model router
if command -v claude >/dev/null 2>&1; then
  echo "=== Configuring Claude Code ==="
  mkdir -p ~/.claude
  cat > ~/.claude/settings.json <<EOF
{
  "apiBaseUrl": "http://127.0.0.1:8000",
  "defaultModel": "janus-router",
  "alwaysThinkingEnabled": true,
  "API_TIMEOUT_MS": 600000,
  "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
}
EOF
  # Also set environment variables for Claude Code CLI
  export CLAUDE_API_BASE_URL="http://127.0.0.1:8000"
  export CLAUDE_MODEL="janus-router"
  echo "Claude Code configured to use local router"
fi

# Cleanup on exit
trap "kill $ROUTER_PID 2>/dev/null" EXIT

# Set up environment
export PYTHONDONTWRITEBYTECODE=1
export NODE_NO_WARNINGS=1
export PYTHONPATH="/workspace/lib:${PYTHONPATH:-}"

echo "=== Bootstrap Complete ==="
echo "Workspace: /workspace"
echo "Agent pack: /agent-pack"
echo "Reference docs: /workspace/docs/"
echo "Available agents:"
ls -la /root/.local/bin/ 2>/dev/null | head -10 || echo "  (none in /root/.local/bin)"
