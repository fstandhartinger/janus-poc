"""Arena mode request/response models."""

from typing import Literal, Optional

from pydantic import BaseModel


ArenaWinner = Literal["A", "B", "tie", "both_bad"]


class ArenaResponseMessage(BaseModel):
    """Simplified response payload for arena comparisons."""

    content: str


class ArenaCompletionResponse(BaseModel):
    """Arena chat completion response containing paired results."""

    prompt_id: str
    response_a: ArenaResponseMessage
    response_b: ArenaResponseMessage


class ArenaVoteRequest(BaseModel):
    """Vote submission payload."""

    prompt_id: str
    winner: ArenaWinner
    user_id: Optional[str] = None
    session_created_at: Optional[int] = None


class ArenaVoteResponse(BaseModel):
    """Vote submission response."""

    status: str
    model_a: str
    model_b: str
