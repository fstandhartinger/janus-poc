"""Desktop GUI automation using PyAutoGUI and accessibility APIs."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pyautogui
import pyatspi2
from PIL import Image


@dataclass
class ScreenRegion:
    """Represents a region of the screen."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class AccessibleElement:
    """Represents an accessible UI element."""

    name: str
    role: str
    description: str
    bounds: ScreenRegion
    states: List[str]
    children: List["AccessibleElement"]


class GUIAutomation:
    """Desktop GUI automation using PyAutoGUI and accessibility APIs."""

    def __init__(self, fail_safe: bool = True) -> None:
        """Initialize GUI automation.

        Args:
            fail_safe: If True, moving mouse to corner aborts automation
        """
        pyautogui.FAILSAFE = fail_safe
        pyautogui.PAUSE = 0.1

    # Mouse Actions

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        """Click at screen coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            button: 'left', 'right', or 'middle'
            clicks: Number of clicks (2 for double-click)
        """
        pyautogui.click(x, y, button=button, clicks=clicks)

    def double_click(self, x: int, y: int) -> None:
        """Double-click at coordinates."""
        self.click(x, y, clicks=2)

    def right_click(self, x: int, y: int) -> None:
        """Right-click at coordinates."""
        self.click(x, y, button="right")

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
    ) -> None:
        """Drag from start to end coordinates.

        Args:
            start_x, start_y: Starting position
            end_x, end_y: Ending position
            duration: Time for drag in seconds
        """
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Scroll the mouse wheel.

        Args:
            clicks: Positive for up, negative for down
            x, y: Position to scroll at (current position if None)
        """
        pyautogui.scroll(clicks, x, y)

    def move_to(self, x: int, y: int, duration: float = 0.25) -> None:
        """Move mouse to coordinates."""
        pyautogui.moveTo(x, y, duration=duration)

    # Keyboard Actions

    def type_text(self, text: str, interval: float = 0.05) -> None:
        """Type text string.

        Args:
            text: Text to type
            interval: Pause between characters
        """
        pyautogui.typewrite(text, interval=interval)

    def press(self, key: str) -> None:
        """Press a single key.

        Args:
            key: Key name (e.g., 'enter', 'tab', 'escape', 'f1')
        """
        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        """Press key combination.

        Args:
            keys: Keys to press together (e.g., 'ctrl', 'c')
        """
        pyautogui.hotkey(*keys)

    def key_down(self, key: str) -> None:
        """Hold a key down."""
        pyautogui.keyDown(key)

    def key_up(self, key: str) -> None:
        """Release a key."""
        pyautogui.keyUp(key)

    # Screenshot Actions

    def screenshot(self, region: Optional[ScreenRegion] = None) -> Image.Image:
        """Capture screenshot.

        Args:
            region: Optional region to capture (full screen if None)

        Returns:
            PIL Image of screenshot
        """
        if region:
            return pyautogui.screenshot(region=(
                region.x,
                region.y,
                region.width,
                region.height,
            ))
        return pyautogui.screenshot()

    def screenshot_base64(self, region: Optional[ScreenRegion] = None) -> str:
        """Capture screenshot as base64.

        Returns:
            Base64-encoded PNG image
        """
        img = self.screenshot(region)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    def locate_on_screen(
        self, image_path: str, confidence: float = 0.9
    ) -> Optional[ScreenRegion]:
        """Find image on screen.

        Args:
            image_path: Path to image to find
            confidence: Match confidence (0-1)

        Returns:
            ScreenRegion if found, None otherwise
        """
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                return ScreenRegion(
                    x=location.left,
                    y=location.top,
                    width=location.width,
                    height=location.height,
                )
        except pyautogui.ImageNotFoundException:
            pass
        return None

    # Screen Info

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        return pyautogui.size()

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return pyautogui.position()


class AccessibilityTree:
    """Navigate UI via accessibility APIs (AT-SPI2 on Linux)."""

    def __init__(self) -> None:
        """Initialize accessibility tree access."""
        self._registry = pyatspi2.Registry

    def get_desktop(self) -> AccessibleElement:
        """Get the desktop root element."""
        desktop = self._registry.getDesktop(0)
        return self._wrap_accessible(desktop)

    def get_focused_application(self) -> Optional[AccessibleElement]:
        """Get the currently focused application."""
        desktop = self._registry.getDesktop(0)
        for i in range(desktop.childCount):
            app = desktop.getChildAtIndex(i)
            if app and self._has_focused_child(app):
                return self._wrap_accessible(app)
        return None

    def find_by_name(self, name: str, partial: bool = False) -> List[AccessibleElement]:
        """Find elements by name.

        Args:
            name: Name to search for
            partial: If True, match partial names

        Returns:
            List of matching elements
        """
        results: List[AccessibleElement] = []
        self._search_by_name(self.get_desktop(), name, partial, results)
        return results

    def find_by_role(self, role: str) -> List[AccessibleElement]:
        """Find elements by role (button, textbox, etc.)."""
        results: List[AccessibleElement] = []
        self._search_by_role(self.get_desktop(), role, results)
        return results

    def _wrap_accessible(self, obj) -> AccessibleElement:
        """Wrap AT-SPI object in our dataclass."""
        try:
            component = obj.queryComponent()
            bounds = component.getExtents(pyatspi2.DESKTOP_COORDS)
            region = ScreenRegion(bounds.x, bounds.y, bounds.width, bounds.height)
        except Exception:
            region = ScreenRegion(0, 0, 0, 0)

        children: List[AccessibleElement] = []
        for i in range(obj.childCount):
            child = obj.getChildAtIndex(i)
            if child:
                children.append(self._wrap_accessible(child))

        return AccessibleElement(
            name=obj.name or "",
            role=obj.getRoleName(),
            description=obj.description or "",
            bounds=region,
            states=[state.value_name for state in obj.getState().getStates()],
            children=children,
        )

    def _has_focused_child(self, obj) -> bool:
        """Check if object or children have focus."""
        states = obj.getState().getStates()
        if pyatspi2.STATE_FOCUSED in states:
            return True
        for i in range(obj.childCount):
            child = obj.getChildAtIndex(i)
            if child and self._has_focused_child(child):
                return True
        return False

    def _search_by_name(
        self,
        element: AccessibleElement,
        name: str,
        partial: bool,
        results: List[AccessibleElement],
    ) -> None:
        """Recursively search for elements by name."""
        if partial:
            if name.lower() in element.name.lower():
                results.append(element)
        else:
            if element.name.lower() == name.lower():
                results.append(element)
        for child in element.children:
            self._search_by_name(child, name, partial, results)

    def _search_by_role(
        self, element: AccessibleElement, role: str, results: List[AccessibleElement]
    ) -> None:
        """Recursively search for elements by role."""
        if element.role.lower() == role.lower():
            results.append(element)
        for child in element.children:
            self._search_by_role(child, role, results)
