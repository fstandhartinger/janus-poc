"""Tool functions for desktop GUI automation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .gui_automation import AccessibilityTree, GUIAutomation, ScreenRegion
from .vision import analyze_screenshot

# Global instances
_gui = GUIAutomation()
_a11y = AccessibilityTree()


def gui_click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> Dict[str, Any]:
    """Click at screen coordinates.

    Args:
        x: X coordinate
        y: Y coordinate
        button: Mouse button ('left', 'right', 'middle')
        clicks: Number of clicks (1 for single, 2 for double)

    Returns:
        Result with screenshot after click
    """
    _gui.click(x, y, button=button, clicks=clicks)
    screenshot = _gui.screenshot_base64()
    return {
        "success": True,
        "action": f"{button} click at ({x}, {y})",
        "screenshot": screenshot,
    }


def gui_type(text: str) -> Dict[str, Any]:
    """Type text at current cursor position.

    Args:
        text: Text to type

    Returns:
        Result with confirmation
    """
    _gui.type_text(text)
    return {
        "success": True,
        "action": f"Typed {len(text)} characters",
    }


def gui_hotkey(*keys: str) -> Dict[str, Any]:
    """Press keyboard shortcut.

    Args:
        keys: Keys to press together (e.g., 'ctrl', 's')

    Returns:
        Result with confirmation
    """
    if len(keys) == 1 and isinstance(keys[0], (list, tuple)):
        keys = tuple(str(key) for key in keys[0])
    _gui.hotkey(*keys)
    screenshot = _gui.screenshot_base64()
    return {
        "success": True,
        "action": f"Pressed {'+'.join(keys)}",
        "screenshot": screenshot,
    }


def gui_screenshot(region: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Capture screenshot of desktop or region.

    Args:
        region: Optional dict with x, y, width, height

    Returns:
        Base64-encoded screenshot
    """
    screen_region = None
    if region:
        screen_region = ScreenRegion(
            x=region["x"],
            y=region["y"],
            width=region["width"],
            height=region["height"],
        )

    screenshot = _gui.screenshot_base64(screen_region)
    width, height = _gui.get_screen_size()

    return {
        "success": True,
        "screenshot": screenshot,
        "screen_size": {"width": width, "height": height},
    }


def gui_find_element(
    name: str | None = None,
    role: str | None = None,
    partial: bool = True,
) -> Dict[str, Any]:
    """Find UI element using accessibility tree.

    Args:
        name: Element name to search for
        role: Element role (button, textbox, etc.)
        partial: Match partial names

    Returns:
        List of found elements with bounds
    """
    elements = []

    if name:
        found = _a11y.find_by_name(name, partial=partial)
        elements.extend(found)

    if role:
        found = _a11y.find_by_role(role)
        elements.extend(found)

    results = []
    for elem in elements[:20]:
        results.append(
            {
                "name": elem.name,
                "role": elem.role,
                "description": elem.description,
                "bounds": {
                    "x": elem.bounds.x,
                    "y": elem.bounds.y,
                    "width": elem.bounds.width,
                    "height": elem.bounds.height,
                    "center": elem.bounds.center,
                },
                "states": elem.states,
            }
        )

    return {
        "success": True,
        "elements": results,
        "count": len(results),
    }


def gui_click_element(name: str | None = None, role: str | None = None) -> Dict[str, Any]:
    """Find and click a UI element.

    Args:
        name: Element name
        role: Element role

    Returns:
        Result with screenshot after click
    """
    result = gui_find_element(name=name, role=role)

    if not result["elements"]:
        return {
            "success": False,
            "error": f"Element not found: name={name}, role={role}",
        }

    elem = result["elements"][0]
    center = elem["bounds"]["center"]
    return gui_click(center[0], center[1])


def gui_analyze_screen(prompt: str = "Describe what you see on screen") -> Dict[str, Any]:
    """Capture and analyze screen with vision model.

    Args:
        prompt: Question about the screen content

    Returns:
        Vision model analysis
    """
    screenshot = _gui.screenshot_base64()
    analysis = analyze_screenshot(screenshot, prompt)

    return {
        "success": True,
        "screenshot": screenshot,
        "analysis": analysis,
    }


def gui_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
) -> Dict[str, Any]:
    """Drag from start to end coordinates.

    Args:
        start_x, start_y: Starting position
        end_x, end_y: Ending position

    Returns:
        Result with screenshot
    """
    _gui.drag(start_x, start_y, end_x, end_y)
    screenshot = _gui.screenshot_base64()
    return {
        "success": True,
        "action": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})",
        "screenshot": screenshot,
    }


def gui_scroll(clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    """Scroll at position.

    Args:
        clicks: Positive for up, negative for down
        x, y: Position to scroll at

    Returns:
        Result with screenshot
    """
    _gui.scroll(clicks, x, y)
    screenshot = _gui.screenshot_base64()
    return {
        "success": True,
        "action": f"Scrolled {clicks} clicks",
        "screenshot": screenshot,
    }
