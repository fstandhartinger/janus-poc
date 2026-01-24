#!/bin/bash
set -e

REGISTRY="${REGISTRY:-ghcr.io/janus}"
VERSION="${VERSION:-latest}"

echo "Building baseline-agent-cli..."
docker build -t ${REGISTRY}/baseline-agent-cli:${VERSION} ./baseline-agent-cli

echo "Building baseline-langchain..."
docker build -t ${REGISTRY}/baseline-langchain:${VERSION} ./baseline-langchain

echo "Building gateway..."
docker build -t ${REGISTRY}/gateway:${VERSION} ./gateway

echo "All containers built successfully!"
echo ""
echo "To push to registry:"
echo "  docker push ${REGISTRY}/baseline-agent-cli:${VERSION}"
echo "  docker push ${REGISTRY}/baseline-langchain:${VERSION}"
echo "  docker push ${REGISTRY}/gateway:${VERSION}"
