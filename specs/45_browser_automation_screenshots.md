# Spec 45: Browser Automation & Screenshot Streaming

## Status: DRAFT

## Context / Why

The agent should be able to browse the web interactively:
- Navigate to URLs and interact with pages
- Fill forms, click buttons, extract content
- Take screenshots and analyze them with vision models
- Stream screenshots back to the user so they can watch the agent work

This enables tasks like:
- Web scraping with JavaScript rendering
- Testing web applications
- Automating web workflows
- Visual verification of websites

## Goals

- Provide Playwright-based browser automation to agent
- Stream screenshots back to chat UI in real-time
- Use vision models to interpret screenshots
- Support both headless and visual debugging modes

## Non-Goals

- Full browser session sharing (just screenshots)
- Browser extensions
- Multi-browser support (Chromium only)

## Functional Requirements

### FR-1: Playwright Client Library

```python
# agent-pack/lib/browser.py
"""Browser automation with screenshot streaming for Janus agents."""

import os
import asyncio
import base64
from typing import Optional, AsyncIterator, Callable
from dataclasses import dataclass


@dataclass
class Screenshot:
    """A browser screenshot."""
    data: bytes  # PNG image data
    url: str
    title: str
    timestamp: float


class BrowserSession:
    """Playwright browser session with screenshot capabilities."""

    def __init__(
        self,
        headless: bool = True,
        viewport: tuple[int, int] = (1280, 720),
        on_screenshot: Callable[[Screenshot], None] = None,
    ):
        self.headless = headless
        self.viewport = viewport
        self.on_screenshot = on_screenshot
        self._browser = None
        self._context = None
        self._page = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def start(self):
        """Start browser session."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox'],
        )
        self._context = await self._browser.new_context(
            viewport={'width': self.viewport[0], 'height': self.viewport[1]},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        )
        self._page = await self._context.new_page()

    async def close(self):
        """Close browser session."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def goto(self, url: str, wait_until: str = "networkidle") -> Screenshot:
        """Navigate to URL and return screenshot."""
        await self._page.goto(url, wait_until=wait_until)
        return await self.screenshot()

    async def screenshot(self, full_page: bool = False) -> Screenshot:
        """Take screenshot of current page."""
        import time

        data = await self._page.screenshot(full_page=full_page)
        shot = Screenshot(
            data=data,
            url=self._page.url,
            title=await self._page.title(),
            timestamp=time.time(),
        )

        if self.on_screenshot:
            self.on_screenshot(shot)

        return shot

    async def click(self, selector: str) -> Screenshot:
        """Click element and return screenshot."""
        await self._page.click(selector)
        await self._page.wait_for_load_state("networkidle")
        return await self.screenshot()

    async def fill(self, selector: str, value: str) -> None:
        """Fill input field."""
        await self._page.fill(selector, value)

    async def type(self, selector: str, text: str, delay: int = 50) -> None:
        """Type text with delay between keystrokes."""
        await self._page.type(selector, text, delay=delay)

    async def press(self, key: str) -> None:
        """Press keyboard key."""
        await self._page.keyboard.press(key)

    async def scroll(self, direction: str = "down", amount: int = 500) -> Screenshot:
        """Scroll page and return screenshot."""
        if direction == "down":
            await self._page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            await self._page.evaluate(f"window.scrollBy(0, -{amount})")
        await asyncio.sleep(0.5)
        return await self.screenshot()

    async def get_text(self, selector: str = "body") -> str:
        """Get text content of element."""
        return await self._page.text_content(selector) or ""

    async def get_html(self, selector: str = "body") -> str:
        """Get HTML content of element."""
        return await self._page.inner_html(selector)

    async def evaluate(self, script: str) -> any:
        """Execute JavaScript and return result."""
        return await self._page.evaluate(script)

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        """Wait for element to appear."""
        await self._page.wait_for_selector(selector, timeout=timeout)

    async def get_accessibility_tree(self) -> dict:
        """Get accessibility tree (useful for understanding page structure)."""
        return await self._page.accessibility.snapshot()


# Vision model integration
async def analyze_screenshot(
    screenshot: Screenshot,
    question: str,
    model: str = "Qwen/Qwen3-VL-235B-A22B-Instruct",
) -> str:
    """
    Analyze a screenshot using a vision model.

    Args:
        screenshot: Screenshot to analyze
        question: What to ask about the screenshot
        model: Vision model to use

    Returns:
        Model's analysis
    """
    import httpx

    api_key = os.environ.get("CHUTES_API_KEY")
    api_url = os.environ.get("CHUTES_API_URL", "https://api.chutes.ai/v1")

    # Convert to base64
    b64_image = base64.b64encode(screenshot.data).decode("utf-8")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{api_url}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64_image}",
                                },
                            },
                        ],
                    }
                ],
            },
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


# Convenience function for simple browsing
async def browse_and_extract(
    url: str,
    actions: list[dict] = None,
    extract_selector: str = "body",
) -> tuple[str, list[Screenshot]]:
    """
    Browse a URL, perform actions, and extract content.

    Args:
        url: URL to visit
        actions: List of actions like [{"click": "#btn"}, {"fill": {"selector": "#input", "value": "text"}}]
        extract_selector: CSS selector to extract text from

    Returns:
        Tuple of (extracted_text, screenshots)
    """
    screenshots = []

    def capture(shot: Screenshot):
        screenshots.append(shot)

    async with BrowserSession(on_screenshot=capture) as browser:
        await browser.goto(url)

        if actions:
            for action in actions:
                if "click" in action:
                    await browser.click(action["click"])
                elif "fill" in action:
                    await browser.fill(action["fill"]["selector"], action["fill"]["value"])
                elif "type" in action:
                    await browser.type(action["type"]["selector"], action["type"]["text"])
                elif "scroll" in action:
                    await browser.scroll(action.get("direction", "down"))
                elif "wait" in action:
                    await asyncio.sleep(action["wait"])

        text = await browser.get_text(extract_selector)
        return text, screenshots
```

### FR-2: Screenshot Streaming Protocol

Stream screenshots back to the chat UI via SSE:

```python
# gateway/janus_gateway/models/streaming.py

from pydantic import BaseModel
from typing import Optional
import base64


class ScreenshotEvent(BaseModel):
    """Screenshot streaming event."""
    type: str = "screenshot"
    data: dict  # {url, title, image_base64, timestamp}


def format_screenshot_sse(screenshot_data: bytes, url: str, title: str) -> str:
    """Format screenshot as SSE event."""
    import json
    import time

    event = {
        "type": "screenshot",
        "data": {
            "url": url,
            "title": title,
            "image_base64": base64.b64encode(screenshot_data).decode("utf-8"),
            "timestamp": time.time(),
        },
    }
    return f"data: {json.dumps(event)}\n\n"
```

### FR-3: Frontend Screenshot Display

```tsx
// ui/src/components/ScreenshotStream.tsx

import { useState, useEffect } from 'react';
import { ExternalLink, Maximize2 } from 'lucide-react';

interface ScreenshotData {
  url: string;
  title: string;
  image_base64: string;
  timestamp: number;
}

interface ScreenshotStreamProps {
  screenshots: ScreenshotData[];
  isLive: boolean;
}

export function ScreenshotStream({ screenshots, isLive }: ScreenshotStreamProps) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (screenshots.length === 0) return null;

  const latestScreenshot = screenshots[screenshots.length - 1];

  return (
    <div className="space-y-3">
      {/* Live indicator */}
      {isLive && (
        <div className="flex items-center gap-2 text-sm text-moss">
          <span className="w-2 h-2 bg-moss rounded-full animate-pulse" />
          Browser session active
        </div>
      )}

      {/* Current screenshot */}
      <div className="relative rounded-lg overflow-hidden border border-ink-700">
        <img
          src={`data:image/png;base64,${latestScreenshot.image_base64}`}
          alt={latestScreenshot.title}
          className="w-full"
        />

        {/* Overlay with URL */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
          <div className="flex items-center justify-between">
            <div className="text-sm text-white truncate max-w-[80%]">
              {latestScreenshot.url}
            </div>
            <button
              onClick={() => setExpanded(screenshots.length - 1)}
              className="p-1 rounded hover:bg-white/20"
            >
              <Maximize2 className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>
      </div>

      {/* Screenshot history (thumbnails) */}
      {screenshots.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {screenshots.map((shot, index) => (
            <button
              key={index}
              onClick={() => setExpanded(index)}
              className={`shrink-0 w-20 h-12 rounded overflow-hidden border-2 ${
                index === screenshots.length - 1 ? 'border-moss' : 'border-ink-700'
              }`}
            >
              <img
                src={`data:image/png;base64,${shot.image_base64}`}
                alt={`Step ${index + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
          ))}
        </div>
      )}

      {/* Expanded modal */}
      {expanded !== null && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setExpanded(null)}
        >
          <div className="max-w-[90vw] max-h-[90vh]">
            <img
              src={`data:image/png;base64,${screenshots[expanded].image_base64}`}
              alt={screenshots[expanded].title}
              className="max-w-full max-h-full object-contain"
            />
            <div className="text-center mt-2 text-white text-sm">
              {screenshots[expanded].url}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

### FR-4: System Prompt Addition

```markdown
### 🌐 Browser Automation

You can browse the web interactively and take screenshots:

```python
from lib.browser import BrowserSession, analyze_screenshot, browse_and_extract

# Basic browsing
async with BrowserSession() as browser:
    # Navigate
    shot = await browser.goto("https://example.com")

    # Interact
    await browser.fill("#search", "query")
    await browser.click("#submit")
    shot = await browser.screenshot()

    # Extract content
    text = await browser.get_text("article")

# Use vision model to understand what you see
analysis = await analyze_screenshot(
    shot,
    "What products are shown on this page?"
)

# Quick extraction
text, shots = await browse_and_extract(
    "https://news.ycombinator.com",
    actions=[
        {"scroll": "down"},
        {"wait": 1},
    ],
    extract_selector=".storylink",
)
```

**Screenshots are automatically streamed to the user** so they can watch your progress!

**Vision model analysis:**
- Use Qwen3-VL or Mistral-3.2 to interpret screenshots
- Useful for understanding complex UIs, charts, or visual content
```

## Non-Functional Requirements

### NFR-1: Performance

- Screenshot capture < 500ms
- Stream latency < 1 second
- Viewport: 1280x720 default

### NFR-2: Resource Management

- Single browser instance per agent
- Auto-close on task completion
- Memory limits enforced

### NFR-3: Security

- Sandboxed browser (no-sandbox flag in container)
- No file:// URLs
- No credential storage

## Acceptance Criteria

- [ ] Playwright library available to agent
- [ ] Screenshots stream to frontend
- [ ] Vision model analysis works
- [ ] Screenshot history displayed
- [ ] Expanded view modal works
- [ ] Browser auto-closes on completion

## Files to Create/Modify

```
baseline-agent-cli/
└── agent-pack/
    ├── bootstrap.sh           # MODIFY - Install Playwright
    └── lib/
        └── browser.py         # NEW

ui/
└── src/
    └── components/
        └── ScreenshotStream.tsx  # NEW

gateway/
└── janus_gateway/
    └── models/
        └── streaming.py       # MODIFY - Add screenshot event
```

## Related Specs

- `specs/38_multimodal_vision_models.md` - Vision model integration
- `specs/44_deep_research_integration.md` - Uses Playwright
- `specs/46_gui_automation.md` - Desktop GUI control
