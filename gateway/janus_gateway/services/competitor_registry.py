"""Competitor registry service."""

from functools import lru_cache
from typing import Optional

from janus_gateway.config import get_settings
from janus_gateway.models import CompetitorInfo


class CompetitorRegistry:
    """Registry of available competitors."""

    def __init__(self, baseline_url: Optional[str] = None) -> None:
        self._competitors: dict[str, CompetitorInfo] = {}
        self._default_id: Optional[str] = None
        self._baseline_url = baseline_url
        self._initialize_default_competitors()

    def _initialize_default_competitors(self) -> None:
        """Initialize with the baseline competitor."""
        baseline_url = self._normalize_url(self._baseline_url) if self._baseline_url else None
        baseline = CompetitorInfo(
            id="baseline",
            name="Janus Baseline",
            description="Reference implementation with CLI agent support",
            url=baseline_url or "http://localhost:8001",
            enabled=True,
            is_baseline=True,
        )
        self.register(baseline, is_default=True)

    @staticmethod
    def _normalize_url(url: str) -> str:
        trimmed = url.rstrip("/")
        if "://" in trimmed:
            return trimmed
        if trimmed.startswith("localhost") or trimmed.startswith("127.0.0.1"):
            return f"http://{trimmed}"
        if ":" in trimmed:
            return f"http://{trimmed}"
        return f"https://{trimmed}"

    def register(self, competitor: CompetitorInfo, is_default: bool = False) -> None:
        """Register a competitor."""
        self._competitors[competitor.id] = competitor
        if is_default or self._default_id is None:
            self._default_id = competitor.id

    def unregister(self, competitor_id: str) -> bool:
        """Unregister a competitor."""
        if competitor_id in self._competitors:
            del self._competitors[competitor_id]
            if self._default_id == competitor_id:
                self._default_id = next(iter(self._competitors), None)
            return True
        return False

    def get(self, competitor_id: str) -> Optional[CompetitorInfo]:
        """Get a competitor by ID."""
        return self._competitors.get(competitor_id)

    def get_default(self) -> Optional[CompetitorInfo]:
        """Get the default competitor."""
        if self._default_id:
            return self._competitors.get(self._default_id)
        return None

    def list_all(self, enabled_only: bool = True) -> list[CompetitorInfo]:
        """List all registered competitors."""
        competitors = list(self._competitors.values())
        if enabled_only:
            competitors = [c for c in competitors if c.enabled]
        return competitors

    def resolve(self, competitor_id: Optional[str] = None) -> Optional[CompetitorInfo]:
        """Resolve a competitor by ID, falling back to default."""
        if competitor_id:
            return self.get(competitor_id)
        return self.get_default()


@lru_cache
def get_competitor_registry() -> CompetitorRegistry:
    """Get cached competitor registry instance."""
    settings = get_settings()
    return CompetitorRegistry(baseline_url=settings.baseline_url)
