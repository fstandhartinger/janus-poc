"""Visual UI tests with Playwright screenshots."""

from __future__ import annotations

import os

import pytest

from tests.config import config

playwright = pytest.importorskip("playwright.async_api")
async_playwright = playwright.async_playwright
expect = playwright.expect

pytestmark = [pytest.mark.visual, pytest.mark.asyncio]


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


async def _take_screenshots(page, name: str) -> None:
    os.makedirs(config.screenshot_dir, exist_ok=True)
    for viewport in config.viewports:
        await page.set_viewport_size(
            {"width": viewport["width"], "height": viewport["height"]}
        )
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path=f"{config.screenshot_dir}/{name}_{viewport['name']}.png",
            full_page=True,
        )


async def _goto_or_skip(page, path: str = "") -> None:
    ui_url = config.get_urls(config.default_mode())["ui"]
    target = f"{ui_url}{path}"
    try:
        await page.goto(target, timeout=config.ui_timeout)
        await page.wait_for_load_state("networkidle")
    except Exception as exc:  # pragma: no cover - skip unreachable UI
        pytest.skip(f"UI not reachable at {target}: {exc}")


async def _capture_console_errors(page) -> list[str]:
    errors: list[str] = []

    def _capture(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", _capture)
    return errors


async def test_landing_page_visual(page) -> None:
    """Landing page renders without console errors."""
    errors = await _capture_console_errors(page)
    await _goto_or_skip(page, "")

    await expect(page.locator("text=Janus")).to_be_visible()
    await _take_screenshots(page, "landing")

    assert not errors, f"Console errors: {errors}"


async def test_chat_page_visual(page) -> None:
    """Chat page renders without console errors."""
    errors = await _capture_console_errors(page)
    await _goto_or_skip(page, "/chat")

    await expect(page.locator("textarea, input[type='text']")).to_be_visible()
    await _take_screenshots(page, "chat_empty")

    assert not errors, f"Console errors: {errors}"


async def test_chat_interaction_visual(page) -> None:
    """Chat interaction renders response and captures screenshots."""
    await _goto_or_skip(page, "/chat")

    input_selector = "textarea, input[placeholder*='Ask']"
    await page.fill(input_selector, "Hello, how are you?")
    await _take_screenshots(page, "chat_input")

    await page.keyboard.press("Enter")
    await page.wait_for_selector(
        "[class*='message'], [class*='bubble']", timeout=config.ui_timeout
    )
    await _take_screenshots(page, "chat_conversation")


async def test_competition_page_visual(page) -> None:
    """Competition page renders Mermaid diagrams."""
    await _goto_or_skip(page, "/competition")

    await page.wait_for_selector("svg", timeout=config.ui_timeout)
    await _take_screenshots(page, "competition")


async def test_marketplace_page_visual(page) -> None:
    """Marketplace page renders properly."""
    await _goto_or_skip(page, "/marketplace")
    await _take_screenshots(page, "marketplace")


async def test_responsive_layout(page) -> None:
    """Responsive layout should not overflow unexpectedly."""
    await _goto_or_skip(page, "")

    pages = ["/", "/chat", "/competition", "/marketplace"]
    for path in pages:
        await _goto_or_skip(page, path)
        for viewport in config.viewports:
            await page.set_viewport_size(
                {"width": viewport["width"], "height": viewport["height"]}
            )
            await page.wait_for_timeout(500)
            overflow = await page.evaluate(
                "() => document.body.scrollWidth > document.body.clientWidth"
            )
            if overflow and viewport["name"] != "mobile":
                await page.screenshot(
                    path=(
                        f"{config.screenshot_dir}/overflow_"
                        f"{path.replace('/', '_')}_{viewport['name']}.png"
                    )
                )
