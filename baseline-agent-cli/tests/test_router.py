"""Tests for the composite model router."""

import httpx
import pytest
from fastapi import Response

from janus_baseline_agent_cli.router.metrics import RoutingMetrics
from janus_baseline_agent_cli.router.models import ModelConfig, get_fallback_models, get_model_for_decision
from janus_baseline_agent_cli.router import server as router_server
from janus_baseline_agent_cli.routing import RoutingDecision


class DummyClassifier:
    async def classify(
        self, messages: list[dict], has_images: bool = False
    ) -> tuple[RoutingDecision, float]:
        return RoutingDecision.FAST_NEMOTRON, 0.9

    async def close(self) -> None:
        return None


def test_model_registry_primary_and_fallbacks() -> None:
    assert get_model_for_decision(RoutingDecision.FAST_QWEN).model_id == "Qwen/Qwen3-30B-A3B-Instruct-2507"
    vision_model = get_model_for_decision(RoutingDecision.FAST_KIMI)
    assert vision_model.supports_vision is True
    fallbacks = get_fallback_models(vision_model.model_id)
    assert fallbacks
    assert any(model.model_id == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16" for model in fallbacks)


@pytest.mark.asyncio
async def test_router_fallback_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    router_server.classifier = DummyClassifier()
    router_server.api_key = "test"
    router_server.api_base = "http://example.com"
    router_server.metrics = RoutingMetrics()

    primary = ModelConfig(
        model_id="primary",
        display_name="Primary",
        priority=1,
    )
    fallback = ModelConfig(
        model_id="fallback",
        display_name="Fallback",
        priority=2,
    )

    monkeypatch.setattr(router_server, "get_model_for_decision", lambda decision: primary)
    monkeypatch.setattr(router_server, "get_fallback_models", lambda model_id: [fallback])

    calls: list[str] = []

    async def fake_non_stream(request, model_config, decision):
        calls.append(model_config.model_id)
        if model_config.model_id == "primary":
            request_obj = httpx.Request("POST", "http://example.com")
            response = httpx.Response(429, request=request_obj)
            raise httpx.HTTPStatusError("rate limited", request=request_obj, response=response)
        return {"id": "resp", "model": "janus-router", "choices": []}

    monkeypatch.setattr(router_server, "_non_stream_response", fake_non_stream)

    request = router_server.ChatCompletionRequest(
        model="janus-router",
        messages=[{"role": "user", "content": "hello"}],
        stream=False,
    )

    response = await router_server.chat_completions(
        request, raw_request=None, http_response=Response()
    )
    assert response["model"] == "janus-router"
    assert calls == ["primary", "fallback"]
    assert router_server.metrics.fallback_count == 1


@pytest.mark.asyncio
async def test_streaming_rewrites_model(monkeypatch: pytest.MonkeyPatch) -> None:
    router_server.api_key = "test"
    router_server.api_base = "http://example.com"

    class DummyStream:
        def __init__(self, lines: list[str]):
            self._lines = lines

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self) -> None:
            return None

        async def aiter_lines(self):
            for line in self._lines:
                yield line

    class DummyClient:
        def __init__(self, *args, **kwargs):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return DummyStream(
                [
                    'data: {"id": "1", "model": "orig", "choices": []}',
                    "data: [DONE]",
                ]
            )

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)

    request = router_server.ChatCompletionRequest(
        model="janus-router",
        messages=[{"role": "user", "content": "hello"}],
        stream=True,
    )
    model_config = ModelConfig(
        model_id="primary",
        display_name="Primary",
        priority=1,
    )

    response = await router_server._stream_response(
        request, model_config, RoutingDecision.FAST_NEMOTRON
    )
    chunks = [chunk async for chunk in response.body_iterator]
    combined = "".join(chunks)
    assert "janus-router" in combined
    assert "data: [DONE]" in combined


def test_openai_tool_calls_convert_to_anthropic_tool_use() -> None:
    openai_response = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "Bash", "arguments": "{\"command\": \"ls\"}"},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }
    anthropic = router_server._openai_to_anthropic_response(openai_response, "janus-router")
    content_blocks = anthropic.get("content", [])
    assert any(block.get("type") == "tool_use" for block in content_blocks)
    tool_block = next(block for block in content_blocks if block.get("type") == "tool_use")
    assert tool_block["name"] == "Bash"
    assert tool_block["input"]["command"] == "ls"
