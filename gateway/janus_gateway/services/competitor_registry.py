"""Competitor registry service."""

from functools import lru_cache
from typing import Optional

from janus_gateway.config import get_settings
from janus_gateway.models import CompetitorInfo


class CompetitorRegistry:
    """Registry of available competitors."""

    def __init__(
        self,
        baseline_url: Optional[str] = None,
        baseline_langchain_url: Optional[str] = None,
    ) -> None:
        self._competitors: dict[str, CompetitorInfo] = {}
        self._default_id: Optional[str] = None
        self._baseline_url = baseline_url
        self._baseline_langchain_url = baseline_langchain_url
        self._initialize_default_competitors()

    def _initialize_default_competitors(self) -> None:
        """Initialize with the baseline competitor."""
        baseline_url = self._normalize_url(self._baseline_url) if self._baseline_url else None
        baseline = CompetitorInfo(
            id="baseline-cli-agent",
            name="Baseline CLI Agent",
            description="Reference agent-based baseline competitor",
            url=baseline_url or "http://localhost:8081",
            enabled=True,
            is_baseline=True,
        )
        self.register(baseline, is_default=True)

        langchain_url = (
            self._normalize_url(self._baseline_langchain_url)
            if self._baseline_langchain_url
            else None
        )
        if langchain_url:
            langchain = CompetitorInfo(
                id="baseline-langchain",
                name="Janus Baseline LangChain",
                description="LangChain-based baseline competitor",
                url=langchain_url,
                enabled=True,
                is_baseline=True,
            )
            self.register(langchain)

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize a URL by ensuring it has a scheme.

        Rules:
        - If URL already has a scheme, return as-is (after stripping trailing slash)
        - localhost and 127.0.0.1 get http://
        - Private IP ranges (10.x, 172.16-31.x, 192.168.x) get http://
        - URLs with ports (host:port) get http://
        - Everything else gets https://
        """
        trimmed = url.rstrip("/")
        if "://" in trimmed:
            return trimmed

        # Extract host part (before any port)
        host = trimmed.split(":")[0] if ":" in trimmed else trimmed

        # Local addresses get http://
        if host in ("localhost", "127.0.0.1"):
            return f"http://{trimmed}"

        # Check for private IP ranges
        if host.startswith(("10.", "192.168.")):
            return f"http://{trimmed}"
        if host.startswith("172."):
            parts = host.split(".")
            if len(parts) >= 2:
                try:
                    second_octet = int(parts[1])
                    if 16 <= second_octet <= 31:
                        return f"http://{trimmed}"
                except ValueError:
                    pass

        # URLs with ports typically indicate development/internal services
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
    return CompetitorRegistry(
        baseline_url=settings.baseline_url,
        baseline_langchain_url=settings.baseline_langchain_url,
    )
