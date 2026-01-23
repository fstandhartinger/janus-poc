"""Artifact storage service."""

import base64
import hashlib
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

from janus_gateway.config import get_settings
from janus_gateway.models import Artifact, ArtifactType

DATA_URL_MAX_BYTES = 1_000_000


def build_data_url(data: bytes, mime_type: str, max_bytes: int = DATA_URL_MAX_BYTES) -> Optional[str]:
    """Return a base64 data URL for small artifacts."""
    if len(data) > max_bytes:
        return None
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


class ArtifactStore:
    """Local artifact storage service."""

    def __init__(self, storage_path: str, ttl_seconds: int = 3600) -> None:
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = ttl_seconds
        self._artifacts: dict[str, Artifact] = {}

    def store(
        self,
        data: bytes,
        mime_type: str,
        display_name: str,
        artifact_type: ArtifactType = ArtifactType.FILE,
        gateway_base_url: str = "http://localhost:8000",
    ) -> Artifact:
        """Store artifact data and return descriptor."""
        artifact_id = f"artf_{uuid.uuid4().hex[:12]}"
        sha256_hash = hashlib.sha256(data).hexdigest()

        # Write to disk
        file_path = self._storage_path / artifact_id
        file_path.write_bytes(data)

        # Create descriptor
        artifact = Artifact(
            id=artifact_id,
            type=artifact_type,
            mime_type=mime_type,
            display_name=display_name,
            size_bytes=len(data),
            sha256=sha256_hash,
            created_at=datetime.now(),
            ttl_seconds=self._ttl_seconds,
            url=f"{gateway_base_url}/v1/artifacts/{artifact_id}",
        )

        self._artifacts[artifact_id] = artifact
        return artifact

    def get(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact metadata by ID."""
        artifact = self._artifacts.get(artifact_id)
        if artifact:
            # Check TTL
            age = (datetime.now() - artifact.created_at).total_seconds()
            if age > artifact.ttl_seconds:
                self.delete(artifact_id)
                return None
        return artifact

    def get_data(self, artifact_id: str) -> Optional[bytes]:
        """Get artifact data by ID."""
        artifact = self.get(artifact_id)
        if artifact:
            file_path = self._storage_path / artifact_id
            if file_path.exists():
                return file_path.read_bytes()
        return None

    def delete(self, artifact_id: str) -> bool:
        """Delete an artifact."""
        if artifact_id in self._artifacts:
            del self._artifacts[artifact_id]
            file_path = self._storage_path / artifact_id
            if file_path.exists():
                file_path.unlink()
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired artifacts. Returns count of removed artifacts."""
        now = datetime.now()
        expired = []
        for artifact_id, artifact in self._artifacts.items():
            age = (now - artifact.created_at).total_seconds()
            if age > artifact.ttl_seconds:
                expired.append(artifact_id)

        for artifact_id in expired:
            self.delete(artifact_id)

        return len(expired)


@lru_cache
def get_artifact_store() -> ArtifactStore:
    """Get cached artifact store instance."""
    settings = get_settings()
    return ArtifactStore(
        storage_path=settings.artifact_storage_path,
        ttl_seconds=settings.artifact_ttl_seconds,
    )
