"""SQLAlchemy database schemas."""

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from sqlalchemy import String, DateTime, LargeBinary, ARRAY, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from browser_session_service.database import Base


class BrowserSession(Base):
    """Browser session storage model."""

    __tablename__ = "browser_sessions"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # User from Chutes IDP JWT sub claim
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # User-provided session name
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional description
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Domains covered by this session (stored as comma-separated for SQLite compatibility)
    domains: Mapped[str] = mapped_column(String(1000), nullable=False, default="")

    # Encrypted storage state (AES-256-GCM ciphertext)
    storage_state_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # Initialization vector for AES-256-GCM
    iv: Mapped[bytes] = mapped_column(LargeBinary(12), nullable=False)

    # Optional expiration timestamp
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Unique constraint on user_id + name
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_session_name"),
        Index("idx_browser_sessions_user_id", "user_id"),
    )

    def get_domains_list(self) -> List[str]:
        """Get domains as a list."""
        if not self.domains:
            return []
        return [d.strip() for d in self.domains.split(",") if d.strip()]

    def set_domains_list(self, domains: List[str]) -> None:
        """Set domains from a list."""
        self.domains = ",".join(domains)
