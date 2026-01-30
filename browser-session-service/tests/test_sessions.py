"""Tests for session CRUD API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthCheck:
    """Tests for health check endpoint."""

    async def test_health_check(self, client: AsyncClient):
        """Health check should return OK status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "janus-browser-session"


@pytest.mark.asyncio
class TestCreateSession:
    """Tests for session creation."""

    async def test_create_session_success(self, client: AsyncClient, sample_storage_state: dict):
        """Should create a new session with valid data."""
        response = await client.post(
            "/sessions",
            json={
                "name": "MyTwitter",
                "description": "Personal Twitter account",
                "domains": ["twitter.com", "x.com"],
                "storage_state": sample_storage_state,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "MyTwitter"
        assert data["description"] == "Personal Twitter account"
        assert set(data["domains"]) == {"twitter.com", "x.com"}
        assert "id" in data
        assert "created_at" in data

    async def test_create_session_minimal(self, client: AsyncClient):
        """Should create session with minimal required fields."""
        response = await client.post(
            "/sessions",
            json={
                "name": "test-session",
                "domains": ["example.com"],
                "storage_state": {"cookies": [], "origins": []},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-session"
        assert data["description"] is None

    async def test_create_session_duplicate_name_fails(
        self, client: AsyncClient, sample_storage_state: dict
    ):
        """Should reject duplicate session names for same user."""
        # Create first session
        response1 = await client.post(
            "/sessions",
            json={
                "name": "duplicate-test",
                "domains": ["example.com"],
                "storage_state": sample_storage_state,
            },
        )
        assert response1.status_code == 201

        # Try to create with same name
        response2 = await client.post(
            "/sessions",
            json={
                "name": "duplicate-test",
                "domains": ["other.com"],
                "storage_state": sample_storage_state,
            },
        )
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    async def test_create_session_invalid_name(self, client: AsyncClient):
        """Should reject invalid session names."""
        # Name starting with dash
        response = await client.post(
            "/sessions",
            json={
                "name": "-invalid",
                "domains": ["example.com"],
                "storage_state": {"cookies": [], "origins": []},
            },
        )
        assert response.status_code == 422

        # Name with spaces
        response = await client.post(
            "/sessions",
            json={
                "name": "invalid name",
                "domains": ["example.com"],
                "storage_state": {"cookies": [], "origins": []},
            },
        )
        assert response.status_code == 422

    async def test_create_session_invalid_domain(self, client: AsyncClient):
        """Should reject invalid domain formats."""
        response = await client.post(
            "/sessions",
            json={
                "name": "test",
                "domains": ["not a valid domain!!"],
                "storage_state": {"cookies": [], "origins": []},
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestListSessions:
    """Tests for listing sessions."""

    async def test_list_empty(self, client: AsyncClient):
        """Should return empty list when no sessions exist."""
        response = await client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    async def test_list_sessions(self, client: AsyncClient, sample_storage_state: dict):
        """Should return list of user's sessions."""
        # Create some sessions
        for i in range(3):
            await client.post(
                "/sessions",
                json={
                    "name": f"session-{i}",
                    "domains": ["example.com"],
                    "storage_state": sample_storage_state,
                },
            )

        response = await client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 3

        # Should NOT include storage_state
        for session in data["sessions"]:
            assert "storage_state" not in session
            assert "storage_state_encrypted" not in session


@pytest.mark.asyncio
class TestGetSession:
    """Tests for getting session details."""

    async def test_get_session_by_id(self, client: AsyncClient, sample_storage_state: dict):
        """Should get session details by ID."""
        # Create session
        create_resp = await client.post(
            "/sessions",
            json={
                "name": "get-test",
                "description": "Test session",
                "domains": ["example.com"],
                "storage_state": sample_storage_state,
            },
        )
        session_id = create_resp.json()["id"]

        # Get session
        response = await client.get(f"/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["name"] == "get-test"
        assert "storage_state" not in data

    async def test_get_session_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent session."""
        response = await client.get("/sessions/non-existent-id")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestGetSessionState:
    """Tests for getting decrypted session state."""

    async def test_get_session_state(self, client: AsyncClient, sample_storage_state: dict):
        """Should return decrypted storage state."""
        # Create session
        create_resp = await client.post(
            "/sessions",
            json={
                "name": "state-test",
                "domains": ["example.com"],
                "storage_state": sample_storage_state,
            },
        )
        session_id = create_resp.json()["id"]

        # Get state
        response = await client.get(f"/sessions/{session_id}/state")
        assert response.status_code == 200
        data = response.json()

        # Verify storage state matches
        assert "storage_state" in data
        state = data["storage_state"]
        assert len(state["cookies"]) == len(sample_storage_state["cookies"])
        assert len(state["origins"]) == len(sample_storage_state["origins"])

    async def test_get_expired_session_state(self, client: AsyncClient, sample_storage_state: dict):
        """Should return 410 for expired sessions."""
        # Create expired session
        create_resp = await client.post(
            "/sessions",
            json={
                "name": "expired-test",
                "domains": ["example.com"],
                "storage_state": sample_storage_state,
                "expires_at": "2020-01-01T00:00:00Z",  # Past date
            },
        )
        session_id = create_resp.json()["id"]

        # Try to get state
        response = await client.get(f"/sessions/{session_id}/state")
        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestUpdateSession:
    """Tests for updating sessions."""

    async def test_update_session_name(self, client: AsyncClient, sample_storage_state: dict):
        """Should update session name."""
        # Create session
        create_resp = await client.post(
            "/sessions",
            json={
                "name": "original-name",
                "domains": ["example.com"],
                "storage_state": sample_storage_state,
            },
        )
        session_id = create_resp.json()["id"]

        # Update name
        response = await client.put(
            f"/sessions/{session_id}",
            json={"name": "new-name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "new-name"

    async def test_update_session_storage_state(
        self, client: AsyncClient, sample_storage_state: dict
    ):
        """Should update storage state."""
        # Create session
        create_resp = await client.post(
            "/sessions",
            json={
                "name": "update-state-test",
                "domains": ["example.com"],
                "storage_state": sample_storage_state,
            },
        )
        session_id = create_resp.json()["id"]

        # Update with new storage state
        new_state = {"cookies": [{"name": "new", "value": "cookie"}], "origins": []}
        response = await client.put(
            f"/sessions/{session_id}",
            json={"storage_state": new_state},
        )
        assert response.status_code == 200

        # Verify new state
        state_resp = await client.get(f"/sessions/{session_id}/state")
        assert len(state_resp.json()["storage_state"]["cookies"]) == 1


@pytest.mark.asyncio
class TestDeleteSession:
    """Tests for deleting sessions."""

    async def test_delete_session(self, client: AsyncClient, sample_storage_state: dict):
        """Should delete session."""
        # Create session
        create_resp = await client.post(
            "/sessions",
            json={
                "name": "delete-test",
                "domains": ["example.com"],
                "storage_state": sample_storage_state,
            },
        )
        session_id = create_resp.json()["id"]

        # Delete session
        response = await client.delete(f"/sessions/{session_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify deleted
        get_resp = await client.get(f"/sessions/{session_id}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent_session(self, client: AsyncClient):
        """Should return 404 when deleting non-existent session."""
        response = await client.delete("/sessions/non-existent-id")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestGetSessionByName:
    """Tests for getting session by name."""

    async def test_get_by_name_success(self, client: AsyncClient, sample_storage_state: dict):
        """Should get session by name."""
        # Create session
        await client.post(
            "/sessions",
            json={
                "name": "MyGitHub",
                "domains": ["github.com"],
                "storage_state": sample_storage_state,
            },
        )

        # Get by name
        response = await client.get("/sessions/by-name/MyGitHub")
        assert response.status_code == 200
        assert response.json()["name"] == "MyGitHub"

    async def test_get_by_name_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent name."""
        response = await client.get("/sessions/by-name/NonExistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
