# Spec 27: Baseline-LangChain Alternative Implementation

## Status: COMPLETE

## Context / Why

The current baseline implementation (`baseline-agent-cli`) uses Claude Code CLI running in a Sandy sandbox. While powerful, this approach:
- Requires Sandy infrastructure and sandbox provisioning
- Has higher latency due to sandbox spin-up time
- Uses a proprietary tool (Claude Code)

A LangChain-based baseline would:
- Run entirely in-process (no sandbox needed)
- Use open-source tooling
- Provide a simpler architecture for developers to understand and extend
- Serve as an alternative competition entry for benchmarking

## Goals

- Create a new baseline implementation using LangChain
- Support the same multimodal capabilities (image gen, TTS, web search)
- Provide equivalent or better latency for simple tasks
- Pass all baseline acceptance tests
- Document architecture for miners to learn from

## Non-Goals

- Replacing the CLI agent baseline (both will coexist)
- Implementing proprietary tools or agents
- Perfect feature parity (LangChain has different tool ecosystem)

## Functional Requirements

### FR-1: Project Structure

```
baseline-langchain/
├── janus_baseline_langchain/
│   ├── __init__.py
│   ├── config.py              # Settings (env vars)
│   ├── main.py                # FastAPI app
│   ├── agent.py               # LangChain agent setup
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── image_gen.py       # Chutes image generation
│   │   ├── tts.py             # Chutes Kokoro TTS
│   │   ├── web_search.py      # Web search (Tavily/SerpAPI)
│   │   └── code_exec.py       # Safe code execution
│   └── models/
│       └── openai.py          # Request/response models
├── tests/
│   ├── test_agent.py
│   ├── test_tools.py
│   └── conftest.py
├── pyproject.toml
└── README.md
```

### FR-2: LangChain Agent Configuration

```python
# agent.py
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from janus_baseline_langchain.tools import (
    image_generation_tool,
    tts_tool,
    web_search_tool,
    code_execution_tool,
)

SYSTEM_PROMPT = """You are Janus, an intelligent assistant competing in The Rodeo.

You have access to these tools:
- image_generation: Generate images using AI (Chutes API)
- text_to_speech: Convert text to audio (Kokoro TTS)
- web_search: Search the web for current information
- code_execution: Execute Python code safely

Always use the appropriate tool for the task. For image requests, use image_generation.
For audio/speech requests, use text_to_speech.
For questions about current events or real-time data, use web_search.
For calculations or data processing, use code_execution."""


def create_agent(settings: Settings) -> AgentExecutor:
    llm = ChatOpenAI(
        model=settings.model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=settings.temperature,
        streaming=True,
    )

    tools = [
        image_generation_tool,
        tts_tool,
        web_search_tool,
        code_execution_tool,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=settings.debug,
        max_iterations=10,
        return_intermediate_steps=True,
    )
```

### FR-3: Tool Implementations

#### Image Generation Tool
```python
# tools/image_gen.py
from langchain_core.tools import tool
import httpx

@tool
def image_generation(prompt: str) -> str:
    """Generate an image from a text description.

    Args:
        prompt: Description of the image to generate

    Returns:
        URL or base64 data of the generated image
    """
    response = httpx.post(
        "https://llm.chutes.ai/v1/images/generations",
        headers={"Authorization": f"Bearer {settings.chutes_api_key}"},
        json={
            "model": "Qwen/Qwen2.5-VL-72B-Instruct",  # or HunYuan
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        },
    )
    data = response.json()
    return data["data"][0]["url"]
```

#### TTS Tool
```python
# tools/tts.py
from langchain_core.tools import tool
import httpx
import base64

@tool
def text_to_speech(text: str, voice: str = "am_michael") -> str:
    """Convert text to speech audio.

    Args:
        text: Text to convert to speech
        voice: Voice to use (am_michael, af_sky, etc.)

    Returns:
        Base64 encoded audio data
    """
    response = httpx.post(
        "https://chutes-kokoro.chutes.ai/speak",
        headers={
            "Authorization": f"Bearer {settings.chutes_api_key}",
            "Content-Type": "application/json",
        },
        json={"text": text, "voice": voice, "speed": 1.0},
    )
    audio_data = base64.b64encode(response.content).decode()
    return f"data:audio/wav;base64,{audio_data}"
```

#### Web Search Tool
```python
# tools/web_search.py
from langchain_community.tools.tavily_search import TavilySearchResults

web_search_tool = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
)
```

#### Code Execution Tool
```python
# tools/code_exec.py
from langchain_experimental.tools import PythonREPLTool

code_execution_tool = PythonREPLTool(
    name="code_execution",
    description="Execute Python code for calculations, data processing, etc.",
)
```

### FR-4: FastAPI Endpoint

```python
# main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI(title="Janus Baseline LangChain")

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    agent = create_agent(settings)

    # Convert messages to LangChain format
    chat_history = []
    for msg in request.messages[:-1]:
        if msg.role == "user":
            chat_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            chat_history.append(AIMessage(content=msg.content))

    user_input = request.messages[-1].content

    if request.stream:
        return StreamingResponse(
            stream_agent_response(agent, user_input, chat_history),
            media_type="text/event-stream",
        )
    else:
        result = await agent.ainvoke({
            "input": user_input,
            "chat_history": chat_history,
        })
        return format_response(result)


async def stream_agent_response(agent, input: str, history: list):
    """Stream agent response as SSE events."""
    async for event in agent.astream_events(
        {"input": input, "chat_history": history},
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                yield f"data: {format_chunk(chunk)}\n\n"
    yield "data: [DONE]\n\n"
```

### FR-5: Configuration

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BASELINE_LANGCHAIN_",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8002
    debug: bool = False

    # LLM
    model: str = "gpt-4o-mini"
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.7

    # Chutes (for image/TTS)
    chutes_api_key: str

    # Web Search
    tavily_api_key: str = None
```

### FR-6: Render Deployment

Add to `render.yaml`:

```yaml
services:
  - type: web
    name: janus-baseline-langchain
    runtime: python
    rootDir: baseline-langchain
    buildCommand: pip install -e .
    startCommand: uvicorn janus_baseline_langchain.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: BASELINE_LANGCHAIN_OPENAI_API_KEY
        sync: false
      - key: BASELINE_LANGCHAIN_CHUTES_API_KEY
        sync: false
      - key: BASELINE_LANGCHAIN_TAVILY_API_KEY
        sync: false
```

## Non-Functional Requirements

### NFR-1: Performance

- Cold start: <5s (no sandbox provisioning)
- Simple chat: <500ms time to first token
- Tool-using request: <10s total (depends on external APIs)

### NFR-2: Reliability

- Graceful degradation if tools fail
- Retry logic for external API calls
- Proper error messages in responses

### NFR-3: Security

- No arbitrary code execution outside sandboxed REPL
- API keys never exposed in responses
- Input validation on all endpoints

## Acceptance Criteria

- [ ] `POST /v1/chat/completions` returns valid OpenAI-compatible responses
- [ ] Streaming responses work correctly
- [ ] "Generate an image of a cat" produces an image URL
- [ ] "Convert this to speech: Hello world" produces audio data
- [ ] "What's the latest news about AI?" returns search results
- [ ] "Calculate 2+2" executes code and returns 4
- [ ] All tests pass: `pytest baseline-langchain/tests/`
- [ ] Deploys successfully to Render
- [ ] Gateway can route requests to this baseline

## Test Plan

### Unit Tests

```python
# tests/test_tools.py
@pytest.mark.asyncio
async def test_image_generation_tool():
    result = await image_generation.ainvoke("a sunset over mountains")
    assert result.startswith("http") or result.startswith("data:")

@pytest.mark.asyncio
async def test_tts_tool():
    result = await text_to_speech.ainvoke({"text": "Hello", "voice": "am_michael"})
    assert "data:audio" in result

@pytest.mark.asyncio
async def test_code_execution_tool():
    result = await code_execution_tool.ainvoke("print(2 + 2)")
    assert "4" in result
```

### Integration Tests

```python
# tests/test_agent.py
@pytest.mark.asyncio
async def test_agent_handles_image_request():
    agent = create_agent(settings)
    result = await agent.ainvoke({"input": "Generate an image of a cat"})
    assert "image" in result["output"].lower() or "http" in result["output"]

@pytest.mark.asyncio
async def test_agent_handles_simple_chat():
    agent = create_agent(settings)
    result = await agent.ainvoke({"input": "Hello, how are you?"})
    assert len(result["output"]) > 0
```

## Dependencies

```toml
[project]
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "langchain>=0.1.0",
    "langchain-openai>=0.0.5",
    "langchain-community>=0.0.20",
    "langchain-experimental>=0.0.50",
    "httpx>=0.26.0",
    "pydantic-settings>=2.0.0",
    "tavily-python>=0.3.0",
]
```

## Open Questions

1. Should we use LangGraph instead of basic AgentExecutor for more complex workflows?
2. Which web search provider is best (Tavily, SerpAPI, DuckDuckGo)?
3. Should code execution be sandboxed more strictly (e.g., Docker container)?

## Related Specs

- Spec 26: Baseline Rename (naming convention)
- Spec 21: Enhanced Baseline Implementation (CLI agent approach)
- Spec 09: Reference Implementation CLI Agent
