import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from scoring_service.settings import get_settings


class Base(DeclarativeBase):
    pass


JSONType = JSON().with_variant(JSONB, "postgresql")


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    name: Mapped[str] = mapped_column(String(200))
    team: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    container_image: Mapped[str] = mapped_column(Text)
    github_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    best_composite_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    best_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scoring_runs.id", use_alter=True, name="competitors_best_run_id_fkey"),
        nullable=True,
    )

    verified: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_baseline: Mapped[bool] = mapped_column(Boolean, server_default="false")

    runs: Mapped[list["ScoringRun"]] = relationship(
        back_populates="competitor",
        foreign_keys="ScoringRun.competitor_id",
    )


class ScoringRun(Base):
    __tablename__ = "scoring_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    target_type: Mapped[str] = mapped_column(String(50))
    target_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    container_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    competitor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("competitors.id"), nullable=True
    )

    suite: Mapped[str] = mapped_column(String(50), server_default="quick")
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subset_percent: Mapped[int] = mapped_column(Integer, server_default="100")

    status: Mapped[str] = mapped_column(String(50), server_default="pending")
    progress_current: Mapped[int] = mapped_column(Integer, server_default="0")
    progress_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    composite_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    speed_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    cost_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    streaming_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    multimodal_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONType, nullable=True)

    results: Mapped[list["TaskResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    competitor: Mapped[Optional[Competitor]] = relationship(
        back_populates="runs",
        foreign_keys=[competitor_id],
    )


class TaskResult(Base):
    __tablename__ = "task_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scoring_runs.id", ondelete="CASCADE"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task_id: Mapped[str] = mapped_column(String(100))
    benchmark: Mapped[str] = mapped_column(String(50))
    task_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    success: Mapped[bool] = mapped_column(Boolean)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    quality_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)

    latency_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    ttft_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    avg_tps: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)

    continuity_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    max_gap_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)

    streaming_metrics: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONType, nullable=True)

    run: Mapped[ScoringRun] = relationship(back_populates="results")


Index("idx_scoring_runs_status", ScoringRun.status)
Index("idx_scoring_runs_created_at", ScoringRun.created_at.desc())
Index("idx_scoring_runs_competitor_id", ScoringRun.competitor_id)
Index("idx_task_results_run_id", TaskResult.run_id)
Index("idx_task_results_benchmark", TaskResult.benchmark)
Index("idx_competitors_best_score", Competitor.best_composite_score.desc())


settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
