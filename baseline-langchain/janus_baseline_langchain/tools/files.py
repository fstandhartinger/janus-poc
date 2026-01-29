"""File operation tools for artifacts."""

from __future__ import annotations

import tempfile
from pathlib import Path

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from janus_baseline_langchain.services import add_artifact, get_artifact_manager


class FileWriteInput(BaseModel):
    """Input schema for writing a file."""

    filename: str = Field(description="Name of the file to write")
    content: str = Field(description="File content")
    mime_type: str | None = Field(default=None, description="Optional MIME type")


class FileReadInput(BaseModel):
    """Input schema for reading a file."""

    filename: str = Field(description="Name of the file to read")


class CreateDirectoryInput(BaseModel):
    """Input schema for creating a directory."""

    path: str = Field(description="Directory path to create")


class FileWriteTool(BaseTool):
    name: str = "write_file"
    description: str = "Write content to a file and create an artifact."
    args_schema: type[BaseModel] = FileWriteInput

    def _run(self, filename: str, content: str, mime_type: str | None = None) -> str:
        manager = get_artifact_manager()
        artifact = manager.create_artifact(filename, content, mime_type)
        add_artifact(artifact)
        return f"File written: {artifact.display_name} ({artifact.url})"

    async def _arun(self, filename: str, content: str, mime_type: str | None = None) -> str:
        return self._run(filename, content, mime_type)


class FileReadTool(BaseTool):
    name: str = "read_file"
    description: str = "Read content from a previously written file."
    args_schema: type[BaseModel] = FileReadInput

    def _run(self, filename: str) -> str:
        manager = get_artifact_manager()
        safe_name = Path(filename).name
        try:
            path = manager.resolve_path(safe_name)
        except ValueError:
            return "File not found: invalid path"
        if not path.exists():
            return f"File not found: {safe_name}"
        return path.read_text(encoding="utf-8", errors="ignore")

    async def _arun(self, filename: str) -> str:
        return self._run(filename)


class CreateDirectoryTool(BaseTool):
    name: str = "create_directory"
    description: str = "Create a working directory for file operations."
    args_schema: type[BaseModel] = CreateDirectoryInput

    def _resolve_path(self, path: str) -> Path:
        base_dir = Path(tempfile.gettempdir()) / "janus_work"
        candidate = (base_dir / path).resolve()
        if base_dir not in candidate.parents and candidate != base_dir:
            raise ValueError("Invalid path")
        return candidate

    def _run(self, path: str) -> str:
        try:
            target = self._resolve_path(path)
        except ValueError:
            return "Invalid path"

        target.mkdir(parents=True, exist_ok=True)
        return str(target)

    async def _arun(self, path: str) -> str:
        return self._run(path)


file_write_tool = FileWriteTool()
file_read_tool = FileReadTool()
create_directory_tool = CreateDirectoryTool()
