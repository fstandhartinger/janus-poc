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

# Set up environment
export PYTHONDONTWRITEBYTECODE=1
export NODE_NO_WARNINGS=1
export PYTHONPATH="/workspace/lib:${PYTHONPATH:-}"

echo "Agent pack initialized. Reference docs available at /workspace/docs/"
