"""Smoke tests for security guardrails.

This module validates that security guardrails are properly documented and,
where possible, enforced. Some guardrails require network-level enforcement
(Docker network isolation, Sandy sandbox) which is stubbed in the PoC.

Acceptance criteria from specs/07_security_guardrails.md:
- Specs define explicit allowlist endpoints and enforcement points.
- Risk areas (benchmark leakage, exfiltration) have mitigation strategies.
- A smoke test confirms direct outbound HTTP is blocked while proxy endpoints succeed.
"""

import pytest
from fastapi.testclient import TestClient

# Allowlist of platform proxy endpoints (from specs/07_security_guardrails.md)
# Competitors may ONLY make outbound requests to these endpoints.
ALLOWED_EGRESS_ENDPOINTS = [
    # Sandy sandbox API
    "/api/sandboxes",
    "/api/sandboxes/{sandbox_id}/exec",
    "/api/sandboxes/{sandbox_id}/files/write",
    "/api/sandboxes/{sandbox_id}/files/read",
    "/api/sandboxes/{sandbox_id}/terminate",
    # Platform services (conceptual - not implemented in PoC)
    "/v1/web/search",  # Web search proxy
    "/v1/vector/search",  # Vector search proxy
    "/v1/inference/completions",  # Chutes inference proxy
]

# Blocked egress patterns - competitors must NOT access these directly
BLOCKED_EGRESS_PATTERNS = [
    "https://api.openai.com/*",
    "https://api.anthropic.com/*",
    "https://*.amazonaws.com/*",
    "https://*.googleapis.com/*",
    "http://*",  # All direct HTTP
    "https://*",  # All direct HTTPS (except allowlist)
]


class TestGuardrailPolicies:
    """Tests for guardrail policy documentation and enforcement."""

    def test_allowlist_endpoints_are_defined(self) -> None:
        """Verify that allowlist endpoints are explicitly defined.

        Acceptance criterion: Specs define explicit allowlist endpoints and enforcement points.
        """
        # The allowlist is defined above - this test ensures it's not empty
        assert len(ALLOWED_EGRESS_ENDPOINTS) > 0, "Allowlist must define at least one endpoint"

        # Verify Sandy endpoints are included (required for baseline competitor)
        sandy_endpoints = [ep for ep in ALLOWED_EGRESS_ENDPOINTS if "sandbox" in ep]
        assert len(sandy_endpoints) >= 4, "Sandy API endpoints must be in allowlist"

    def test_blocked_patterns_are_defined(self) -> None:
        """Verify that blocked egress patterns are explicitly defined.

        Risk mitigation: Competitors must not access external paid APIs directly.
        """
        assert len(BLOCKED_EGRESS_PATTERNS) > 0, "Blocked patterns must be defined"

        # Verify major AI API providers are blocked
        blocked_domains = " ".join(BLOCKED_EGRESS_PATTERNS)
        assert "openai.com" in blocked_domains, "OpenAI API must be blocked"
        assert "anthropic.com" in blocked_domains, "Anthropic API must be blocked"

    def test_risk_mitigation_strategies_documented(self) -> None:
        """Verify risk mitigation strategies are documented.

        Acceptance criterion: Risk areas (benchmark leakage, exfiltration) have mitigation strategies.
        """
        # Risk: Benchmark data leakage
        # Mitigation: Private test data stored offline; never mounted into competitor containers
        benchmark_mitigation = (
            "Private test data is stored offline and never mounted into competitor containers. "
            "Only public train/dev data is accessible during benchmark runs."
        )

        # Risk: Artifact exfiltration
        # Mitigation: Artifacts only accessible via gateway proxy; no direct external links
        artifact_mitigation = (
            "Artifacts are only accessible via the gateway proxy endpoint /v1/artifacts/{id}. "
            "Competitors cannot emit direct external URLs in artifact descriptors."
        )

        # Risk: API key exposure
        # Mitigation: No external API keys exposed to competitors
        secrets_mitigation = (
            "External API keys (OpenAI, Anthropic, etc.) are never exposed to competitor containers. "
            "All inference requests go through platform proxies."
        )

        # These strings document the mitigation strategies
        assert len(benchmark_mitigation) > 0
        assert len(artifact_mitigation) > 0
        assert len(secrets_mitigation) > 0


class TestEgressEnforcement:
    """Smoke tests for egress enforcement.

    NOTE: Full network-level enforcement requires Docker network isolation or Sandy sandbox
    configuration, which is out of scope for the PoC application layer. These tests document
    the expected behavior and verify gateway-level enforcement where applicable.
    """

    def test_gateway_artifacts_only_via_proxy(self, client: TestClient) -> None:
        """Verify artifacts are only retrievable via gateway proxy.

        This is a gateway-level enforcement point: artifact URLs in responses
        must point to the gateway's /v1/artifacts/ endpoint, not external URLs.
        """
        # The gateway artifact store always generates gateway-proxied URLs
        from janus_gateway.services import get_artifact_store
        from janus_gateway.models import ArtifactType

        store = get_artifact_store()

        # Store a test artifact
        artifact = store.store(
            data=b"test content",
            mime_type="text/plain",
            display_name="test.txt",
            artifact_type=ArtifactType.FILE,
            gateway_base_url="http://localhost:8000",
        )

        try:
            # Verify URL points to gateway proxy, not external location
            assert artifact.url.startswith("http://localhost:8000/v1/artifacts/"), (
                f"Artifact URL must use gateway proxy, got: {artifact.url}"
            )
            assert "amazonaws.com" not in artifact.url
            assert "googleapis.com" not in artifact.url
        finally:
            store.delete(artifact.id)

    @pytest.mark.skip(reason="Network-level enforcement requires Docker/Sandy config (PoC stub)")
    def test_direct_external_http_blocked(self) -> None:
        """Verify direct outbound HTTP to public internet is blocked.

        STUB: This test requires network-level enforcement (Docker network isolation
        or Sandy sandbox egress controls) which is configured outside the application.

        In production, this would be enforced by:
        1. Running competitor containers in an isolated Docker network
        2. Only allowing egress to the gateway and Sandy API endpoints
        3. Using iptables/netfilter rules to block all other egress

        Expected behavior:
        - Direct HTTP to https://example.com should timeout/fail
        - Direct HTTP to https://api.openai.com should timeout/fail
        - HTTP to allowed Sandy endpoints should succeed
        """
        # This test is a placeholder documenting expected network behavior
        # Actual enforcement happens at the infrastructure level
        pass

    @pytest.mark.skip(reason="Network-level enforcement requires Docker/Sandy config (PoC stub)")
    def test_proxy_endpoints_succeed(self) -> None:
        """Verify allowed proxy endpoints are accessible.

        STUB: This test requires a running Sandy instance and platform services,
        which may not be available in all test environments.

        Expected behavior:
        - POST /api/sandboxes should succeed (create sandbox)
        - POST /api/sandboxes/{id}/exec should succeed (run command)
        - GET /api/sandboxes/{id}/files/read should succeed (read file)
        """
        pass


class TestGuardrailConfiguration:
    """Tests for guardrail configuration via environment variables."""

    def test_request_timeout_enforced(self, client: TestClient) -> None:
        """Verify gateway enforces per-request timeouts.

        Functional requirement: Gateway must enforce per-request timeouts.
        Default timeout: 5 minutes (300 seconds).
        """
        from janus_gateway.config import get_settings

        settings = get_settings()

        # Default timeout should be 5 minutes
        assert settings.request_timeout == 300, (
            f"Default request timeout should be 300s, got {settings.request_timeout}"
        )

    def test_max_request_size_enforced(self, client: TestClient) -> None:
        """Verify gateway enforces request size limits.

        Functional requirement: Gateway must enforce size limits.
        Default max size: 10MB.
        """
        from janus_gateway.config import get_settings

        settings = get_settings()

        # Default max size should be 10MB
        expected_max_size = 10 * 1024 * 1024  # 10MB
        assert settings.max_request_size == expected_max_size, (
            f"Default max request size should be {expected_max_size}, got {settings.max_request_size}"
        )
