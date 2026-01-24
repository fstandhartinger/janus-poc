#!/bin/bash
# Bootstrap script run when agent starts in sandbox

# Create docs directory structure
mkdir -p /workspace/docs/models

# Copy reference documentation
cp /agent-pack/models/*.md /workspace/docs/models/

# Ensure agent binaries are executable
if [ -d /agent-pack/bin ]; then
  chmod +x /agent-pack/bin/*
fi

# Start artifact server
ARTIFACTS_DIR="${JANUS_ARTIFACTS_DIR:-/workspace/artifacts}"
ARTIFACT_PORT="${JANUS_ARTIFACT_PORT:-8787}"
mkdir -p "$ARTIFACTS_DIR"
python3 -m http.server "$ARTIFACT_PORT" --directory "$ARTIFACTS_DIR" >/workspace/artifact_server.log 2>&1 &

# Set up environment
export PYTHONDONTWRITEBYTECODE=1
export NODE_NO_WARNINGS=1

echo "Agent pack initialized. Reference docs available at /workspace/docs/"
