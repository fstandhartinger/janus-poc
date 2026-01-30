"""JWT authentication with Chutes IDP."""

import logging
from typing import Optional

import httpx
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from browser_session_service.config import get_settings

logger = logging.getLogger("browser_session_service.auth")
settings = get_settings()

# Cache for JWKS
_jwks_cache: Optional[dict] = None


async def fetch_jwks() -> dict:
    """
    Fetch JSON Web Key Set from Chutes IDP.

    Returns cached JWKS if available.
    """
    global _jwks_cache

    if _jwks_cache is not None:
        return _jwks_cache

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.chutes_idp_jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch JWKS from {settings.chutes_idp_jwks_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to validate authentication token",
        )


def clear_jwks_cache() -> None:
    """Clear the JWKS cache (for testing or key rotation)."""
    global _jwks_cache
    _jwks_cache = None


async def validate_token(token: str) -> dict:
    """
    Validate a JWT token against Chutes IDP.

    Args:
        token: JWT access token

    Returns:
        Decoded token claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Fetch JWKS
        jwks = await fetch_jwks()
        keys = jwks.get("keys", [])

        # Find matching key
        key = None
        for k in keys:
            if k.get("kid") == kid:
                key = k
                break

        if key is None:
            # Try refreshing JWKS in case keys were rotated
            clear_jwks_cache()
            jwks = await fetch_jwks()
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break

        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key for token validation",
            )

        # Decode and validate token
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256", "ES256"],
            audience=settings.chutes_idp_audience,
            issuer=settings.chutes_idp_issuer,
            options={"verify_aud": bool(settings.chutes_idp_audience)},
        )

        return payload

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {e}",
        )


def extract_bearer_token(request: Request) -> str:
    """
    Extract Bearer token from Authorization header.

    Args:
        request: FastAPI request object

    Returns:
        JWT token string

    Raises:
        HTTPException: If Authorization header is missing or malformed
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
        )

    return parts[1]


async def get_current_user_id(request: Request) -> str:
    """
    Get the current user ID from the JWT token.

    This is the main dependency for authenticated endpoints.

    Args:
        request: FastAPI request object

    Returns:
        User ID from JWT 'sub' claim

    Raises:
        HTTPException: If authentication fails
    """
    token = extract_bearer_token(request)
    payload = await validate_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    return user_id
