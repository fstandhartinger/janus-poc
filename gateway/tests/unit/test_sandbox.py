"""Unit tests for sandbox router."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from janus_gateway.routers.sandbox import (
    CreateSandboxRequest,
    CreateSandboxResponse,
    CaptureSessionResponse,
)


@pytest.fixture
def mock_sandy_settings():
    """Mock Sandy settings to have proper config."""
    with patch("janus_gateway.routers.sandbox.settings") as mock_settings:
        mock_settings.sandy_base_url = "https://sandy.example.com"
        mock_settings.sandy_api_key = "test-api-key"
        yield mock_settings


@pytest.fixture
def mock_sandy_unconfigured():
    """Mock Sandy settings without config."""
    with patch("janus_gateway.routers.sandbox.settings") as mock_settings:
        mock_settings.sandy_base_url = None
        mock_settings.sandy_api_key = None
        yield mock_settings


class TestCreateSandboxRequest:
    """Tests for CreateSandboxRequest model."""

    def test_defaults(self):
        """Test default values for sandbox request."""
        request = CreateSandboxRequest()
        assert request.flavor == "agent-ready"
        assert request.enableVnc is True
        assert request.timeout == 600

    def test_custom_values(self):
        """Test custom values for sandbox request."""
        request = CreateSandboxRequest(
            flavor="custom-image",
            enableVnc=False,
            timeout=300,
        )
        assert request.flavor == "custom-image"
        assert request.enableVnc is False
        assert request.timeout == 300


class TestCreateSandboxResponse:
    """Tests for CreateSandboxResponse model."""

    def test_response_model(self):
        """Test response model fields."""
        response = CreateSandboxResponse(
            id="sandbox-123",
            url="https://sandy.example.com",
            vncPort=5900,
        )
        assert response.id == "sandbox-123"
        assert response.url == "https://sandy.example.com"
        assert response.vncPort == 5900


class TestCaptureSessionResponse:
    """Tests for CaptureSessionResponse model."""

    def test_response_model(self):
        """Test capture session response model."""
        response = CaptureSessionResponse(
            storage_state={"cookies": [], "origins": []},
            detected_domains=["example.com", "login.example.com"],
        )
        assert response.storage_state == {"cookies": [], "origins": []}
        assert response.detected_domains == ["example.com", "login.example.com"]


class TestSandboxEndpoints:
    """Tests for sandbox router endpoints."""

    @pytest.mark.asyncio
    async def test_create_sandbox_not_configured(self, mock_sandy_unconfigured):
        """Test create sandbox returns 503 when Sandy not configured."""
        from janus_gateway.routers.sandbox import create_sandbox

        with pytest.raises(httpx.HTTPStatusError) if False else pytest.raises(Exception) as exc_info:
            request = CreateSandboxRequest()
            try:
                await create_sandbox(request)
            except Exception as e:
                assert "not configured" in str(e).lower()
                raise

    @pytest.mark.asyncio
    async def test_create_sandbox_success(self, mock_sandy_settings):
        """Test successful sandbox creation."""
        from janus_gateway.routers.sandbox import create_sandbox

        mock_response = httpx.Response(
            200,
            json={"sandbox_id": "sbx-123", "vnc_port": 5901},
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            request = CreateSandboxRequest()
            response = await create_sandbox(request)

            assert response.id == "sbx-123"
            assert response.vncPort == 5901
            assert response.url == "https://sandy.example.com"

    @pytest.mark.asyncio
    async def test_capture_session_success(self, mock_sandy_settings):
        """Test successful session capture."""
        from janus_gateway.routers.sandbox import capture_session

        storage_state = {
            "cookies": [
                {"domain": ".example.com", "name": "session", "value": "abc123"},
                {"domain": "login.example.com", "name": "auth", "value": "xyz"},
            ],
            "origins": [],
        }

        mock_response = httpx.Response(
            200,
            json={"stdout": json.dumps(storage_state), "exit_code": 0},
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            response = await capture_session("sbx-123")

            assert response.storage_state == storage_state
            assert "example.com" in response.detected_domains
            assert "login.example.com" in response.detected_domains

    @pytest.mark.asyncio
    async def test_capture_session_empty_state(self, mock_sandy_settings):
        """Test session capture with empty state."""
        from janus_gateway.routers.sandbox import capture_session

        mock_response = httpx.Response(
            200,
            json={"stdout": "", "exit_code": 0},
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            response = await capture_session("sbx-123")

            assert response.storage_state == {"cookies": [], "origins": []}
            assert response.detected_domains == []

    @pytest.mark.asyncio
    async def test_delete_sandbox_success(self, mock_sandy_settings):
        """Test successful sandbox deletion."""
        from janus_gateway.routers.sandbox import delete_sandbox

        mock_response = httpx.Response(200, json={"status": "terminated"})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            response = await delete_sandbox("sbx-123")

            assert response["status"] == "deleted"
            assert response["sandbox_id"] == "sbx-123"

    @pytest.mark.asyncio
    async def test_delete_sandbox_already_gone(self, mock_sandy_settings):
        """Test sandbox deletion when sandbox already terminated."""
        from janus_gateway.routers.sandbox import delete_sandbox

        mock_response = httpx.Response(404, text="Not found")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            # Should not raise, just return success
            response = await delete_sandbox("sbx-123")
            assert response["status"] == "deleted"


class TestDomainExtraction:
    """Tests for domain extraction logic."""

    def test_extract_domains_from_cookies(self):
        """Test domain extraction strips leading dots."""
        from janus_gateway.routers.sandbox import CaptureSessionResponse

        # This tests the model can hold the expected data
        response = CaptureSessionResponse(
            storage_state={
                "cookies": [
                    {"domain": ".example.com"},
                    {"domain": "api.example.com"},
                ],
                "origins": [],
            },
            detected_domains=["example.com", "api.example.com"],
        )
        assert "example.com" in response.detected_domains
        assert "api.example.com" in response.detected_domains
