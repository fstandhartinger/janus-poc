"""API routers for Janus Gateway."""

from .health import router as health_router
from .chat import router as chat_router
from .models import router as models_router
from .artifacts import router as artifacts_router
from .transcription import router as transcription_router
from .research import router as research_router
from .tts import router as tts_router
from .memories import router as memories_router
from .sessions import router as sessions_router
from .debug import router as debug_router
from .logs import router as logs_router
from .arena import router as arena_router

__all__ = [
    "health_router",
    "chat_router",
    "models_router",
    "artifacts_router",
    "transcription_router",
    "research_router",
    "tts_router",
    "memories_router",
    "sessions_router",
    "debug_router",
    "logs_router",
    "arena_router",
]
