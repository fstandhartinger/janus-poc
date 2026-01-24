"""Browser automation with screenshot streaming for Janus agents."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Screenshot:
    """A browser screenshot."""

    data: bytes  # PNG image data
    url: str
    title: str
    timestamp: float


def _default_screenshot_handler(shot: Screenshot) -> None:
    target_dir = os.environ.get("JANUS_SCREENSHOT_DIR", "/workspace/artifacts/screenshots")
    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError:
        return

    stamp_ms = int(shot.timestamp * 1000)
    token = uuid.uuid4().hex[:6]
    base_name = f"screenshot-{stamp_ms}-{token}"
    image_path = os.path.join(target_dir, f"{base_name}.png")
    meta_path = os.path.join(target_dir, f"{base_name}.json")

    try:
        with open(image_path, "wb") as handle:
            handle.write(shot.data)
        with open(meta_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "url": shot.url,
                    "title": shot.title,
                    "timestamp": shot.timestamp,
                },
                handle,
            )
    except OSError:
        return


class BrowserSession:
    """Playwright browser session with screenshot capabilities."""

    def __init__(
        self,
        headless: bool = True,
        viewport: tuple[int, int] = (1280, 720),
        on_screenshot: Optional[Callable[[Screenshot], None]] = None,
    ):
        self.headless = headless
        self.viewport = viewport
        self.on_screenshot = on_screenshot or _default_screenshot_handler
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def __aenter__(self) -> "BrowserSession":
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def start(self) -> None:
        """Start browser session."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": self.viewport[0], "height": self.viewport[1]},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self._page = await self._context.new_page()

    async def close(self) -> None:
        """Close browser session."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def goto(self, url: str, wait_until: str = "networkidle") -> Screenshot:
        """Navigate to URL and return screenshot."""
        if url.lower().startswith("file://"):
            raise ValueError("file:// URLs are not allowed")
        await self._page.goto(url, wait_until=wait_until)
        return await self.screenshot()

    async def screenshot(self, full_page: bool = False) -> Screenshot:
        """Take screenshot of current page."""
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

    async def evaluate(self, script: str) -> object:
        """Execute JavaScript and return result."""
        return await self._page.evaluate(script)

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        """Wait for element to appear."""
        await self._page.wait_for_selector(selector, timeout=timeout)

    async def get_accessibility_tree(self) -> dict:
        """Get accessibility tree (useful for understanding page structure)."""
        return await self._page.accessibility.snapshot()


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


async def browse_and_extract(
    url: str,
    actions: list[dict] | None = None,
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
    screenshots: list[Screenshot] = []

    def capture(shot: Screenshot) -> None:
        screenshots.append(shot)
        _default_screenshot_handler(shot)

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
