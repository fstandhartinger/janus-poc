# Janus Baseline LangChain

An alternative Janus baseline implementation built on LangChain. This service runs fully in-process (no sandbox), exposes the OpenAI-compatible `/v1/chat/completions` endpoint, and uses tools for image generation, text-to-speech, web search, and safe code execution.

## Architecture

- **FastAPI API**: Handles OpenAI-compatible requests and SSE streaming.
- **LangChain Agent**: Uses `ChatOpenAI` with an OpenAI-tools agent.
- **Tools**:
  - `image_generation`: Chutes image generation API
  - `text_to_speech`: Chutes Kokoro TTS API
  - `web_search`: Tavily search API
  - `code_execution`: LangChain Python REPL tool

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASELINE_LANGCHAIN_HOST` | Server host | `0.0.0.0` |
| `BASELINE_LANGCHAIN_PORT` | Server port | `8002` |
| `BASELINE_LANGCHAIN_DEBUG` | Enable debug mode | `false` |
| `BASELINE_LANGCHAIN_MODEL` | LLM model name | `gpt-4o-mini` |
| `BASELINE_LANGCHAIN_OPENAI_API_KEY` | OpenAI API key | - |
| `BASELINE_LANGCHAIN_OPENAI_BASE_URL` | OpenAI-compatible base URL | `https://api.openai.com/v1` |
| `BASELINE_LANGCHAIN_CHUTES_API_KEY` | Chutes API key (image/TTS) | - |
| `BASELINE_LANGCHAIN_TAVILY_API_KEY` | Tavily API key (web search) | - |

## Run Locally

```bash
cd baseline-langchain
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m janus_baseline_langchain.main
```

The service listens on `http://localhost:8002`.

## Example Request

```bash
curl -N -X POST http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "baseline-langchain", "messages": [{"role": "user", "content": "Generate an image of a cat"}], "stream": true}'
```
