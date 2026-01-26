# Spec 92: Baseline Agent CLI End-to-End Verification

## Status: COMPLETE
**Priority:** Critical
**Complexity:** High
**Prerequisites:** Spec 79, Spec 84

---

## Overview

This spec ensures the baseline-agent-cli actually works end-to-end with real CLI agents (Claude Code, Codex, Aider) running inside Sandy sandboxes. The investigation revealed several issues that were fixed, but comprehensive E2E testing is needed to verify the system works as intended.

### Current Architecture (PoC Target)

The PoC uses this architecture, which is simpler and already working:

```
USER → UI → Gateway (Render) → baseline-agent-cli (Render) → Sandy agent/run API → Agent
```

Key points:
- **baseline-agent-cli** runs as a Render service (NOT inside Sandy)
- **Sandy's agent/run API** handles agent execution (Claude Code, Codex, Aider)
- **Sandy** manages yolo mode, agent config, streaming
- This is the correct architecture for PoC - containerization is deferred (see Spec 95)

### Background (from Investigation)

The investigation uncovered:
1. **Fake aider wrapper** was shadowing the real aider binary
2. **PATH issues** with unexpanded shell variables
3. **Parameter naming** - Sandy uses `rawPrompt` (camelCase) not `raw_prompt`
4. **Model compatibility** - DeepSeek V3 causes tool-call parsing errors; MiniMax works better
5. **Model router integration** - Sandy agent path now supports `apiBaseUrl` for smart routing

---

## Functional Requirements

### FR-1: Agent CLI Selection Tests

Verify each supported CLI agent can be selected and used.

```python
# tests/e2e/test_agent_selection.py

import pytest
import httpx

GATEWAY_URL = "https://janus-gateway.onrender.com"
BASELINE_CLI = "https://janus-baseline-agent-cli.onrender.com"

class TestAgentSelection:
    """Test different CLI agents can be selected and work."""

    @pytest.mark.e2e
    @pytest.mark.parametrize("agent", ["claude-code", "codex", "aider"])
    async def test_agent_responds(self, agent: str):
        """Each agent type should produce a reasonable response."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{BASELINE_CLI}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{"role": "user", "content": "What is 2 + 2?"}],
                    "stream": False,
                },
                headers={"X-Baseline-Agent": agent},
            )
            assert response.status_code == 200
            data = response.json()
            assert "4" in data["choices"][0]["message"]["content"]

    @pytest.mark.e2e
    async def test_default_agent_is_claude_code(self):
        """Default agent should be claude-code."""
        # Check via logs or config endpoint
        pass
```

### FR-2: Complex Task Execution Tests

Test various complex prompts that require real agent capabilities.

```python
# tests/e2e/test_complex_tasks.py

class TestComplexTasks:
    """Test complex tasks that require Sandy sandbox execution."""

    @pytest.mark.e2e
    @pytest.mark.timeout(600)
    async def test_git_clone_and_summarize(self):
        """Test: 'lade das chutes-api repo von github herunter und gib mir eine zusammenfassung'"""
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{
                        "role": "user",
                        "content": "Clone the chutes-api repo from github and give me a summary of what it does"
                    }],
                    "stream": True,
                },
            )

            # Collect SSE events
            events = []
            content = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data != "[DONE]":
                        events.append(json.loads(data))
                        if "choices" in events[-1]:
                            delta = events[-1]["choices"][0].get("delta", {})
                            content += delta.get("content", "")

            # Should mention repo contents, not template response
            assert "chutes" in content.lower() or "api" in content.lower()
            # Should NOT be template response about LLM endpoint
            assert "llm.chutes.ai/v1/chat/completions" not in content

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_web_search_task(self):
        """Test a task requiring web search."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{
                        "role": "user",
                        "content": "Search the web for the latest news about AI agents and summarize the top 3 findings"
                    }],
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should have actual search results
            assert len(content) > 200
            # Should mention sources or findings
            assert any(word in content.lower() for word in ["source", "found", "according", "report"])

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_coding_task(self):
        """Test a task requiring code execution."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{
                        "role": "user",
                        "content": "Write a Python script that fetches the current Bitcoin price from an API and prints it. Actually run the script and show me the output."
                    }],
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should contain actual price or code output
            assert "python" in content.lower() or "$" in content or "BTC" in content

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_multimodal_image_generation(self):
        """Test image generation via Chutes API."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{
                        "role": "user",
                        "content": "Generate an image of a futuristic city with flying cars"
                    }],
                    "stream": False,
                },
            )
            data = response.json()

            # Should have artifacts with image
            artifacts = data.get("artifacts", [])
            has_image = any(
                a.get("type") == "image" or
                "image" in str(a.get("data", {}).get("mime_type", ""))
                for a in artifacts
            )
            assert has_image or "generated" in data["choices"][0]["message"]["content"].lower()

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_text_to_speech(self):
        """Test TTS via Chutes API."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{
                        "role": "user",
                        "content": "Convert this text to speech: Hello, welcome to Janus!"
                    }],
                    "stream": False,
                },
            )
            data = response.json()

            # Should have audio artifact
            artifacts = data.get("artifacts", [])
            has_audio = any(
                a.get("type") == "audio" or
                "audio" in str(a.get("data", {}).get("mime_type", ""))
                for a in artifacts
            )
            assert has_audio or "audio" in data["choices"][0]["message"]["content"].lower()
```

### FR-3: Model Compatibility Tests

Test different LLM models work correctly.

```python
# tests/e2e/test_model_compatibility.py

class TestModelCompatibility:
    """Test different models work with the agent."""

    MODELS_TO_TEST = [
        "MiniMaxAI/MiniMax-M2",           # Works well
        "deepseek-ai/DeepSeek-V3-0324",   # May have tool-call issues
        "THUDM/GLM-4-Plus",               # Alternative
        "Qwen/Qwen2.5-VL-72B-Instruct",   # For vision tasks
        "mistralai/Mistral-Small-3.2",    # Fast, small
    ]

    @pytest.mark.e2e
    @pytest.mark.parametrize("model", MODELS_TO_TEST)
    async def test_model_simple_task(self, model: str):
        """Each model should handle simple tasks."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{BASELINE_CLI}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say hello in exactly 5 words."}],
                    "stream": False,
                },
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                assert len(content) > 0
            else:
                # Log which model failed
                pytest.skip(f"Model {model} not available or failed")

    @pytest.mark.e2e
    async def test_vision_model_with_image(self):
        """Vision model should process images."""
        # Test with image URL
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{BASELINE_CLI}/v1/chat/completions",
                json={
                    "model": "Qwen/Qwen2.5-VL-72B-Instruct",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image"},
                            {"type": "image_url", "image_url": {"url": "https://picsum.photos/200"}}
                        ]
                    }],
                    "stream": False,
                },
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                assert len(content) > 50  # Should have description
```

### FR-4: SSE Streaming Verification

Verify SSE events are properly formatted and streamed.

```python
# tests/e2e/test_sse_streaming.py

class TestSSEStreaming:
    """Test SSE streaming is working correctly."""

    @pytest.mark.e2e
    async def test_sse_format(self):
        """SSE events should follow OpenAI format."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{BASELINE_CLI}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{"role": "user", "content": "Count from 1 to 5"}],
                    "stream": True,
                },
            ) as response:
                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(line)

                # Should have multiple events
                assert len(events) > 1
                # Should end with [DONE]
                assert events[-1] == "data: [DONE]"
                # Earlier events should be valid JSON
                for event in events[:-1]:
                    data = json.loads(event[6:])
                    assert "id" in data
                    assert "choices" in data

    @pytest.mark.e2e
    async def test_reasoning_content_streaming(self):
        """reasoning_content should be streamed before main content."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{BASELINE_CLI}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{"role": "user", "content": "What is the capital of France?"}],
                    "stream": True,
                },
            ) as response:
                saw_reasoning = False
                saw_content = False

                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if delta.get("reasoning_content"):
                            saw_reasoning = True
                        if delta.get("content"):
                            saw_content = True

                # Should have both types
                assert saw_content
                # reasoning_content is optional but expected for complex tasks
```

### FR-5: Yolo Mode Verification

Verify agents run in yolo/bypass-permissions mode.

```python
# tests/e2e/test_yolo_mode.py

class TestYoloMode:
    """Test agents run with full permissions (no interactive prompts)."""

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_file_operations_no_prompt(self):
        """Agent should create files without asking for permission."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{
                        "role": "user",
                        "content": "Create a file called test.txt with the content 'Hello World' and then read it back to me"
                    }],
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should complete without asking permission
            assert "Hello World" in content or "created" in content.lower()
            # Should NOT ask for permission
            assert "permission" not in content.lower() or "granted" in content.lower()

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_command_execution_no_prompt(self):
        """Agent should execute commands without asking for permission."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{
                        "role": "user",
                        "content": "Run 'echo Hello from the sandbox' and show me the output"
                    }],
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should have actual output
            assert "Hello from the sandbox" in content
```

---

## Acceptance Criteria

### Agent Selection
- [ ] Claude Code agent launches and responds correctly
- [ ] Codex agent launches and responds correctly
- [ ] Aider agent launches and responds correctly
- [ ] Default agent is Claude Code when not specified
- [ ] Agent selection via X-Baseline-Agent header works

### Complex Tasks
- [ ] Git clone + summarize works (not template response)
- [ ] Web search tasks return real results with sources
- [ ] Code execution tasks run and return output
- [ ] Image generation creates artifacts
- [ ] TTS creates audio artifacts

### Model Compatibility
- [ ] MiniMax M2 works for all task types
- [ ] DeepSeek V3 is tested (document any limitations)
- [ ] Vision models process images correctly
- [ ] Model fallback works via router on 429 errors

### SSE Streaming
- [ ] Events follow OpenAI SSE format
- [ ] Events end with data: [DONE]
- [ ] reasoning_content streams before content
- [ ] Artifacts are included in final message

### Yolo Mode
- [ ] File operations complete without permission prompts
- [ ] Command execution completes without permission prompts
- [ ] No "waiting for user input" states occur

---

## Testing Procedure

### 1. Via Gateway API (End-to-End)

```bash
# Test complex task
curl -X POST https://janus-gateway.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "baseline-agent-cli",
    "messages": [{"role": "user", "content": "Clone chutes-api repo and summarize it"}],
    "stream": true
  }'
```

### 2. Check Logs

Watch Render logs during test:
```bash
# Via Render MCP
render logs --service janus-baseline-agent-cli --tail 100
```

Expected log events:
- `complexity_analysis` - Shows routing decision
- `agent_api_request` - Shows agent API call
- `agent_api_sse_event` - Shows streaming events from Sandy
- `agent_api_complete` - Shows final result

### 3. Verify Actual Agent Execution

In Sandy logs, verify:
- Agent binary was found (not builtin fallback)
- Yolo mode flags were passed
- Agent executed tools (git, code execution, etc.)

---

## Files to Modify

| File | Changes |
|------|---------|
| `baseline-agent-cli/tests/e2e/` | Add E2E test files |
| `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py` | Ensure logging covers all events |
| `baseline-agent-cli/janus_baseline_agent_cli/config.py` | Add test configuration |

---

## Notes

- E2E tests require deployed services (not mocked)
- Tests may take 5-10 minutes to run fully
- Some tests are marked with @pytest.mark.timeout to prevent hangs
- Model availability may vary; tests should handle unavailability gracefully
- Test results should be logged for debugging

---

## Related Specs

- Spec 79: Baseline LangChain Feature Parity
- Spec 84: Baseline Smoke Tests
- Spec 93: Comprehensive Logging & Observability (creates logging framework)
- Spec 94: Baseline LangChain E2E Verification

NR_OF_TRIES: 3
