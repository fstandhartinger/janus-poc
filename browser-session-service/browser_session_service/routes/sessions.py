"""Session CRUD API routes."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from browser_session_service.auth import get_current_user_id
from browser_session_service.config import get_settings
from browser_session_service.crypto import decrypt_storage_state, encrypt_storage_state, decode_secret
from browser_session_service.database import get_session
from browser_session_service.models import (
    DeleteResponse,
    SessionCreate,
    SessionCreateResponse,
    SessionListResponse,
    SessionStateResponse,
    SessionSummary,
    SessionUpdate,
    StorageState,
)
from browser_session_service.schemas import BrowserSession

logger = logging.getLogger("browser_session_service.routes.sessions")
router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_server_secret() -> bytes:
    """Get the server encryption secret."""
    settings = get_settings()
    if not settings.encryption_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Encryption secret not configured",
        )
    return decode_secret(settings.encryption_secret)


def session_to_summary(session: BrowserSession) -> SessionSummary:
    """Convert a database session to a summary response."""
    return SessionSummary(
        id=session.id,
        name=session.name,
        description=session.description,
        domains=session.get_domains_list(),
        expires_at=session.expires_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SessionCreateResponse:
    """
    Create a new browser session.

    The storage state (cookies + localStorage) is encrypted before storage.
    """
    # Validate storage state size
    settings = get_settings()
    storage_state_json = request.storage_state.model_dump_json()
    if len(storage_state_json.encode()) > settings.max_storage_state_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Storage state exceeds maximum size of {settings.max_storage_state_bytes} bytes",
        )

    # Encrypt storage state
    server_secret = get_server_secret()
    ciphertext, iv = encrypt_storage_state(storage_state_json, server_secret, user_id)

    # Create database record
    session = BrowserSession(
        id=str(uuid4()),
        user_id=user_id,
        name=request.name,
        description=request.description,
        storage_state_encrypted=ciphertext,
        iv=iv,
        expires_at=request.expires_at,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.set_domains_list(request.domains)

    try:
        db.add(session)
        await db.commit()
        await db.refresh(session)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session with name '{request.name}' already exists",
        )

    logger.info(f"Created session {session.id} for user {user_id}")

    return SessionCreateResponse(
        id=session.id,
        name=session.name,
        description=session.description,
        domains=session.get_domains_list(),
        expires_at=session.expires_at,
        created_at=session.created_at,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SessionListResponse:
    """
    List all sessions for the authenticated user.

    Does NOT return storage state - only metadata.
    """
    result = await db.execute(
        select(BrowserSession)
        .where(BrowserSession.user_id == user_id)
        .order_by(BrowserSession.created_at.desc())
    )
    sessions = result.scalars().all()

    return SessionListResponse(
        sessions=[session_to_summary(s) for s in sessions]
    )


@router.get("/{session_id}", response_model=SessionSummary)
async def get_session_info(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SessionSummary:
    """
    Get session details (without storage state).
    """
    result = await db.execute(
        select(BrowserSession)
        .where(BrowserSession.id == session_id)
        .where(BrowserSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return session_to_summary(session)


@router.get("/{session_id}/state", response_model=SessionStateResponse)
async def get_session_state(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SessionStateResponse:
    """
    Get the decrypted storage state for a session.

    This is used for session injection into sandboxes.
    """
    result = await db.execute(
        select(BrowserSession)
        .where(BrowserSession.id == session_id)
        .where(BrowserSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Check expiration
    if session.expires_at:
        # Handle both timezone-aware and naive datetimes from DB
        expires_at = session.expires_at
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            # Assume naive datetime is UTC
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Session has expired",
            )

    # Decrypt storage state
    server_secret = get_server_secret()
    try:
        storage_state_json = decrypt_storage_state(
            session.storage_state_encrypted,
            session.iv,
            server_secret,
            user_id,
        )
        storage_state = StorageState.model_validate_json(storage_state_json)
    except Exception as e:
        logger.error(f"Failed to decrypt session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt session data",
        )

    return SessionStateResponse(storage_state=storage_state)


@router.put("/{session_id}", response_model=SessionSummary)
async def update_session(
    session_id: str,
    request: SessionUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SessionSummary:
    """
    Update a session's metadata or storage state.
    """
    result = await db.execute(
        select(BrowserSession)
        .where(BrowserSession.id == session_id)
        .where(BrowserSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Update fields if provided
    if request.name is not None:
        session.name = request.name

    if request.description is not None:
        session.description = request.description

    if request.expires_at is not None:
        session.expires_at = request.expires_at

    if request.storage_state is not None:
        # Validate and encrypt new storage state
        settings = get_settings()
        storage_state_json = request.storage_state.model_dump_json()
        if len(storage_state_json.encode()) > settings.max_storage_state_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Storage state exceeds maximum size of {settings.max_storage_state_bytes} bytes",
            )

        server_secret = get_server_secret()
        ciphertext, iv = encrypt_storage_state(storage_state_json, server_secret, user_id)
        session.storage_state_encrypted = ciphertext
        session.iv = iv

    session.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        await db.refresh(session)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session with name '{request.name}' already exists",
        )

    logger.info(f"Updated session {session_id} for user {user_id}")

    return session_to_summary(session)


@router.delete("/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> DeleteResponse:
    """
    Delete a session.
    """
    result = await db.execute(
        select(BrowserSession)
        .where(BrowserSession.id == session_id)
        .where(BrowserSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    await db.delete(session)
    await db.commit()

    logger.info(f"Deleted session {session_id} for user {user_id}")

    return DeleteResponse(status="deleted")


@router.get("/by-name/{name}", response_model=SessionSummary)
async def get_session_by_name(
    name: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SessionSummary:
    """
    Get a session by name for the current user.

    This is convenient for agents that reference sessions by name.
    """
    result = await db.execute(
        select(BrowserSession)
        .where(BrowserSession.user_id == user_id)
        .where(BrowserSession.name == name)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with name '{name}' not found",
        )

    return session_to_summary(session)
