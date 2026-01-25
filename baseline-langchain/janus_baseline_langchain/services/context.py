"""Request-scoped context helpers for auth tokens and artifacts."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from janus_baseline_langchain.models import Artifact


_request_auth_token: ContextVar[Optional[str]] = ContextVar("request_auth_token", default=None)
_artifact_collection: ContextVar[Optional[list[Artifact]]] = ContextVar(
    "artifact_collection", default=None
)


def set_request_auth_token(token: str | None) -> None:
    """Set the request-scoped auth token for downstream tool calls."""
    _request_auth_token.set(token)


def get_request_auth_token() -> str | None:
    """Get the request-scoped auth token, if any."""
    return _request_auth_token.get()


def start_artifact_collection() -> list[Artifact]:
    """Initialize artifact collection for the active request."""
    artifacts: list[Artifact] = []
    _artifact_collection.set(artifacts)
    return artifacts


def add_artifact(artifact: Artifact) -> None:
    """Add an artifact to the active request collection."""
    artifacts = _artifact_collection.get()
    if artifacts is not None:
        artifacts.append(artifact)


def get_collected_artifacts() -> list[Artifact]:
    """Get artifacts collected during the active request."""
    artifacts = _artifact_collection.get()
    return list(artifacts) if artifacts else []


def clear_artifact_collection() -> None:
    """Clear the artifact collection for the active request."""
    _artifact_collection.set(None)
