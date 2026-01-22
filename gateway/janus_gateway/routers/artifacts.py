"""Artifact retrieval endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from janus_gateway.services import ArtifactStore, get_artifact_store

router = APIRouter(prefix="/v1", tags=["artifacts"])


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    store: ArtifactStore = Depends(get_artifact_store),
) -> Response:
    """Retrieve an artifact by ID."""
    artifact = store.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    data = store.get_data(artifact_id)
    if not data:
        raise HTTPException(status_code=404, detail="Artifact data not found")

    return Response(
        content=data,
        media_type=artifact.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.display_name}"',
            "X-Artifact-Id": artifact.id,
            "X-Artifact-Size": str(artifact.size_bytes),
        },
    )
