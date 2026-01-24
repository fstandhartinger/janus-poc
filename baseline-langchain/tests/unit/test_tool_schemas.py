"""Unit tests for LangChain tool schemas."""

from __future__ import annotations

from typing import Any

from janus_baseline_langchain.tools import (
    code_execution_tool,
    image_generation_tool,
    text_to_speech_tool,
    web_search_tool,
)


def _schema_from_tool(tool: Any) -> dict[str, Any]:
    schema_obj = getattr(tool, "args_schema", None)
    if schema_obj is not None:
        if hasattr(schema_obj, "model_json_schema"):
            return schema_obj.model_json_schema()
        if hasattr(schema_obj, "schema"):
            return schema_obj.schema()
    schema_obj = getattr(tool, "tool_call_schema", None)
    if schema_obj is not None:
        if hasattr(schema_obj, "model_json_schema"):
            return schema_obj.model_json_schema()
        if hasattr(schema_obj, "schema"):
            return schema_obj.schema()
    if isinstance(getattr(tool, "args", None), dict):
        return {"type": "object", "properties": tool.args}
    return {}


def test_tool_schemas_present() -> None:
    tools = [
        web_search_tool,
        image_generation_tool,
        text_to_speech_tool,
        code_execution_tool,
    ]

    for tool in tools:
        assert tool.name
        assert tool.description
        schema = _schema_from_tool(tool)
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
