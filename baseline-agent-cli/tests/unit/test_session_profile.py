"""Unit tests for browser session profile conversion."""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

# Add agent-pack lib to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent-pack" / "lib"))

from session_profile import (
    create_browser_profile,
    create_cookies_database,
    create_local_storage,
    create_preferences_file,
    extract_domains_from_storage_state,
    _unix_to_chrome_timestamp,
    _samesite_to_int,
)


class TestTimestampConversion:
    """Test Chrome timestamp conversion."""

    def test_unix_to_chrome_timestamp(self):
        """Unix timestamp converts to Chrome timestamp."""
        # Unix timestamp for 2024-01-01 00:00:00 UTC
        unix_ts = 1704067200
        chrome_ts = _unix_to_chrome_timestamp(unix_ts)

        # Chrome timestamp should be larger (includes epoch offset)
        assert chrome_ts > unix_ts
        # Verify the offset is applied (approximately)
        assert chrome_ts > 13300000000000000  # Some time after Windows epoch

    def test_unix_to_chrome_timestamp_none(self):
        """None timestamp returns 0."""
        assert _unix_to_chrome_timestamp(None) == 0

    def test_unix_to_chrome_timestamp_negative_one(self):
        """Session cookie (-1) returns 0."""
        assert _unix_to_chrome_timestamp(-1) == 0


class TestSameSiteConversion:
    """Test SameSite attribute conversion."""

    def test_samesite_strict(self):
        """Strict converts to 2."""
        assert _samesite_to_int("Strict") == 2
        assert _samesite_to_int("strict") == 2

    def test_samesite_lax(self):
        """Lax converts to 1."""
        assert _samesite_to_int("Lax") == 1
        assert _samesite_to_int("lax") == 1

    def test_samesite_none(self):
        """None converts to 0."""
        assert _samesite_to_int("None") == 0
        assert _samesite_to_int("none") == 0

    def test_samesite_unspecified(self):
        """None/unspecified returns -1."""
        assert _samesite_to_int(None) == -1
        assert _samesite_to_int("") == -1


class TestCookiesDatabase:
    """Test cookies database creation."""

    def test_create_empty_cookies_database(self):
        """Empty cookies list creates valid database with schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "Default", "Cookies")
            create_cookies_database(db_path, [])

            # Verify database exists
            assert os.path.exists(db_path)

            # Verify schema
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            assert "cookies" in tables
            assert "meta" in tables
            conn.close()

    def test_create_cookies_database_with_cookies(self):
        """Cookies are inserted into database correctly."""
        cookies = [
            {
                "name": "session_id",
                "value": "abc123",
                "domain": ".example.com",
                "path": "/",
                "expires": 1735689600,  # 2025-01-01
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
            {
                "name": "tracking",
                "value": "xyz789",
                "domain": "example.com",
                "path": "/app",
                "expires": -1,  # Session cookie
                "httpOnly": False,
                "secure": False,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "Default", "Cookies")
            create_cookies_database(db_path, cookies)

            # Query cookies
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, value, host_key, path, is_secure, is_httponly FROM cookies ORDER BY name")
            rows = cursor.fetchall()
            conn.close()

            assert len(rows) == 2

            # Check session_id cookie
            session_cookie = [r for r in rows if r[0] == "session_id"][0]
            assert session_cookie[1] == "abc123"
            assert session_cookie[2] == ".example.com"  # Already has dot
            assert session_cookie[3] == "/"
            assert session_cookie[4] == 1  # is_secure
            assert session_cookie[5] == 1  # is_httponly

            # Check tracking cookie (domain gets dot prefix)
            tracking_cookie = [r for r in rows if r[0] == "tracking"][0]
            assert tracking_cookie[1] == "xyz789"
            assert tracking_cookie[2] == ".example.com"  # Gets dot prefix
            assert tracking_cookie[3] == "/app"
            assert tracking_cookie[4] == 0  # is_secure
            assert tracking_cookie[5] == 0  # is_httponly


class TestLocalStorage:
    """Test localStorage creation."""

    def test_create_empty_local_storage(self):
        """Empty origins list creates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ls_path = os.path.join(tmpdir, "Default", "Local Storage", "leveldb")
            create_local_storage(ls_path, [])

            # Directory should exist
            assert os.path.isdir(ls_path)

    def test_create_local_storage_with_origins(self):
        """Origins create JSON files with localStorage data."""
        origins = [
            {
                "origin": "https://example.com",
                "localStorage": [
                    {"name": "user_id", "value": "12345"},
                    {"name": "theme", "value": "dark"},
                ],
            },
            {
                "origin": "https://api.example.com:8080",
                "localStorage": [
                    {"name": "api_token", "value": "secret"},
                ],
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            ls_path = os.path.join(tmpdir, "Default", "Local Storage", "leveldb")
            create_local_storage(ls_path, origins)

            # Check files exist
            files = os.listdir(ls_path)
            assert len(files) == 2

            # Check content of first origin
            with open(os.path.join(ls_path, "https_example.com.json")) as f:
                data = json.load(f)
            assert data["user_id"] == "12345"
            assert data["theme"] == "dark"


class TestPreferencesFile:
    """Test preferences file creation."""

    def test_create_preferences_file(self):
        """Creates valid JSON preferences file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_path = os.path.join(tmpdir, "Default", "Preferences")
            create_preferences_file(prefs_path)

            # Verify file exists
            assert os.path.exists(prefs_path)

            # Verify valid JSON
            with open(prefs_path) as f:
                prefs = json.load(f)

            assert "profile" in prefs
            assert prefs["profile"]["name"] == "Janus Session Profile"

    def test_create_preferences_file_with_domains(self):
        """Includes domain information in preferences."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_path = os.path.join(tmpdir, "Default", "Preferences")
            create_preferences_file(prefs_path, domains=["twitter.com", "x.com"])

            with open(prefs_path) as f:
                prefs = json.load(f)

            assert "janus_session" in prefs
            assert prefs["janus_session"]["domains"] == ["twitter.com", "x.com"]
            assert prefs["janus_session"]["injected"] is True


class TestExtractDomains:
    """Test domain extraction from storage state."""

    def test_extract_domains_from_cookies(self):
        """Extracts domains from cookies."""
        storage_state = {
            "cookies": [
                {"domain": ".twitter.com"},
                {"domain": "x.com"},
                {"domain": ".twitter.com"},  # Duplicate
            ],
            "origins": [],
        }

        domains = extract_domains_from_storage_state(storage_state)

        assert "twitter.com" in domains
        assert "x.com" in domains
        assert len(domains) == 2  # Deduplicated

    def test_extract_domains_from_origins(self):
        """Extracts domains from origins."""
        storage_state = {
            "cookies": [],
            "origins": [
                {"origin": "https://github.com"},
                {"origin": "https://api.github.com:443"},
            ],
        }

        domains = extract_domains_from_storage_state(storage_state)

        assert "github.com" in domains
        assert "api.github.com:443" in domains

    def test_extract_domains_combined(self):
        """Extracts and combines domains from both sources."""
        storage_state = {
            "cookies": [
                {"domain": ".example.com"},
            ],
            "origins": [
                {"origin": "https://example.com"},
                {"origin": "https://api.example.com"},
            ],
        }

        domains = extract_domains_from_storage_state(storage_state)

        assert "example.com" in domains
        assert "api.example.com" in domains


class TestCreateBrowserProfile:
    """Test full browser profile creation."""

    def test_create_browser_profile(self):
        """Creates complete browser profile structure."""
        storage_state = {
            "cookies": [
                {
                    "name": "session",
                    "value": "test123",
                    "domain": ".example.com",
                    "path": "/",
                    "expires": 1735689600,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                },
            ],
            "origins": [
                {
                    "origin": "https://example.com",
                    "localStorage": [
                        {"name": "token", "value": "abc"},
                    ],
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = os.path.join(tmpdir, "profile")
            create_browser_profile(storage_state, profile_path, domains=["example.com"])

            # Check structure
            default_path = os.path.join(profile_path, "Default")
            assert os.path.isdir(default_path)

            # Check cookies database
            cookies_path = os.path.join(default_path, "Cookies")
            assert os.path.exists(cookies_path)

            conn = sqlite3.connect(cookies_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cookies")
            count = cursor.fetchone()[0]
            conn.close()
            assert count == 1

            # Check localStorage
            ls_path = os.path.join(default_path, "Local Storage", "leveldb")
            assert os.path.isdir(ls_path)

            # Check preferences
            prefs_path = os.path.join(default_path, "Preferences")
            assert os.path.exists(prefs_path)

            # Check storage_state.json backup
            state_path = os.path.join(profile_path, "storage_state.json")
            assert os.path.exists(state_path)

            with open(state_path) as f:
                saved_state = json.load(f)
            assert saved_state == storage_state

    def test_create_browser_profile_empty_state(self):
        """Creates profile even with empty storage state."""
        storage_state = {
            "cookies": [],
            "origins": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = os.path.join(tmpdir, "profile")
            create_browser_profile(storage_state, profile_path)

            # Structure should still be created
            assert os.path.isdir(os.path.join(profile_path, "Default"))
            assert os.path.exists(os.path.join(profile_path, "Default", "Preferences"))
