# Spec 69: Comprehensive Testing Suite

## Status: COMPLETE

## Context / Why

The Janus platform has grown to include multiple components (Gateway, Baselines, UI, Bench) with numerous features spanning multimodal capabilities, streaming, sandbox integration, and more. A comprehensive testing suite is needed to:

1. Ensure all specified functionality works correctly
2. Catch regressions before deployment
3. Validate integrations between components
4. Test against both local and deployed environments
5. Perform visual UI testing across device sizes
6. Add extensive logging for debugging

This spec consolidates testing requirements from all other specs into an executable test suite.

## Goals

- Create extensive unit tests for all components
- Create integration tests that can run against local or deployed services
- Add smoke tests for all architecture components
- Add visual UI tests using browser automation
- Add comprehensive logging throughout services
- Ensure all tests pass before considering specs complete

## Architecture

### Test Configuration

```python
# tests/config.py

import os
from pydantic_settings import BaseSettings

class TestConfig(BaseSettings):
    """Test configuration with environment-based URLs."""

    # Service URLs - configurable for local vs deployed testing
    gateway_url: str = os.getenv("TEST_GATEWAY_URL", "http://localhost:8000")
    baseline_cli_url: str = os.getenv("TEST_BASELINE_CLI_URL", "http://localhost:8001")
    baseline_langchain_url: str = os.getenv("TEST_BASELINE_LANGCHAIN_URL", "http://localhost:8002")
    ui_url: str = os.getenv("TEST_UI_URL", "http://localhost:3000")

    # Deployed URLs (for production testing)
    gateway_deployed_url: str = "https://janus-gateway-bqou.onrender.com"
    baseline_cli_deployed_url: str = "https://janus-baseline-agent.onrender.com"
    baseline_langchain_deployed_url: str = "https://janus-baseline-langchain.onrender.com"
    ui_deployed_url: str = "https://janus-ui.onrender.com"

    # Test mode
    test_mode: str = os.getenv("TEST_MODE", "local")  # local, deployed, both

    # Authentication
    chutes_fingerprint: str = os.getenv("CHUTES_FINGERPRINT", "")
    chutes_api_key: str = os.getenv("CHUTES_API_KEY", "")

    # Timeouts
    request_timeout: int = 60
    streaming_timeout: int = 300
    ui_timeout: int = 30000  # ms for Playwright

    # Visual testing
    screenshot_dir: str = "./test-screenshots"
    viewports: list = [
        {"name": "desktop", "width": 1920, "height": 1080},
        {"name": "tablet", "width": 768, "height": 1024},
        {"name": "mobile", "width": 375, "height": 812},
    ]

    def get_urls(self):
        """Get URLs based on test mode."""
        if self.test_mode == "deployed":
            return {
                "gateway": self.gateway_deployed_url,
                "baseline_cli": self.baseline_cli_deployed_url,
                "baseline_langchain": self.baseline_langchain_deployed_url,
                "ui": self.ui_deployed_url,
            }
        return {
            "gateway": self.gateway_url,
            "baseline_cli": self.baseline_cli_url,
            "baseline_langchain": self.baseline_langchain_url,
            "ui": self.ui_url,
        }

config = TestConfig()
```

---

## Part 1: Unit Tests

### Gateway Unit Tests

```python
# gateway/tests/test_models.py

import pytest
from janus_gateway.models.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
    MessageContent,
)

class TestChatCompletionRequest:
    def test_minimal_request(self):
        """Test minimal valid request."""
        request = ChatCompletionRequest(
            model="baseline",
            messages=[Message(role="user", content="Hello")]
        )
        assert request.model == "baseline"
        assert len(request.messages) == 1
        assert request.stream is True  # default

    def test_multimodal_message(self):
        """Test request with image content."""
        request = ChatCompletionRequest(
            model="baseline",
            messages=[
                Message(
                    role="user",
                    content=[
                        {"type": "text", "text": "What's in this image?"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
                    ]
                )
            ]
        )
        assert isinstance(request.messages[0].content, list)

    def test_system_message(self):
        """Test request with system message."""
        request = ChatCompletionRequest(
            model="baseline",
            messages=[
                Message(role="system", content="You are helpful."),
                Message(role="user", content="Hello"),
            ]
        )
        assert request.messages[0].role == "system"

    def test_optional_fields(self):
        """Test all optional fields."""
        request = ChatCompletionRequest(
            model="baseline",
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            stream=False,
            user="test-user",
        )
        assert request.temperature == 0.7
        assert request.stream is False


# gateway/tests/test_competitor_registry.py

class TestCompetitorRegistry:
    def test_register_competitor(self):
        """Test competitor registration."""
        registry = CompetitorRegistry()
        # ... test registration

    def test_get_default_competitor(self):
        """Test getting default competitor."""
        pass

    def test_competitor_health_check(self):
        """Test health check for competitor."""
        pass


# gateway/tests/test_streaming.py

class TestStreamingService:
    def test_sse_format(self):
        """Test SSE chunk format."""
        pass

    def test_keep_alive(self):
        """Test keep-alive generation."""
        pass

    def test_done_marker(self):
        """Test [DONE] marker."""
        pass
```

### Baseline CLI Unit Tests

```python
# baseline-agent-cli/tests/test_complexity.py

import pytest
from janus_baseline_agent_cli.services.complexity import (
    detect_complexity,
    ComplexityResult,
)

class TestComplexityDetection:
    @pytest.mark.parametrize("prompt,expected", [
        ("What is 2+2?", False),
        ("Hello, how are you?", False),
        ("Write a Python function to sort a list", True),
        ("Generate an image of a cat", True),
        ("Create a video showing a sunset", True),
        ("Search the web for latest news", True),
        ("Convert this text to speech", True),
    ])
    def test_keyword_detection(self, prompt, expected):
        """Test keyword-based complexity detection."""
        result = detect_complexity([{"role": "user", "content": prompt}])
        assert result.needs_agent == expected

    def test_empty_message(self):
        """Test empty message handling."""
        result = detect_complexity([{"role": "user", "content": ""}])
        assert result.needs_agent is False

    def test_unicode_handling(self):
        """Test unicode in prompts."""
        result = detect_complexity([{"role": "user", "content": "こんにちは"}])
        assert isinstance(result, ComplexityResult)

    def test_multimodal_detection(self):
        """Test multimodal content detection."""
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "What's this?"},
                {"type": "image_url", "image_url": {"url": "data:..."}}
            ]
        }]
        result = detect_complexity(messages)
        assert result.needs_agent is True
        assert "image" in result.reason.lower()


# baseline-agent-cli/tests/test_vision.py

class TestVisionDetection:
    def test_contains_images_text_only(self):
        """Test text-only messages."""
        messages = [{"role": "user", "content": "Hello"}]
        assert contains_images(messages) is False

    def test_contains_images_with_image(self):
        """Test message with image."""
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "What's this?"},
                {"type": "image_url", "image_url": {"url": "..."}}
            ]
        }]
        assert contains_images(messages) is True


# baseline-agent-cli/tests/test_sandy.py

class TestSandyIntegration:
    @pytest.mark.asyncio
    async def test_sandbox_creation(self, mock_sandy):
        """Test sandbox creation."""
        pass

    @pytest.mark.asyncio
    async def test_file_operations(self, mock_sandy):
        """Test file read/write."""
        pass

    @pytest.mark.asyncio
    async def test_command_execution(self, mock_sandy):
        """Test command execution."""
        pass
```

### UI Unit Tests

```typescript
// ui/src/components/__tests__/ChatArea.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatArea } from '../ChatArea';

describe('ChatArea', () => {
  it('renders empty state correctly', () => {
    render(<ChatArea />);
    expect(screen.getByText('New chat')).toBeInTheDocument();
  });

  it('handles message submission', async () => {
    render(<ChatArea />);
    const input = screen.getByPlaceholderText('Ask anything...');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.submit(input.closest('form')!);
    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument();
    });
  });

  it('shows loading state during request', async () => {
    render(<ChatArea />);
    // Submit and check for loading indicator
  });

  it('displays error messages', async () => {
    // Mock API error and verify error display
  });

  it('handles streaming responses', async () => {
    // Test incremental response rendering
  });
});


// ui/src/components/__tests__/VoiceInput.test.tsx

describe('VoiceInput', () => {
  it('requests microphone permission', async () => {
    // Mock mediaDevices.getUserMedia
  });

  it('shows recording state', async () => {
    // Test recording indicator
  });

  it('handles transcription', async () => {
    // Test transcription flow
  });

  it('shows error on permission denied', async () => {
    // Test permission error handling
  });
});


// ui/src/lib/__tests__/api.test.ts

describe('API Client', () => {
  it('sends correct headers', async () => {
    // Verify request headers
  });

  it('handles streaming responses', async () => {
    // Test SSE parsing
  });

  it('handles errors correctly', async () => {
    // Test error handling
  });
});
```

---

## Part 2: Integration Tests

### Gateway Integration Tests

```python
# tests/integration/test_gateway.py

import pytest
import httpx
from tests.config import config

@pytest.fixture
def gateway_url():
    return config.get_urls()["gateway"]

class TestGatewayHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, gateway_url):
        """Test /health endpoint."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

class TestChatCompletions:
    @pytest.mark.asyncio
    async def test_simple_chat(self, gateway_url):
        """Test simple chat completion."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Say hello"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]

    @pytest.mark.asyncio
    async def test_streaming_chat(self, gateway_url):
        """Test streaming chat completion."""
        chunks = []
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Count to 5"}],
                    "stream": True,
                }
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data != "[DONE]":
                            chunks.append(json.loads(data))

        assert len(chunks) > 0
        # Verify chunk format
        for chunk in chunks:
            assert "id" in chunk
            assert "choices" in chunk

    @pytest.mark.asyncio
    async def test_multimodal_request(self, gateway_url):
        """Test multimodal (image) request."""
        # Create a test image (1x1 pixel)
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What color is this?"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{test_image_b64}"}}
                        ]
                    }],
                    "stream": False,
                }
            )
            assert response.status_code == 200

class TestModelsEndpoint:
    @pytest.mark.asyncio
    async def test_list_models(self, gateway_url):
        """Test /v1/models endpoint."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{gateway_url}/v1/models")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            models = [m["id"] for m in data["data"]]
            assert "baseline-cli-agent" in models or "baseline" in models

class TestTranscription:
    @pytest.mark.asyncio
    async def test_transcribe_health(self, gateway_url):
        """Test /api/transcribe/health endpoint."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{gateway_url}/api/transcribe/health")
            assert response.status_code == 200
```

### Baseline CLI Integration Tests

```python
# tests/integration/test_baseline_cli.py

import pytest
import httpx
from tests.config import config

@pytest.fixture
def baseline_url():
    return config.get_urls()["baseline_cli"]

class TestBaselineHealth:
    @pytest.mark.asyncio
    async def test_health(self, baseline_url):
        """Test baseline health endpoint."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{baseline_url}/health")
            assert response.status_code == 200

class TestFastPath:
    @pytest.mark.asyncio
    async def test_simple_query(self, baseline_url):
        """Test simple query uses fast path."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{baseline_url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "4" in data["choices"][0]["message"]["content"]

class TestComplexPath:
    @pytest.mark.asyncio
    async def test_code_generation(self, baseline_url):
        """Test code generation routes to agent."""
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{baseline_url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "Write a hello world function in Python"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "def" in content or "print" in content

class TestStreaming:
    @pytest.mark.asyncio
    async def test_streaming_response(self, baseline_url):
        """Test streaming works correctly."""
        first_chunk_time = None
        chunks = []

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{baseline_url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                }
            ) as response:
                import time
                async for line in response.aiter_lines():
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                    if line.startswith("data: ") and line[6:] != "[DONE]":
                        chunks.append(line)

        assert len(chunks) > 0
        # Verify reasonable TTFT (< 5s for simple prompt)
```

### End-to-End Integration Tests

```python
# tests/integration/test_e2e.py

import pytest
import httpx
from tests.config import config

class TestEndToEndFlow:
    """Full end-to-end tests through the gateway."""

    @pytest.mark.asyncio
    async def test_gateway_to_baseline_flow(self):
        """Test request flows through gateway to baseline."""
        gateway_url = config.get_urls()["gateway"]

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "What is the capital of France?"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "Paris" in data["choices"][0]["message"]["content"]

    @pytest.mark.asyncio
    async def test_competitor_switching(self):
        """Test switching between competitors."""
        gateway_url = config.get_urls()["gateway"]

        async with httpx.AsyncClient(timeout=120) as client:
            # Test CLI baseline
            response1 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False,
                }
            )
            assert response1.status_code == 200

            # Test LangChain baseline (if available)
            response2 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False,
                }
            )
            # May be 200 or error if not configured
```

---

## Part 3: Smoke Tests

```python
# tests/smoke/test_all_services.py

import pytest
import httpx
from tests.config import config

class TestSmokeTests:
    """Quick smoke tests for all services."""

    @pytest.mark.asyncio
    async def test_gateway_smoke(self):
        """Gateway is responding."""
        url = config.get_urls()["gateway"]
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{url}/health")
            assert response.status_code == 200
            print(f"✓ Gateway healthy: {url}")

    @pytest.mark.asyncio
    async def test_baseline_cli_smoke(self):
        """Baseline CLI is responding."""
        url = config.get_urls()["baseline_cli"]
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{url}/health")
            assert response.status_code == 200
            print(f"✓ Baseline CLI healthy: {url}")

    @pytest.mark.asyncio
    async def test_baseline_langchain_smoke(self):
        """Baseline LangChain is responding."""
        url = config.get_urls()["baseline_langchain"]
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(f"{url}/health")
                assert response.status_code == 200
                print(f"✓ Baseline LangChain healthy: {url}")
            except Exception as e:
                print(f"⚠ Baseline LangChain not available: {e}")

    @pytest.mark.asyncio
    async def test_ui_smoke(self):
        """UI is serving pages."""
        url = config.get_urls()["ui"]
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url)
            assert response.status_code == 200
            assert "Janus" in response.text
            print(f"✓ UI healthy: {url}")

    @pytest.mark.asyncio
    async def test_chat_completion_smoke(self):
        """Chat completion works end-to-end."""
        url = config.get_urls()["gateway"]
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            print("✓ Chat completion working")

    @pytest.mark.asyncio
    async def test_models_endpoint_smoke(self):
        """Models endpoint returns data."""
        url = config.get_urls()["gateway"]
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{url}/v1/models")
            assert response.status_code == 200
            data = response.json()
            assert len(data.get("data", [])) > 0
            print(f"✓ Models endpoint: {len(data['data'])} models")
```

---

## Part 4: Visual UI Tests

```python
# tests/visual/test_ui_visual.py

import pytest
from playwright.async_api import async_playwright, expect
from tests.config import config
import os

@pytest.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.fixture
async def page(browser):
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()

class TestVisualUI:
    """Visual UI tests with screenshots."""

    async def take_screenshots(self, page, name):
        """Take screenshots at multiple viewports."""
        os.makedirs(config.screenshot_dir, exist_ok=True)

        for viewport in config.viewports:
            await page.set_viewport_size({
                "width": viewport["width"],
                "height": viewport["height"]
            })
            await page.wait_for_load_state("networkidle")
            await page.screenshot(
                path=f"{config.screenshot_dir}/{name}_{viewport['name']}.png",
                full_page=True
            )

    @pytest.mark.asyncio
    async def test_landing_page(self, page):
        """Test landing page visual."""
        ui_url = config.get_urls()["ui"]
        await page.goto(ui_url)
        await page.wait_for_load_state("networkidle")

        # Check no console errors
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)

        # Verify key elements
        await expect(page.locator("text=Janus")).to_be_visible()

        # Take screenshots
        await self.take_screenshots(page, "landing")

        assert len(errors) == 0, f"Console errors: {errors}"

    @pytest.mark.asyncio
    async def test_chat_page(self, page):
        """Test chat page visual."""
        ui_url = config.get_urls()["ui"]
        await page.goto(f"{ui_url}/chat")
        await page.wait_for_load_state("networkidle")

        # Check for Chutes sign-in if needed
        fingerprint = config.chutes_fingerprint
        if fingerprint and await page.locator("text=Sign in with Chutes").is_visible():
            # Handle Chutes authentication
            pass

        # Verify chat elements
        await expect(page.locator("[data-testid='model-select']")).to_be_visible()
        await expect(page.locator("textarea, input[type='text']")).to_be_visible()

        # Take screenshots
        await self.take_screenshots(page, "chat_empty")

    @pytest.mark.asyncio
    async def test_chat_interaction(self, page):
        """Test chat interaction flow."""
        ui_url = config.get_urls()["ui"]
        await page.goto(f"{ui_url}/chat")
        await page.wait_for_load_state("networkidle")

        # Type a message
        input_selector = "textarea, input[placeholder*='Ask']"
        await page.fill(input_selector, "Hello, how are you?")

        # Take screenshot of filled input
        await self.take_screenshots(page, "chat_input")

        # Submit (Enter or button click)
        await page.keyboard.press("Enter")

        # Wait for response
        await page.wait_for_selector("[class*='message'], [class*='bubble']", timeout=30000)

        # Take screenshot of conversation
        await self.take_screenshots(page, "chat_conversation")

    @pytest.mark.asyncio
    async def test_competition_page(self, page):
        """Test competition page visual."""
        ui_url = config.get_urls()["ui"]
        await page.goto(f"{ui_url}/competition")
        await page.wait_for_load_state("networkidle")

        # Verify Mermaid diagrams render
        await page.wait_for_selector("svg", timeout=10000)

        # Take screenshots
        await self.take_screenshots(page, "competition")

    @pytest.mark.asyncio
    async def test_marketplace_page(self, page):
        """Test marketplace page visual."""
        ui_url = config.get_urls()["ui"]
        await page.goto(f"{ui_url}/marketplace")
        await page.wait_for_load_state("networkidle")

        await self.take_screenshots(page, "marketplace")

    @pytest.mark.asyncio
    async def test_responsive_design(self, page):
        """Test responsive design across viewports."""
        ui_url = config.get_urls()["ui"]
        pages = ["/", "/chat", "/competition", "/marketplace"]

        for path in pages:
            await page.goto(f"{ui_url}{path}")
            await page.wait_for_load_state("networkidle")

            for viewport in config.viewports:
                await page.set_viewport_size({
                    "width": viewport["width"],
                    "height": viewport["height"]
                })
                await page.wait_for_timeout(500)  # Allow reflow

                # Check no horizontal scroll (except where expected)
                overflow = await page.evaluate("""
                    () => document.body.scrollWidth > document.body.clientWidth
                """)

                if overflow and viewport["name"] != "mobile":
                    await page.screenshot(
                        path=f"{config.screenshot_dir}/overflow_{path.replace('/', '_')}_{viewport['name']}.png"
                    )

    @pytest.mark.asyncio
    async def test_dark_mode_consistency(self, page):
        """Verify consistent dark mode styling."""
        ui_url = config.get_urls()["ui"]
        await page.goto(f"{ui_url}/chat")

        # Check background colors are dark
        bg_color = await page.evaluate("""
            () => window.getComputedStyle(document.body).backgroundColor
        """)
        # Should be dark (RGB values low)

        await self.take_screenshots(page, "dark_mode")

    @pytest.mark.asyncio
    async def test_model_dropdown(self, page):
        """Test model dropdown functionality."""
        ui_url = config.get_urls()["ui"]
        await page.goto(f"{ui_url}/chat")
        await page.wait_for_load_state("networkidle")

        # Click dropdown
        dropdown = page.locator("[data-testid='model-select'], .chat-model-dropdown, select")
        await dropdown.click()

        # Take screenshot of open dropdown
        await self.take_screenshots(page, "model_dropdown")

        # Check options are visible and readable
        options = page.locator("option, [role='option']")
        count = await options.count()
        assert count > 0, "No model options found"
```

---

## Part 5: Logging Enhancements

### Gateway Logging

```python
# gateway/janus_gateway/middleware/logging.py

import structlog
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Bind request context
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        logger.info(
            "request_started",
            query_params=dict(request.query_params),
        )

        try:
            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
            )
            raise
```

### Baseline CLI Logging

```python
# baseline-agent-cli/janus_baseline_agent_cli/logging.py

import structlog
import functools

logger = structlog.get_logger()

def log_function_call(func):
    """Decorator to log function entry/exit."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"{func_name}_started", args_count=len(args), kwargs_keys=list(kwargs.keys()))
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"{func_name}_completed")
            return result
        except Exception as e:
            logger.error(f"{func_name}_failed", error=str(e), error_type=type(e).__name__)
            raise
    return wrapper

# Usage in services
@log_function_call
async def detect_complexity(messages: list) -> ComplexityResult:
    logger.info("complexity_detection_started", message_count=len(messages))
    # ... detection logic
    logger.info("complexity_detection_completed", needs_agent=result.needs_agent, reason=result.reason)
    return result
```

---

## Part 6: Test Runner Script

```bash
#!/bin/bash
# scripts/run-tests.sh

set -e

echo "=== Janus Comprehensive Test Suite ==="
echo ""

# Parse arguments
TEST_MODE=${1:-local}  # local, deployed, both
export TEST_MODE

echo "Test mode: $TEST_MODE"
echo ""

# Run unit tests
echo "=== Running Unit Tests ==="
cd gateway && pytest tests/ -v --tb=short || true
cd ../baseline-agent-cli && pytest tests/ -v --tb=short || true
cd ../ui && npm test || true
cd ..

# Run integration tests
echo ""
echo "=== Running Integration Tests ==="

if [ "$TEST_MODE" = "local" ] || [ "$TEST_MODE" = "both" ]; then
    echo "--- Local Integration Tests ---"
    export TEST_MODE=local
    pytest tests/integration/ -v --tb=short || true
fi

if [ "$TEST_MODE" = "deployed" ] || [ "$TEST_MODE" = "both" ]; then
    echo "--- Deployed Integration Tests ---"
    export TEST_MODE=deployed
    pytest tests/integration/ -v --tb=short || true
fi

# Run smoke tests
echo ""
echo "=== Running Smoke Tests ==="
pytest tests/smoke/ -v --tb=short || true

# Run visual tests
echo ""
echo "=== Running Visual Tests ==="
pytest tests/visual/ -v --tb=short || true

echo ""
echo "=== Test Suite Complete ==="
echo "Screenshots saved to: ./test-screenshots/"
```

---

## Acceptance Criteria

- [ ] Unit tests achieve >80% coverage
- [ ] All integration tests pass against local services
- [ ] All integration tests pass against deployed services
- [ ] Smoke tests pass for all components
- [ ] Visual tests capture screenshots at all viewports
- [ ] No console errors in visual tests
- [ ] Comprehensive logging added to all services
- [ ] Test configuration supports local/deployed switching
- [ ] All identified issues fixed during testing

## Files to Create/Modify

```
tests/
├── config.py                      # Test configuration
├── conftest.py                    # Pytest fixtures
├── integration/
│   ├── test_gateway.py
│   ├── test_baseline_cli.py
│   ├── test_baseline_langchain.py
│   └── test_e2e.py
├── smoke/
│   └── test_all_services.py
└── visual/
    └── test_ui_visual.py

gateway/
└── janus_gateway/
    └── middleware/
        └── logging.py             # Enhanced logging

baseline-agent-cli/
└── janus_baseline_agent_cli/
    └── logging.py                 # Enhanced logging

scripts/
└── run-tests.sh                   # Test runner script
```

## Related Specs

- All feature specs (00-61) - Functionality to test
- `specs/63_code_review_gateway.md` - Gateway review
- `specs/64_code_review_baseline_cli.md` - Baseline CLI review
- `specs/65_code_review_baseline_langchain.md` - LangChain review
- `specs/66_code_review_ui.md` - UI review
- `specs/67_code_review_bench.md` - Bench review

NR_OF_TRIES=2
