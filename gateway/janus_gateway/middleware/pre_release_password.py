"""Pre-release password middleware for Janus Gateway."""

from typing import Callable, Awaitable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


# Paths that must stay reachable without the pre-release password:
# /health is used by Render's health checks and the janus-keepwarm cron —
# blocking it lets free-tier containers spin down and users see cold-start
# errors.
EXEMPT_PATHS = {"/health"}


class PreReleasePasswordMiddleware(BaseHTTPMiddleware):
    """Require X-PreReleasePassword header for all API calls when configured."""

    def __init__(self, app: ASGIApp, password: str) -> None:
        super().__init__(app)
        self._password = password

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not self._password:
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-PreReleasePassword")
        if provided and provided == self._password:
            return await call_next(request)

        return JSONResponse(
            {"error": "PRE_RELEASE_PASSWORD_REQUIRED", "message": "Pre-release password required"},
            status_code=401,
        )
