#!/bin/bash
# Bootstrap script run when agent starts in sandbox

# Create docs directory structure
mkdir -p /workspace/docs/models

# Copy reference documentation
cp /agent-pack/models/*.md /workspace/docs/models/

# Set up environment
export PYTHONDONTWRITEBYTECODE=1
export NODE_NO_WARNINGS=1

echo "Agent pack initialized. Reference docs available at /workspace/docs/"
