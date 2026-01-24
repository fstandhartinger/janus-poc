#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Starting containers..."
docker-compose up -d

echo "Waiting for services to be ready..."
sleep 10

echo "Testing baseline-agent-cli..."
curl -s http://localhost:8081/health | jq .

echo "Testing baseline-langchain..."
curl -s http://localhost:8082/health | jq .

echo ""
echo "Services running:"
echo "  - baseline-agent-cli: http://localhost:8081"
echo "  - baseline-langchain: http://localhost:8082"
echo "  - gateway: http://localhost:8000"
