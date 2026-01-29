"""Git repository tools for the LangChain baseline."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class CloneRepositoryInput(BaseModel):
    """Input schema for cloning a repository."""

    url: str = Field(description="Git repository URL")
    branch: str = Field(default="main", description="Branch to clone")


class ListRepositoryFilesInput(BaseModel):
    """Input schema for listing repository files."""

    repo_path: str = Field(description="Path to the cloned repository")
    pattern: str = Field(default="*", description="Glob pattern to filter files")


class ReadRepositoryFileInput(BaseModel):
    """Input schema for reading repository file contents."""

    file_path: str = Field(description="Path to the file to read")


class CloneRepositoryTool(BaseTool):
    name: str = "clone_repository"
    description: str = "Clone a git repository and return the path."
    args_schema: type[BaseModel] = CloneRepositoryInput

    timeout_seconds: int = 120

    def _run(self, url: str, branch: str = "main") -> str:
        work_dir = tempfile.mkdtemp(prefix="janus_repo_")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, url, work_dir],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            detail = stderr or stdout or "unknown error"
            raise RuntimeError(f"Git clone failed: {detail}")

        return work_dir

    async def _arun(self, url: str, branch: str = "main") -> str:
        return self._run(url, branch)


class ListRepositoryFilesTool(BaseTool):
    name: str = "list_repository_files"
    description: str = "List files in a cloned repository."
    args_schema: type[BaseModel] = ListRepositoryFilesInput

    max_results: int = 100

    def _run(self, repo_path: str, pattern: str = "*") -> str:
        repo = Path(repo_path)
        if not repo.exists():
            return "Repository path not found."

        files: list[Path] = []
        for path in repo.rglob(pattern):
            if ".git" in path.parts:
                continue
            files.append(path)
            if len(files) >= self.max_results:
                break

        return "\n".join(str(path) for path in files)

    async def _arun(self, repo_path: str, pattern: str = "*") -> str:
        return self._run(repo_path, pattern)


class ReadRepositoryFileTool(BaseTool):
    name: str = "read_repository_file"
    description: str = "Read a file from a cloned repository."
    args_schema: type[BaseModel] = ReadRepositoryFileInput

    max_chars: int = 50000

    def _run(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return f"File not found: {path.name}"

        content = path.read_text(encoding="utf-8", errors="ignore")
        if len(content) > self.max_chars:
            content = content[: self.max_chars] + "\n\n[... truncated ...]"

        return content

    async def _arun(self, file_path: str) -> str:
        return self._run(file_path)


clone_repository_tool = CloneRepositoryTool()
list_repository_files_tool = ListRepositoryFilesTool()
read_repository_file_tool = ReadRepositoryFileTool()
