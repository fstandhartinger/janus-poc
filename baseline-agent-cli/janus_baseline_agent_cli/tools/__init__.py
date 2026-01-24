"""Tool registry for baseline agent CLI."""

from __future__ import annotations

from janus_baseline_agent_cli.config import Settings, get_settings

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
                            "height": {"type": "integer"},
                        },
                    }
                },
            },
        },
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
                        "default": "left",
                    },
                    "clicks": {"type": "integer", "default": 1},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gui_type",
            "description": "Type text at the current cursor position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                },
                "required": ["text"],
            },
        },
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
                        "description": "Keys to press together (e.g., ['ctrl', 's'])",
                    }
                },
                "required": ["keys"],
            },
        },
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
                    "partial": {"type": "boolean", "default": True},
                },
            },
        },
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
                    "role": {"type": "string", "description": "Element role"},
                },
            },
        },
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
                        "default": "Describe what you see on screen",
                    }
                },
            },
        },
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
                    "end_y": {"type": "integer"},
                },
                "required": ["start_x", "start_y", "end_x", "end_y"],
            },
        },
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
                    "y": {"type": "integer"},
                },
                "required": ["clicks"],
            },
        },
    },
]

_BASE_TOOL_DEFINITIONS = {
    "web_search": {
        "name": "web_search",
        "description": "Search the web for up-to-date information.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    "code_execution": {
        "name": "code_execution",
        "description": "Execute Python code safely in the sandbox.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    },
    "file_read": {
        "name": "file_read",
        "description": "Read the contents of a file from the workspace.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    "file_write": {
        "name": "file_write",
        "description": "Write content to a file in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
}


def get_registered_tools(settings: Settings | None = None) -> dict[str, dict]:
    """Return tool definitions filtered by settings."""
    settings = settings or get_settings()
    tools: dict[str, dict] = {}

    for tool in GUI_TOOLS:
        function = tool.get("function", {})
        name = function.get("name")
        if name:
            tools[name] = function

    if settings.enable_web_search:
        tools["web_search"] = _BASE_TOOL_DEFINITIONS["web_search"]
    if settings.enable_code_execution:
        tools["code_execution"] = _BASE_TOOL_DEFINITIONS["code_execution"]
    if settings.enable_file_tools:
        tools["file_read"] = _BASE_TOOL_DEFINITIONS["file_read"]
        tools["file_write"] = _BASE_TOOL_DEFINITIONS["file_write"]

    return tools


__all__ = ["GUI_TOOLS", "get_registered_tools"]
