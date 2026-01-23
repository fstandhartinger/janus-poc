# Janus Gateway

OpenAI-compatible AI agent gateway for the Janus competitive network.

## Features

- OpenAI Chat Completions API compatibility
- SSE streaming with keep-alives
- Competitor registry and routing
- Artifact storage and retrieval
- Janus extensions (reasoning_content, artifacts)

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Running

```bash
# Development mode
python -m janus_gateway.main

# Or with uvicorn directly
uvicorn janus_gateway.main:app --reload
```

## Testing

```bash
pytest
```

## API Endpoints

- `GET /health` - Health check
- `GET /v1/models` - List available models/competitors
- `POST /v1/chat/completions` - Chat completions (streaming supported)
- `GET /v1/artifacts/{id}` - Retrieve stored artifacts

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JANUS_HOST` | `0.0.0.0` | Server host |
| `JANUS_PORT` | `8000` | Server port |
| `JANUS_DEBUG` | `false` | Enable debug mode |
| `JANUS_LOG_LEVEL` | `INFO` | Log level |
| `JANUS_BASELINE_URL` | `https://janus-baseline-agent-cli.onrender.com` | Baseline competitor base URL |
| `JANUS_BASELINE_LANGCHAIN_URL` | `http://localhost:8002` | Baseline LangChain competitor base URL |
| `JANUS_SANDY_BASE_URL` | - | Sandy API base URL |
| `JANUS_SANDY_API_KEY` | - | Sandy API key |

`BASELINE_AGENT_CLI_URL` and `BASELINE_URL` are accepted as aliases for `JANUS_BASELINE_URL`. `BASELINE_LANGCHAIN_URL` is accepted as an alias for `JANUS_BASELINE_LANGCHAIN_URL`.
