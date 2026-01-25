# Spec 84: Baseline Smoke Tests via Gateway

## Status: NOT STARTED

## Context / Why

The baseline implementations (baseline-agent-cli and baseline-langchain) are accessed via the gateway, same as the chat UI does. Quick smoke tests are needed to:

1. Validate baselines work correctly through the gateway
2. Catch common errors (like missing model fields, connection issues)
3. Ensure the chat experience works before users hit errors
4. Run periodically to monitor service health

This spec creates a focused smoke test suite that mirrors real chat UI usage.

## Goals

- Create simple, fast smoke tests for baseline models via gateway
- Test both baseline-agent-cli and baseline-langchain
- Cover basic chat, streaming, multimodal, and error scenarios
- Make tests runnable against deployed services
- Provide clear pass/fail results

## Non-Goals

- Comprehensive unit testing (covered by spec 52)
- Full integration testing (covered by spec 69)
- Performance benchmarking
- UI testing

## Functional Requirements

### FR-1: Smoke Test Script

Create a Python script that tests baseline models through the gateway.

```python
# tests/smoke_baselines.py

"""
Smoke tests for baseline models via the gateway.

Usage:
    python tests/smoke_baselines.py [--gateway-url URL] [--baseline MODEL]

Examples:
    # Test against deployed gateway
    python tests/smoke_baselines.py

    # Test locally
    python tests/smoke_baselines.py --gateway-url http://localhost:8000

    # Test specific baseline
    python tests/smoke_baselines.py --baseline baseline-agent-cli
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Optional

import httpx

DEFAULT_GATEWAY_URL = "https://janus-gateway-bqou.onrender.com"
BASELINES = ["baseline", "baseline-cli-agent"]  # baseline-langchain if available


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: float


class SmokeTests:
    def __init__(self, gateway_url: str, baseline: Optional[str] = None):
        self.gateway_url = gateway_url.rstrip("/")
        self.baselines = [baseline] if baseline else BASELINES
        self.results: list[TestResult] = []

    async def run_all(self) -> bool:
        """Run all smoke tests and return True if all pass."""
        print(f"\n{'='*60}")
        print(f"Baseline Smoke Tests - Gateway: {self.gateway_url}")
        print(f"{'='*60}\n")

        # Test gateway health first
        await self.test_gateway_health()

        # Test each baseline
        for baseline in self.baselines:
            print(f"\n--- Testing: {baseline} ---\n")
            await self.test_simple_query(baseline)
            await self.test_streaming(baseline)
            await self.test_math_question(baseline)
            await self.test_empty_message(baseline)

        # Print summary
        self.print_summary()
        return all(r.passed for r in self.results)

    def record(self, name: str, passed: bool, message: str, duration_ms: float):
        result = TestResult(name, passed, message, duration_ms)
        self.results.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {message} ({duration_ms:.0f}ms)")

    async def test_gateway_health(self):
        """Test gateway health endpoint."""
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.gateway_url}/health")
                duration = (time.perf_counter() - start) * 1000
                if response.status_code == 200:
                    self.record("gateway_health", True, "Gateway healthy", duration)
                else:
                    self.record("gateway_health", False, f"Status {response.status_code}", duration)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self.record("gateway_health", False, str(e), duration)

    async def test_simple_query(self, baseline: str):
        """Test simple chat query."""
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": baseline,
                        "messages": [{"role": "user", "content": "What is 2+2?"}],
                        "stream": False,
                    }
                )
                duration = (time.perf_counter() - start) * 1000
                if response.status_code != 200:
                    self.record(f"{baseline}_simple", False, f"Status {response.status_code}", duration)
                    return

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if "error" in content.lower() and "sorry" in content.lower():
                    self.record(f"{baseline}_simple", False, f"Error response: {content[:100]}", duration)
                elif "4" in content:
                    self.record(f"{baseline}_simple", True, "Correct answer", duration)
                else:
                    self.record(f"{baseline}_simple", True, f"Got response: {content[:50]}...", duration)

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self.record(f"{baseline}_simple", False, str(e), duration)

    async def test_streaming(self, baseline: str):
        """Test streaming response."""
        import time
        start = time.perf_counter()
        chunks = 0
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": baseline,
                        "messages": [{"role": "user", "content": "Say hello"}],
                        "stream": True,
                    }
                ) as response:
                    if response.status_code != 200:
                        duration = (time.perf_counter() - start) * 1000
                        self.record(f"{baseline}_stream", False, f"Status {response.status_code}", duration)
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line[6:] != "[DONE]":
                            chunks += 1

                duration = (time.perf_counter() - start) * 1000
                if chunks > 0:
                    self.record(f"{baseline}_stream", True, f"{chunks} chunks received", duration)
                else:
                    self.record(f"{baseline}_stream", False, "No chunks received", duration)

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self.record(f"{baseline}_stream", False, str(e), duration)

    async def test_math_question(self, baseline: str):
        """Test a math/reasoning question."""
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": baseline,
                        "messages": [{"role": "user", "content": "If I have 3 apples and buy 2 more, how many do I have?"}],
                        "stream": False,
                    }
                )
                duration = (time.perf_counter() - start) * 1000
                if response.status_code != 200:
                    self.record(f"{baseline}_math", False, f"Status {response.status_code}", duration)
                    return

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if "5" in content:
                    self.record(f"{baseline}_math", True, "Correct answer (5)", duration)
                elif "error" in content.lower():
                    self.record(f"{baseline}_math", False, "Error in response", duration)
                else:
                    self.record(f"{baseline}_math", True, f"Response received", duration)

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self.record(f"{baseline}_math", False, str(e), duration)

    async def test_empty_message(self, baseline: str):
        """Test handling of edge cases."""
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": baseline,
                        "messages": [{"role": "user", "content": ""}],
                        "stream": False,
                    }
                )
                duration = (time.perf_counter() - start) * 1000
                # Should handle gracefully (200 or 400, not 500)
                if response.status_code in [200, 400]:
                    self.record(f"{baseline}_edge", True, f"Handled gracefully (status {response.status_code})", duration)
                else:
                    self.record(f"{baseline}_edge", False, f"Unexpected status {response.status_code}", duration)

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self.record(f"{baseline}_edge", False, str(e), duration)

    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"Passed: {passed}/{total}")
        print(f"Failed: {failed}/{total}")

        if failed > 0:
            print("\nFailed tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")

        print(f"\n{'='*60}\n")


async def main():
    parser = argparse.ArgumentParser(description="Baseline smoke tests via gateway")
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL, help="Gateway URL")
    parser.add_argument("--baseline", help="Specific baseline to test")
    args = parser.parse_args()

    tests = SmokeTests(args.gateway_url, args.baseline)
    success = await tests.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
```

### FR-2: Quick Run Command

Add npm script and pytest marker for quick smoke testing.

```python
# tests/conftest.py - add marker
def pytest_configure(config):
    config.addinivalue_line("markers", "smoke_baseline: baseline smoke tests")
```

```bash
# scripts/smoke-baselines.sh
#!/bin/bash

# Quick baseline smoke test
python tests/smoke_baselines.py "$@"
```

### FR-3: Integration with Test Suite

```python
# tests/smoke/test_baseline_gateway.py

import pytest
import httpx

GATEWAY_URL = "https://janus-gateway-bqou.onrender.com"
BASELINES = ["baseline", "baseline-cli-agent"]


class TestBaselineSmokeGateway:
    """Smoke tests for baselines via gateway."""

    @pytest.mark.smoke_baseline
    @pytest.mark.parametrize("baseline", BASELINES)
    @pytest.mark.asyncio
    async def test_simple_query(self, baseline):
        """Simple query returns a response."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": baseline,
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            assert "error" not in content.lower() or "sorry" not in content.lower()

    @pytest.mark.smoke_baseline
    @pytest.mark.parametrize("baseline", BASELINES)
    @pytest.mark.asyncio
    async def test_streaming_works(self, baseline):
        """Streaming returns chunks."""
        chunks = []
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": baseline,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                }
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and "[DONE]" not in line:
                        chunks.append(line)

        assert len(chunks) > 0, "No streaming chunks received"
```

## Acceptance Criteria

- [ ] Smoke test script runs against deployed gateway
- [ ] Tests both baseline-cli-agent and baseline-langchain (if available)
- [ ] Simple query test passes
- [ ] Streaming test passes
- [ ] Math/reasoning test passes
- [ ] Edge case handling test passes
- [ ] Clear output showing pass/fail for each test
- [ ] Exit code reflects test success/failure

## Files to Create

```
tests/
├── smoke_baselines.py           # Main smoke test script
└── smoke/
    └── test_baseline_gateway.py # Pytest-based smoke tests

scripts/
└── smoke-baselines.sh          # Quick run script
```

## Usage

```bash
# Run smoke tests against deployed gateway
python tests/smoke_baselines.py

# Run against local gateway
python tests/smoke_baselines.py --gateway-url http://localhost:8000

# Run via pytest
pytest tests/smoke/test_baseline_gateway.py -v

# Run just baseline-cli-agent
python tests/smoke_baselines.py --baseline baseline-cli-agent
```

## Related Specs

- `specs/52_comprehensive_baseline_testing.md` - Full baseline testing
- `specs/69_comprehensive_testing_suite.md` - Complete test suite
- `specs/21_enhanced_baseline.md` - Baseline implementation

NR_OF_TRIES: 0
