"""Artifact management for baseline-langchain."""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Optional

from janus_baseline_langchain.config import get_settings
from janus_baseline_langchain.models import Artifact, ArtifactType


class ArtifactManager:
    """Manage creation and serving of local and remote artifacts."""

    def __init__(self, artifacts_dir: str, ttl_seconds: int, base_url: str = "/artifacts") -> None:
        self._artifacts_dir = Path(artifacts_dir)
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = ttl_seconds
        self._base_url = base_url.rstrip("/")

    @property
    def artifacts_dir(self) -> Path:
        return self._artifacts_dir

    def _safe_filename(self, filename: str) -> str:
        return Path(filename).name or "artifact"

    def _artifact_type_for(self, mime_type: str) -> ArtifactType:
        if mime_type.startswith("image/"):
            return ArtifactType.IMAGE
        if mime_type.startswith("application/octet-stream"):
            return ArtifactType.BINARY
        return ArtifactType.FILE

    def _artifact_url(self, stored_name: str) -> str:
        return f"{self._base_url}/{stored_name}"

    def resolve_path(self, stored_name: str) -> Path:
        """Resolve a stored artifact path safely within the artifacts directory."""
        candidate = (self._artifacts_dir / stored_name).resolve()
        if self._artifacts_dir not in candidate.parents and candidate != self._artifacts_dir:
            raise ValueError("Invalid artifact path")
        return candidate

    def create_artifact(
        self,
        filename: str,
        content: bytes | str,
        mime_type: Optional[str] = None,
    ) -> Artifact:
        """Create a local artifact and return its metadata."""
        safe_name = self._safe_filename(filename)
        artifact_id = uuid.uuid4().hex[:12]
        path = self._artifacts_dir / safe_name

        if isinstance(content, str):
            data = content.encode("utf-8")
            path.write_text(content, encoding="utf-8")
        else:
            data = content
            path.write_bytes(content)

        resolved_mime = mime_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        sha = hashlib.sha256(data).hexdigest()
        size = len(data)

        return Artifact(
            id=artifact_id,
            type=self._artifact_type_for(resolved_mime),
            mime_type=resolved_mime,
            display_name=safe_name,
            size_bytes=size,
            sha256=sha,
            ttl_seconds=self._ttl_seconds,
            url=self._artifact_url(safe_name),
        )

    def create_remote_artifact(
        self,
        name: str,
        url: str,
        mime_type: Optional[str] = None,
    ) -> Artifact:
        """Create metadata for an externally hosted artifact."""
        safe_name = self._safe_filename(name)
        artifact_id = uuid.uuid4().hex[:12]
        resolved_mime = mime_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        return Artifact(
            id=artifact_id,
            type=self._artifact_type_for(resolved_mime),
            mime_type=resolved_mime,
            display_name=safe_name,
            size_bytes=0,
            ttl_seconds=self._ttl_seconds,
            url=url,
        )


@lru_cache
def get_artifact_manager() -> ArtifactManager:
    """Get cached artifact manager instance."""
    settings = get_settings()
    return ArtifactManager(
        artifacts_dir=settings.artifacts_dir,
        ttl_seconds=settings.artifact_ttl_seconds,
        base_url=settings.artifact_base_url,
    )
