# Janus Baseline Competitor

Reference implementation for the Janus competitive network.

## Features

- OpenAI-compatible `/v1/chat/completions` endpoint
- Fast-path for simple prompts (direct LLM call)
- Complex-path with Sandy sandbox for CLI agent execution
- SSE streaming with reasoning_content
- Artifact generation for file outputs

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
python -m janus_baseline.main

# Or with uvicorn directly
uvicorn janus_baseline.main:app --port 8001 --reload
```

## Testing

```bash
pytest
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASELINE_HOST` | `0.0.0.0` | Server host |
| `BASELINE_PORT` | `8001` | Server port |
| `BASELINE_DEBUG` | `false` | Enable debug mode |
| `BASELINE_OPENAI_API_KEY` | - | OpenAI API key for LLM calls |
| `BASELINE_OPENAI_BASE_URL` | - | Custom OpenAI-compatible base URL |
| `BASELINE_MODEL` | `gpt-4o-mini` | Default model for fast path |
| `BASELINE_AGENT_PACK_PATH` | `./agent-pack` | Path to the baseline agent pack |
| `BASELINE_SYSTEM_PROMPT_PATH` | `./agent-pack/prompts/system.md` | System prompt for the CLI agent |
| `BASELINE_ENABLE_WEB_SEARCH` | `true` | Enable web search tools |
| `BASELINE_ENABLE_CODE_EXECUTION` | `true` | Enable code execution tools |
| `BASELINE_ENABLE_FILE_TOOLS` | `true` | Enable file tooling |
| `SANDY_BASE_URL` | - | Sandy API base URL |
| `SANDY_API_KEY` | - | Sandy API key |
