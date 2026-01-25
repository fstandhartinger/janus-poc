# Spec 46: GUI Automation & Desktop Control

## Status: COMPLETE

## Context / Why

While Spec 45 covers browser automation for web pages, the agent also needs the ability to interact with desktop applications and native GUIs. This enables:

- Testing desktop applications
- Automating native software (IDEs, editors, design tools)
- Interacting with system dialogs
- Visual verification of desktop app states
- Accessibility tree navigation for robust element identification

This spec adds desktop GUI automation capabilities using PyAutoGUI and accessibility APIs.

## Goals

- Enable mouse/keyboard simulation for desktop apps
- Provide accessibility tree navigation
- Support screenshot capture and analysis
- Integrate with vision models for visual understanding
- Stream GUI screenshots to frontend

## Non-Goals

- Replace existing browser automation (Spec 45)
- Support mobile device automation
- Implement full RPA framework

## Functional Requirements

### FR-1: GUI Automation Library

```python
# baseline-agent-cli/janus_baseline_agent_cli/tools/gui_automation.py

import pyautogui
import pyatspi2
from PIL import Image
import io
import base64
from dataclasses import dataclass
from typing import Optional, Tuple, List

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
    children: List['AccessibleElement']

class GUIAutomation:
    """Desktop GUI automation using PyAutoGUI and accessibility APIs."""

    def __init__(self, fail_safe: bool = True):
        """Initialize GUI automation.

        Args:
            fail_safe: If True, moving mouse to corner aborts automation
        """
        pyautogui.FAILSAFE = fail_safe
        pyautogui.PAUSE = 0.1  # Small pause between actions

    # Mouse Actions

    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1):
        """Click at screen coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            button: 'left', 'right', or 'middle'
            clicks: Number of clicks (2 for double-click)
        """
        pyautogui.click(x, y, button=button, clicks=clicks)

    def double_click(self, x: int, y: int):
        """Double-click at coordinates."""
        self.click(x, y, clicks=2)

    def right_click(self, x: int, y: int):
        """Right-click at coordinates."""
        self.click(x, y, button='right')

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.5):
        """Drag from start to end coordinates.

        Args:
            start_x, start_y: Starting position
            end_x, end_y: Ending position
            duration: Time for drag in seconds
        """
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None):
        """Scroll the mouse wheel.

        Args:
            clicks: Positive for up, negative for down
            x, y: Position to scroll at (current position if None)
        """
        pyautogui.scroll(clicks, x, y)

    def move_to(self, x: int, y: int, duration: float = 0.25):
        """Move mouse to coordinates."""
        pyautogui.moveTo(x, y, duration=duration)

    # Keyboard Actions

    def type_text(self, text: str, interval: float = 0.05):
        """Type text string.

        Args:
            text: Text to type
            interval: Pause between characters
        """
        pyautogui.typewrite(text, interval=interval)

    def press(self, key: str):
        """Press a single key.

        Args:
            key: Key name (e.g., 'enter', 'tab', 'escape', 'f1')
        """
        pyautogui.press(key)

    def hotkey(self, *keys: str):
        """Press key combination.

        Args:
            keys: Keys to press together (e.g., 'ctrl', 'c')
        """
        pyautogui.hotkey(*keys)

    def key_down(self, key: str):
        """Hold a key down."""
        pyautogui.keyDown(key)

    def key_up(self, key: str):
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
                region.x, region.y, region.width, region.height
            ))
        return pyautogui.screenshot()

    def screenshot_base64(self, region: Optional[ScreenRegion] = None) -> str:
        """Capture screenshot as base64.

        Returns:
            Base64-encoded PNG image
        """
        img = self.screenshot(region)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()

    def locate_on_screen(self, image_path: str, confidence: float = 0.9) -> Optional[ScreenRegion]:
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
                    height=location.height
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

    def __init__(self):
        """Initialize accessibility tree access."""
        # AT-SPI2 requires running accessibility bus
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
        results = []
        self._search_by_name(self.get_desktop(), name, partial, results)
        return results

    def find_by_role(self, role: str) -> List[AccessibleElement]:
        """Find elements by role (button, textbox, etc.)."""
        results = []
        self._search_by_role(self.get_desktop(), role, results)
        return results

    def _wrap_accessible(self, obj) -> AccessibleElement:
        """Wrap AT-SPI object in our dataclass."""
        try:
            component = obj.queryComponent()
            bounds = component.getExtents(pyatspi2.DESKTOP_COORDS)
            region = ScreenRegion(bounds.x, bounds.y, bounds.width, bounds.height)
        except:
            region = ScreenRegion(0, 0, 0, 0)

        children = []
        for i in range(obj.childCount):
            child = obj.getChildAtIndex(i)
            if child:
                children.append(self._wrap_accessible(child))

        return AccessibleElement(
            name=obj.name or '',
            role=obj.getRoleName(),
            description=obj.description or '',
            bounds=region,
            states=[s.value_name for s in obj.getState().getStates()],
            children=children
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

    def _search_by_name(self, element: AccessibleElement, name: str,
                        partial: bool, results: List[AccessibleElement]):
        """Recursively search for elements by name."""
        if partial:
            if name.lower() in element.name.lower():
                results.append(element)
        else:
            if element.name.lower() == name.lower():
                results.append(element)
        for child in element.children:
            self._search_by_name(child, name, partial, results)

    def _search_by_role(self, element: AccessibleElement, role: str,
                        results: List[AccessibleElement]):
        """Recursively search for elements by role."""
        if element.role.lower() == role.lower():
            results.append(element)
        for child in element.children:
            self._search_by_role(child, role, results)
```

### FR-2: Agent Tools for GUI Automation

```python
# baseline-agent-cli/janus_baseline_agent_cli/tools/gui_tools.py

from .gui_automation import GUIAutomation, AccessibilityTree, ScreenRegion
from .vision import analyze_screenshot
from typing import Optional, Dict, Any

# Global instances
_gui = GUIAutomation()
_a11y = AccessibilityTree()

def gui_click(x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
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
        "screenshot": screenshot
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
        "action": f"Typed {len(text)} characters"
    }

def gui_hotkey(*keys: str) -> Dict[str, Any]:
    """Press keyboard shortcut.

    Args:
        keys: Keys to press together (e.g., 'ctrl', 's')

    Returns:
        Result with confirmation
    """
    _gui.hotkey(*keys)
    screenshot = _gui.screenshot_base64()
    return {
        "success": True,
        "action": f"Pressed {'+'.join(keys)}",
        "screenshot": screenshot
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
            x=region['x'],
            y=region['y'],
            width=region['width'],
            height=region['height']
        )

    screenshot = _gui.screenshot_base64(screen_region)
    width, height = _gui.get_screen_size()

    return {
        "success": True,
        "screenshot": screenshot,
        "screen_size": {"width": width, "height": height}
    }

def gui_find_element(name: str = None, role: str = None,
                     partial: bool = True) -> Dict[str, Any]:
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

    # Convert to serializable format
    results = []
    for elem in elements[:20]:  # Limit results
        results.append({
            "name": elem.name,
            "role": elem.role,
            "description": elem.description,
            "bounds": {
                "x": elem.bounds.x,
                "y": elem.bounds.y,
                "width": elem.bounds.width,
                "height": elem.bounds.height,
                "center": elem.bounds.center
            },
            "states": elem.states
        })

    return {
        "success": True,
        "elements": results,
        "count": len(results)
    }

def gui_click_element(name: str = None, role: str = None) -> Dict[str, Any]:
    """Find and click a UI element.

    Args:
        name: Element name
        role: Element role

    Returns:
        Result with screenshot after click
    """
    result = gui_find_element(name=name, role=role)

    if not result['elements']:
        return {
            "success": False,
            "error": f"Element not found: name={name}, role={role}"
        }

    # Click the first matching element
    elem = result['elements'][0]
    center = elem['bounds']['center']
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
        "analysis": analysis
    }

def gui_drag(start_x: int, start_y: int, end_x: int, end_y: int) -> Dict[str, Any]:
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
        "screenshot": screenshot
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
        "screenshot": screenshot
    }
```

### FR-3: Tool Registration

```python
# baseline-agent-cli/janus_baseline_agent_cli/tools/__init__.py

# Add GUI tools to the tool registry
GUI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "gui_screenshot",
            "description": "Capture screenshot of the desktop. Use this to see the current state of the screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "object",
                        "description": "Optional region to capture",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"}
                        }
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_click",
            "description": "Click at screen coordinates. First use gui_screenshot to see the screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "default": "left"
                    },
                    "clicks": {"type": "integer", "default": 1}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_type",
            "description": "Type text at the current cursor position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_hotkey",
            "description": "Press a keyboard shortcut (e.g., Ctrl+S, Alt+F4).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keys to press together (e.g., ['ctrl', 's'])"
                    }
                },
                "required": ["keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_find_element",
            "description": "Find UI element by name or role using accessibility tree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Element name to find"},
                    "role": {"type": "string", "description": "Element role (button, textbox, etc.)"},
                    "partial": {"type": "boolean", "default": True}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_click_element",
            "description": "Find and click a UI element by name or role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Element name"},
                    "role": {"type": "string", "description": "Element role"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_analyze_screen",
            "description": "Capture screenshot and analyze with vision model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "default": "Describe what you see on screen"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_drag",
            "description": "Drag from one position to another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer"},
                    "start_y": {"type": "integer"},
                    "end_x": {"type": "integer"},
                    "end_y": {"type": "integer"}
                },
                "required": ["start_x", "start_y", "end_x", "end_y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_scroll",
            "description": "Scroll mouse wheel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clicks": {"type": "integer", "description": "Positive=up, negative=down"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"}
                },
                "required": ["clicks"]
            }
        }
    }
]
```

### FR-4: Sandbox Configuration for GUI

```yaml
# sandy/sandbox-configs/gui-enabled.yaml

name: gui-sandbox
base_image: sandy-base:latest
packages:
  apt:
    - xvfb
    - x11vnc
    - python3-pyatspi
    - at-spi2-core
    - dbus-x11
    - libgtk-3-0
  pip:
    - pyautogui
    - pillow
    - python-xlib

environment:
  DISPLAY: ":99"
  DBUS_SESSION_BUS_ADDRESS: "unix:path=/run/dbus/system_bus_socket"

startup:
  - "Xvfb :99 -screen 0 1920x1080x24 &"
  - "dbus-daemon --session --fork"
  - "/usr/lib/at-spi2-core/at-spi-bus-launcher &"
  - "x11vnc -display :99 -forever -shared -nopw -listen 0.0.0.0 &"
```

### FR-5: VNC Streaming to Frontend

```typescript
// ui/src/components/VNCViewer.tsx

'use client';

import { useEffect, useRef, useState } from 'react';
import RFB from '@novnc/novnc/lib/rfb';

interface VNCViewerProps {
  sandboxUrl: string;
  vncPort?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export function VNCViewer({
  sandboxUrl,
  vncPort = 5900,
  onConnect,
  onDisconnect
}: VNCViewerProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<RFB | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const wsUrl = `${sandboxUrl.replace('http', 'ws')}/vnc`;

    try {
      const rfb = new RFB(canvasRef.current, wsUrl, {
        credentials: { password: '' },
      });

      rfb.addEventListener('connect', () => {
        setConnected(true);
        setError(null);
        onConnect?.();
      });

      rfb.addEventListener('disconnect', (e: CustomEvent) => {
        setConnected(false);
        if (e.detail.clean) {
          onDisconnect?.();
        } else {
          setError('Connection lost');
        }
      });

      rfb.scaleViewport = true;
      rfb.resizeSession = true;
      rfbRef.current = rfb;

      return () => {
        rfb.disconnect();
        rfbRef.current = null;
      };
    } catch (err) {
      setError(`Failed to connect: ${err}`);
    }
  }, [sandboxUrl, vncPort, onConnect, onDisconnect]);

  return (
    <div className="vnc-viewer">
      <div className="vnc-status">
        <span className={`vnc-indicator ${connected ? 'connected' : 'disconnected'}`} />
        <span>{connected ? 'Connected' : 'Disconnected'}</span>
      </div>

      {error && (
        <div className="vnc-error">{error}</div>
      )}

      <div
        ref={canvasRef}
        className="vnc-canvas"
        style={{ width: '100%', height: '600px' }}
      />
    </div>
  );
}
```

## Non-Functional Requirements

### NFR-1: Performance

- Screenshot capture < 100ms
- Mouse/keyboard actions < 50ms latency
- Accessibility tree queries < 500ms

### NFR-2: Reliability

- Failsafe: moving mouse to corner aborts automation
- Graceful handling of element not found
- Timeout on all operations

### NFR-3: Sandbox Isolation

- X11 display virtualized (Xvfb)
- No access to host display
- VNC for remote viewing only

## Acceptance Criteria

- [ ] PyAutoGUI mouse actions working (click, drag, scroll)
- [ ] PyAutoGUI keyboard actions working (type, hotkey)
- [ ] Screenshot capture working
- [ ] Accessibility tree navigation working
- [ ] Vision model analysis of screenshots working
- [ ] VNC streaming to frontend working
- [ ] Tool registration complete
- [ ] Sandbox Xvfb configuration working

## Files to Modify/Create

```
baseline-agent-cli/
├── janus_baseline_agent_cli/
│   └── tools/
│       ├── gui_automation.py    # NEW - Core GUI automation
│       ├── gui_tools.py         # NEW - Agent tool functions
│       └── __init__.py          # MODIFY - Register tools
│
sandy/
├── sandbox-configs/
│   └── gui-enabled.yaml         # NEW - GUI sandbox config
│
ui/
└── src/
    └── components/
        └── VNCViewer.tsx        # NEW - VNC viewer component
```

## Dependencies

```
# baseline-agent-cli/pyproject.toml
pyautogui>=0.9.54
pillow>=10.0.0
python-xlib>=0.33

# ui/package.json
"@novnc/novnc": "^1.4.0"
```

## Related Specs

- `specs/45_browser_automation_screenshots.md` - Browser automation
- `specs/41_enhanced_agent_system_prompt.md` - Agent capabilities
- `specs/43_agent_sandbox_management.md` - Sandbox creation

NR_OF_TRIES: 1
