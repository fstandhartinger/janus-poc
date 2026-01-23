# Spec 54: Baseline Containerization for Sandy Execution

## Status: DRAFT

## Context / Why

The reference architecture (Spec 02) specifies that **competitor containers run in isolated environments**. The competitor submission spec (Spec 10) requires:

- Container exposes HTTP on port **8080**
- Container accepts configuration via environment variables
- Container starts and is ready within 30 seconds
- Container handles at least 2 concurrent requests

Currently, the baseline implementations (`baseline-agent-cli` and `baseline-langchain`) are Python packages that run directly via uvicorn, but they are **not containerized**. This means:

1. They cannot be tested as real competitor submissions
2. They cannot be deployed inside Sandy sandboxes as intended
3. Miners cannot use them as reference Docker images

The intended flow is:
```
Gateway → Sandy Sandbox (Firecracker VM) → Docker Container (Baseline)
```

Sandy sandboxes run on Firecracker VMs and can run Docker containers inside them. The baselines should be packaged as Docker images that can be pulled and run within these sandboxes.

## Goals

- Create Dockerfiles for both baseline implementations
- Ensure containers follow competitor submission spec (port 8080)
- Enable running baselines inside Sandy sandboxes
- Provide docker-compose for local testing
- Document the container build and deployment process

## Non-Goals

- Changing the baseline implementation logic
- Full CI/CD pipeline (separate spec)
- Container registry management (separate spec)

## Functional Requirements

### FR-1: Baseline Agent CLI Dockerfile

```dockerfile
# baseline-agent-cli/Dockerfile

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
COPY janus_baseline_agent_cli/__init__.py janus_baseline_agent_cli/
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir .

# Copy application code
COPY . .

# Install package in development mode for all modules
RUN pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=builder /app /app

# Copy agent-pack for reference docs
COPY agent-pack /agent-pack

# Environment configuration
ENV HOST=0.0.0.0
ENV PORT=8080
ENV LOG_LEVEL=INFO
ENV DEBUG=false

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose competitor port
EXPOSE 8080

# Run the server
CMD ["python", "-m", "janus_baseline_agent_cli.main"]
```

### FR-2: Baseline LangChain Dockerfile

```dockerfile
# baseline-langchain/Dockerfile

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
COPY janus_baseline_langchain/__init__.py janus_baseline_langchain/
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir .

# Copy application code
COPY . .

# Install package
RUN pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=builder /app /app

# Environment configuration
ENV HOST=0.0.0.0
ENV PORT=8080
ENV LOG_LEVEL=INFO
ENV DEBUG=false

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose competitor port
EXPOSE 8080

# Run the server
CMD ["python", "-m", "janus_baseline_langchain.main"]
```

### FR-3: Configuration Updates

Ensure the baselines respect PORT environment variable:

```python
# baseline-agent-cli/janus_baseline_agent_cli/config.py

class Settings(BaseSettings):
    """Application settings."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")  # Changed from 8000 to 8080

    # ... rest of settings
```

```python
# baseline-langchain/janus_baseline_langchain/config.py

class Settings(BaseSettings):
    """Application settings."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")  # Changed from 8000 to 8080

    # ... rest of settings
```

### FR-4: Docker Compose for Local Testing

```yaml
# docker-compose.yml (root level)

version: '3.8'

services:
  baseline-agent-cli:
    build:
      context: ./baseline-agent-cli
      dockerfile: Dockerfile
    ports:
      - "8081:8080"
    environment:
      - CHUTES_API_KEY=${CHUTES_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - SANDY_BASE_URL=${SANDY_BASE_URL:-https://sandy.chutes.ai}
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  baseline-langchain:
    build:
      context: ./baseline-langchain
      dockerfile: Dockerfile
    ports:
      - "8082:8080"
    environment:
      - CHUTES_API_KEY=${CHUTES_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - TAVILY_API_KEY=${TAVILY_API_KEY:-}
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # Gateway for testing the full flow
  gateway:
    build:
      context: ./gateway
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - COMPETITOR_URL=http://baseline-agent-cli:8080
      - DEBUG=true
    depends_on:
      - baseline-agent-cli
    restart: unless-stopped
```

### FR-5: Gateway Dockerfile

```dockerfile
# gateway/Dockerfile

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY janus_gateway/__init__.py janus_gateway/
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir .

COPY . .
RUN pip install --no-cache-dir -e .

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

ENV HOST=0.0.0.0
ENV PORT=8000
ENV LOG_LEVEL=INFO

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "janus_gateway.main"]
```

### FR-6: Sandy Integration - Running Containers in Sandboxes

When the gateway needs to run a competitor container inside Sandy:

```python
# gateway/janus_gateway/services/competitor_runner.py

import httpx
from typing import AsyncIterator
import asyncio

class SandyCompetitorRunner:
    """Run competitor containers inside Sandy sandboxes."""

    def __init__(
        self,
        sandy_base_url: str,
        competitor_image: str,  # e.g., "ghcr.io/janus/baseline-agent-cli:latest"
        api_key: str
    ):
        self.sandy_base_url = sandy_base_url
        self.competitor_image = competitor_image
        self.api_key = api_key
        self.sandbox_id: str | None = None
        self.competitor_port = 8080

    async def start_sandbox(self) -> str:
        """Create a Sandy sandbox and start the competitor container."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create sandbox with Docker support
            response = await client.post(
                f"{self.sandy_base_url}/api/sandboxes",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "image": "sandy-docker",  # Sandy image with Docker support
                    "resources": {
                        "cpu": 2,
                        "memory_mb": 4096,
                        "disk_gb": 10
                    },
                    "env": {
                        "CHUTES_API_KEY": self.api_key,
                    }
                }
            )
            response.raise_for_status()
            self.sandbox_id = response.json()["sandbox_id"]

            # Pull and run the competitor container inside the sandbox
            await client.post(
                f"{self.sandy_base_url}/api/sandboxes/{self.sandbox_id}/exec",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "command": f"docker pull {self.competitor_image} && docker run -d -p {self.competitor_port}:{self.competitor_port} --name competitor {self.competitor_image}"
                }
            )

            # Wait for container to be ready
            await self._wait_for_ready()

            return self.sandbox_id

    async def _wait_for_ready(self, timeout: int = 30):
        """Wait for the competitor container to be ready."""
        start = asyncio.get_event_loop().time()
        async with httpx.AsyncClient() as client:
            while asyncio.get_event_loop().time() - start < timeout:
                try:
                    # Try health check via Sandy exec
                    response = await client.post(
                        f"{self.sandy_base_url}/api/sandboxes/{self.sandbox_id}/exec",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"command": f"curl -s http://localhost:{self.competitor_port}/health"}
                    )
                    result = response.json()
                    if result.get("exit_code") == 0 and "ok" in result.get("stdout", ""):
                        return
                except Exception:
                    pass
                await asyncio.sleep(1)
            raise TimeoutError("Competitor container failed to start")

    async def forward_request(self, request: dict) -> AsyncIterator[str]:
        """Forward a chat completion request to the competitor container."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Use Sandy's proxy to reach the container
            async with client.stream(
                "POST",
                f"{self.sandy_base_url}/api/sandboxes/{self.sandbox_id}/proxy/{self.competitor_port}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=request
            ) as response:
                async for line in response.aiter_lines():
                    yield line

    async def stop_sandbox(self):
        """Terminate the sandbox."""
        if self.sandbox_id:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.sandy_base_url}/api/sandboxes/{self.sandbox_id}/terminate",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
            self.sandbox_id = None
```

### FR-7: Build Scripts

```bash
# scripts/build-containers.sh

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
```

```bash
# scripts/run-local.sh

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
```

### FR-8: .dockerignore Files

```
# baseline-agent-cli/.dockerignore

__pycache__
*.pyc
*.pyo
*.egg-info
.git
.gitignore
.env
.venv
venv
.pytest_cache
.mypy_cache
.coverage
htmlcov
dist
build
*.md
!README.md
tests
.ruff_cache
```

```
# baseline-langchain/.dockerignore

__pycache__
*.pyc
*.pyo
*.egg-info
.git
.gitignore
.env
.venv
venv
.pytest_cache
.mypy_cache
.coverage
htmlcov
dist
build
*.md
!README.md
tests
.ruff_cache
```

### FR-9: Container Registry Documentation

```markdown
# docs/container-registry.md

# Janus Container Registry

## Available Images

| Image | Description | Port |
|-------|-------------|------|
| `ghcr.io/janus/baseline-agent-cli` | Agent CLI baseline | 8080 |
| `ghcr.io/janus/baseline-langchain` | LangChain baseline | 8080 |
| `ghcr.io/janus/gateway` | Janus Gateway | 8000 |

## Pulling Images

```bash
# Login to GitHub Container Registry (if private)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull images
docker pull ghcr.io/janus/baseline-agent-cli:latest
docker pull ghcr.io/janus/baseline-langchain:latest
```

## Running Locally

```bash
# Run baseline-agent-cli
docker run -p 8080:8080 \
  -e CHUTES_API_KEY=$CHUTES_API_KEY \
  ghcr.io/janus/baseline-agent-cli:latest

# Test health
curl http://localhost:8080/health

# Test chat completion
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"baseline","messages":[{"role":"user","content":"Hello"}]}'
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CHUTES_API_KEY` | Yes | Chutes API key for LLM access |
| `OPENAI_API_KEY` | No | OpenAI API key (fallback) |
| `SANDY_BASE_URL` | No | Sandy service URL |
| `LOG_LEVEL` | No | Logging level (DEBUG, INFO, etc.) |
| `DEBUG` | No | Enable debug mode |
```

## Non-Functional Requirements

### NFR-1: Container Size

- Base images should be < 500MB
- Use multi-stage builds to minimize size
- Only include runtime dependencies

### NFR-2: Startup Time

- Container must be ready within 30 seconds (per competitor spec)
- Health check should pass within 10 seconds of start

### NFR-3: Security

- Run as non-root user
- No secrets baked into images
- All secrets via environment variables

### NFR-4: Compatibility

- Containers run on Linux amd64
- Compatible with Sandy's Docker-in-Firecracker setup
- Work with standard Docker and Podman

## Acceptance Criteria

- [ ] Dockerfile exists for baseline-agent-cli
- [ ] Dockerfile exists for baseline-langchain
- [ ] Dockerfile exists for gateway
- [ ] docker-compose.yml works for local testing
- [ ] Containers start and pass health checks
- [ ] Containers expose port 8080 (baselines) / 8000 (gateway)
- [ ] Chat completions work through containerized baselines
- [ ] Build scripts documented
- [ ] .dockerignore files in place
- [ ] Configuration defaults to port 8080 for baselines

## Files to Create/Modify

```
baseline-agent-cli/
├── Dockerfile                    # NEW
├── .dockerignore                 # NEW
└── janus_baseline_agent_cli/
    └── config.py                 # MODIFY - Default port 8080

baseline-langchain/
├── Dockerfile                    # NEW
├── .dockerignore                 # NEW
└── janus_baseline_langchain/
    └── config.py                 # MODIFY - Default port 8080

gateway/
├── Dockerfile                    # NEW
└── .dockerignore                 # NEW

docker-compose.yml                # NEW
scripts/
├── build-containers.sh           # NEW
└── run-local.sh                  # NEW

docs/
└── container-registry.md         # NEW
```

## Related Specs

- `specs/02_architecture.md` - Reference architecture
- `specs/10_competitor_submission.md` - Competitor contract
- `specs/08_sandy_integration.md` - Sandy sandboxing
