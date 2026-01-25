#!/bin/bash
# Bootstrap script run when agent starts in sandbox

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
  chmod +x /agent-pack/bin/*
fi

# Start artifact server
export JANUS_ARTIFACTS_DIR="${JANUS_ARTIFACTS_DIR:-/workspace/artifacts}"
export JANUS_ARTIFACT_PORT="${JANUS_ARTIFACT_PORT:-8787}"
mkdir -p "$JANUS_ARTIFACTS_DIR"
mkdir -p "${JANUS_SCREENSHOT_DIR:-/workspace/artifacts/screenshots}"

# Install Playwright for browser automation
if ! python3 - <<'PY' >/dev/null 2>&1
import playwright  # noqa: F401
PY
then
  pip install playwright
fi
python3 -m playwright install chromium

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

# Start the model router in the background
echo "Starting Janus Model Router..."
python3 -m janus_baseline_agent_cli.router.server >/workspace/router.log 2>&1 &
ROUTER_PID=$!

# Wait for router to be ready
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "Router ready!"
    break
  fi
  sleep 0.5
done

# Configure agent to use local router
export OPENAI_API_BASE="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="${CHUTES_API_KEY}"
export OPENAI_MODEL="janus-router"

# Cleanup on exit
trap "kill $ROUTER_PID 2>/dev/null" EXIT

# Set up environment
export PYTHONDONTWRITEBYTECODE=1
export NODE_NO_WARNINGS=1
export PYTHONPATH="/workspace/lib:${PYTHONPATH:-}"

echo "Agent pack initialized. Reference docs available at /workspace/docs/"
