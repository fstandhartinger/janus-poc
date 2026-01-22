"""Data models for benchmark tasks and results."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Benchmark task types."""

    CHAT_QUALITY = "chat_quality"
    RESEARCH = "research"
    CODING = "coding"
    STREAMING = "streaming"
    MULTIMODAL = "multimodal"


class Suite(str, Enum):
    """Benchmark suites."""

    PUBLIC_TRAIN = "public/train"
    PUBLIC_DEV = "public/dev"
    PRIVATE_TEST = "private/test"


class BenchmarkTask(BaseModel):
    """A single benchmark task."""

    id: str
    suite: Suite
    type: TaskType
    prompt: str
    expected_answer: Optional[str] = None
    expected_keywords: Optional[list[str]] = None
    image_url: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class StreamingMetrics(BaseModel):
    """Metrics for streaming evaluation."""

    ttft_seconds: float = Field(description="Time to first token in seconds")
    max_gap_seconds: float = Field(description="Maximum gap between SSE events")
    total_chunks: int = Field(description="Total number of SSE chunks received")
    keep_alive_count: int = Field(description="Number of keep-alive pings received")
    total_duration_seconds: float = Field(description="Total stream duration")


class TaskResult(BaseModel):
    """Result from running a single benchmark task."""

    task_id: str
    task_type: TaskType
    success: bool
    response_text: Optional[str] = None
    error: Optional[str] = None

    # Timing metrics
    latency_seconds: float = Field(description="Total request latency")
    streaming_metrics: Optional[StreamingMetrics] = None

    # Usage metrics (from response)
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    sandbox_seconds: Optional[float] = None

    # Scoring
    quality_score: float = Field(default=0.0, ge=0, le=1)
    speed_score: float = Field(default=0.0, ge=0, le=1)
    cost_score: float = Field(default=0.0, ge=0, le=1)
    streaming_score: float = Field(default=0.0, ge=0, le=1)
    multimodal_score: float = Field(default=0.0, ge=0, le=1)

    timestamp: datetime = Field(default_factory=datetime.now)


class BenchmarkReport(BaseModel):
    """Full benchmark report with all results."""

    run_id: str
    suite: str
    target_url: str
    model: str
    started_at: datetime
    completed_at: datetime

    # Aggregate scores (0-100)
    composite_score: float = Field(ge=0, le=100)
    quality_score: float = Field(ge=0, le=100)
    speed_score: float = Field(ge=0, le=100)
    cost_score: float = Field(ge=0, le=100)
    streaming_score: float = Field(ge=0, le=100)
    multimodal_score: float = Field(ge=0, le=100)

    # Aggregate metrics
    total_tasks: int
    passed_tasks: int
    failed_tasks: int
    avg_latency_seconds: float
    p50_latency_seconds: float
    avg_ttft_seconds: Optional[float] = None
    max_gap_seconds: Optional[float] = None
    total_tokens: int
    total_cost_usd: float

    # Individual results
    results: list[TaskResult]

    # Weights used
    weights: dict[str, int]
