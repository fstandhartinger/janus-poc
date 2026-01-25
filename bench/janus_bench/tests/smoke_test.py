"""Quick smoke tests for Janus benchmark targets."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx


SMOKE_TEST_CASES = [
    {
        "name": "simple_qa",
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "expected_contains": ["4"],
        "max_latency_seconds": 20,
    },
    {
        "name": "web_search",
        "messages": [
            {
                "role": "user",
                "content": "What is the current weather in Tokyo?",
            }
        ],
        "expected_tool_calls": ["web_search"],
        "max_latency_seconds": 15,
    },
    {
        "name": "code_execution",
        "messages": [
            {
                "role": "user",
                "content": "Calculate the factorial of 10 using Python",
            }
        ],
        "expected_tool_calls": ["code_execution"],
        "max_latency_seconds": 20,
    },
    {
        "name": "image_generation",
        "messages": [
            {
                "role": "user",
                "content": "Generate an image of a sunset over mountains",
            }
        ],
        "expected_tool_calls": ["image_generation"],
        "max_latency_seconds": 30,
    },
    {
        "name": "streaming_quality",
        "messages": [
            {
                "role": "user",
                "content": "Write a 200-word story about a robot",
            }
        ],
        "min_chunks": 10,
        "max_ttft_seconds": 5.0,
    },
]


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current information.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "code_execution",
                "description": "Execute Python code for calculations.",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "image_generation",
                "description": "Generate an image from a prompt.",
                "parameters": {
                    "type": "object",
                    "properties": {"prompt": {"type": "string"}},
                    "required": ["prompt"],
                },
            },
        },
    ]


def _extract_tool_calls(response: dict[str, Any]) -> list[str]:
    choices = response.get("choices", [])
    if not choices:
        return []
    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls") or []
    names = []
    for call in tool_calls:
        function = call.get("function") or {}
        name = function.get("name")
        if name:
            names.append(str(name))
    return names


def _extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return str(message.get("content") or "")


async def _run_streaming_test(
    client: httpx.AsyncClient,
    target_url: str,
    test: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": test["messages"],
        "stream": True,
    }

    start_time = time.monotonic()
    first_chunk_time: float | None = None
    chunk_count = 0

    async with client.stream(
        "POST",
        f"{target_url}/v1/chat/completions",
        json=payload,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk_count += 1
            if first_chunk_time is None:
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    payload = {}
                choices = payload.get("choices", []) if isinstance(payload, dict) else []
                if choices:
                    delta = choices[0].get("delta", {})
                    if delta.get("content") or delta.get("reasoning_content"):
                        first_chunk_time = time.monotonic()

    ttft = None
    if first_chunk_time is not None:
        ttft = first_chunk_time - start_time

    passed = True
    details: dict[str, Any] = {
        "chunk_count": chunk_count,
        "ttft_seconds": ttft,
    }

    min_chunks = test.get("min_chunks")
    if min_chunks is not None and chunk_count < min_chunks:
        passed = False

    max_ttft = test.get("max_ttft_seconds")
    if max_ttft is not None and (ttft is None or ttft > max_ttft):
        passed = False

    return {
        "name": test["name"],
        "passed": passed,
        "details": details,
    }


async def run_single_smoke_test(
    client: httpx.AsyncClient,
    target_url: str,
    test: dict[str, Any],
    model: str = "janus-baseline-agent-cli",
) -> dict[str, Any]:
    """Run one smoke test and return the result."""
    if "min_chunks" in test:
        return await _run_streaming_test(client, target_url, test, model)

    payload = {
        "model": model,
        "messages": test["messages"],
        "stream": False,
    }
    expected_tool_calls = test.get("expected_tool_calls")
    if expected_tool_calls:
        payload["tools"] = _tool_definitions()
        payload["tool_choice"] = {
            "type": "function",
            "function": {"name": expected_tool_calls[0]},
        }

    start_time = time.monotonic()
    response = await client.post(
        f"{target_url}/v1/chat/completions",
        json=payload,
    )
    latency = time.monotonic() - start_time
    response.raise_for_status()
    data = response.json()

    passed = True
    details: dict[str, Any] = {
        "latency_seconds": latency,
    }

    expected_contains = test.get("expected_contains")
    if expected_contains:
        content = _extract_content(data)
        details["content_preview"] = content[:200]
        for needle in expected_contains:
            if needle not in content:
                passed = False

    if expected_tool_calls:
        tool_calls = _extract_tool_calls(data)
        details["tool_calls"] = tool_calls
        for name in expected_tool_calls:
            if name not in tool_calls:
                passed = False

    max_latency = test.get("max_latency_seconds")
    if max_latency is not None and latency > max_latency:
        passed = False

    return {
        "name": test["name"],
        "passed": passed,
        "details": details,
    }


async def run_smoke_tests(
    target_url: str,
    model: str = "janus-baseline-agent-cli",
) -> dict[str, Any]:
    """Run quick smoke tests and return aggregated results."""
    results: dict[str, Any] = {"passed": 0, "failed": 0, "tests": []}

    async with httpx.AsyncClient(timeout=60) as client:
        for test in SMOKE_TEST_CASES:
            try:
                result = await run_single_smoke_test(client, target_url, test, model)
                results["tests"].append(result)
                if result["passed"]:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
            except Exception as exc:
                results["tests"].append(
                    {
                        "name": test.get("name", "unknown"),
                        "passed": False,
                        "error": str(exc),
                    }
                )
                results["failed"] += 1

    return results
