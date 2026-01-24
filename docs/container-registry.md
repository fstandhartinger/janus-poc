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
