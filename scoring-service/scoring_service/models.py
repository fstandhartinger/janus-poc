from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


RunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
SuiteName = Literal[
    "quick",
    "full",
    "research",
    "tool_use",
    "multimodal",
    "streaming",
    "cost",
]
TargetType = Literal["url", "container", "competitor_id"]


class CreateRunRequest(BaseModel):
    target_type: TargetType
    target_url: Optional[str] = None
    container_image: Optional[str] = None
    competitor_id: Optional[UUID] = None
    suite: SuiteName = "quick"
    model: Optional[str] = None
    subset_percent: int = Field(default=100, ge=1, le=100)

    @model_validator(mode="after")
    def validate_target(self) -> "CreateRunRequest":
        if self.target_type == "url" and not self.target_url:
            raise ValueError("target_url is required for target_type=url")
        if self.target_type == "container" and not self.container_image:
            raise ValueError("container_image is required for target_type=container")
        if self.target_type == "competitor_id" and not self.competitor_id:
            raise ValueError("competitor_id is required for target_type=competitor_id")
        return self


class ScoringRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    target_type: str
    target_url: Optional[str]
    container_image: Optional[str]
    competitor_id: Optional[UUID]
    suite: str
    status: RunStatus
    progress_current: int
    progress_total: Optional[int]
    composite_score: Optional[float]
    quality_score: Optional[float]
    speed_score: Optional[float]
    cost_score: Optional[float]
    streaming_score: Optional[float]
    multimodal_score: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]


class TaskResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: str
    benchmark: str
    task_type: Optional[str]
    success: bool
    quality_score: Optional[float]
    latency_seconds: Optional[float]
    ttft_seconds: Optional[float]
    avg_tps: Optional[float]
    total_tokens: Optional[int]
    cost_usd: Optional[float]
    continuity_score: Optional[float]
    error: Optional[str]


class ScoringRunDetailResponse(ScoringRunResponse):
    results: list[TaskResultResponse]


class RunSummaryResponse(BaseModel):
    run_id: UUID
    composite_score: float
    scores: dict[str, float]
    by_benchmark: dict[str, dict]
    metrics: dict[str, float]


class CompetitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    team: Optional[str]
    container_image: str
    best_composite_score: Optional[float]
    verified: bool
    is_baseline: bool


class LeaderboardEntry(BaseModel):
    rank: int
    competitor: CompetitorResponse
    best_run_id: Optional[UUID]
    scores: dict[str, float]
