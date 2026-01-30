"""Browser session profile conversion utilities.

Converts Playwright storageState format to Chrome/Chromium user data directory format
for use with agent-browser and Playwright in sandboxes.
"""

import json
import os
import sqlite3
import struct
import time
from pathlib import Path
from typing import Any


# Chrome uses Windows FILETIME epoch (1601-01-01) for cookie timestamps
# Convert from Unix epoch (1970-01-01) to Windows FILETIME
# Difference in microseconds: 11644473600 seconds * 1000000
WINDOWS_EPOCH_OFFSET = 11644473600000000


def _unix_to_chrome_timestamp(unix_timestamp: float | int | None) -> int:
    """Convert Unix timestamp to Chrome timestamp (microseconds since 1601-01-01)."""
    if unix_timestamp is None or unix_timestamp == -1:
        # Return far future for session cookies or unset
        return 0
    # Chrome uses microseconds since Windows FILETIME epoch
    return int(unix_timestamp * 1000000) + WINDOWS_EPOCH_OFFSET


def _now_chrome_timestamp() -> int:
    """Get current time as Chrome timestamp."""
    return _unix_to_chrome_timestamp(time.time())


def _samesite_to_int(samesite: str | None) -> int:
    """Convert SameSite string to Chrome integer value."""
    if samesite is None:
        return -1  # Unspecified
    samesite = samesite.lower()
    if samesite == "strict":
        return 2
    elif samesite == "lax":
        return 1
    elif samesite == "none":
        return 0
    return -1  # Unspecified


def _source_scheme_to_int(secure: bool) -> int:
    """Convert secure flag to source scheme integer."""
    return 2 if secure else 1  # 2 = Secure, 1 = NonSecure, 0 = Unset


def create_cookies_database(db_path: str, cookies: list[dict[str, Any]]) -> None:
    """Create Chrome-compatible cookies SQLite database.

    Args:
        db_path: Path to the Cookies database file
        cookies: List of cookie dictionaries in Playwright storageState format
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the cookies table with Chrome's schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cookies (
            creation_utc INTEGER NOT NULL,
            host_key TEXT NOT NULL,
            top_frame_site_key TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            encrypted_value BLOB NOT NULL DEFAULT X'',
            path TEXT NOT NULL,
            expires_utc INTEGER NOT NULL,
            is_secure INTEGER NOT NULL,
            is_httponly INTEGER NOT NULL,
            last_access_utc INTEGER NOT NULL,
            has_expires INTEGER NOT NULL DEFAULT 1,
            is_persistent INTEGER NOT NULL DEFAULT 1,
            priority INTEGER NOT NULL DEFAULT 1,
            samesite INTEGER NOT NULL DEFAULT -1,
            source_scheme INTEGER NOT NULL DEFAULT 0,
            source_port INTEGER NOT NULL DEFAULT -1,
            is_same_party INTEGER NOT NULL DEFAULT 0,
            last_update_utc INTEGER NOT NULL DEFAULT 0,
            UNIQUE (host_key, top_frame_site_key, name, path, source_scheme, source_port)
        )
    """)

    # Create meta table for database version
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT NOT NULL UNIQUE PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('version', '21')")
    cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_compatible_version', '21')")

    now = _now_chrome_timestamp()

    for cookie in cookies:
        # Handle domain - Chrome uses host_key
        domain = cookie.get("domain", "")
        # Leading dot means subdomain matching
        host_key = domain if domain.startswith(".") else f".{domain}" if domain else ""

        name = cookie.get("name", "")
        value = cookie.get("value", "")
        path = cookie.get("path", "/")

        # Handle expires - Playwright uses Unix timestamp or -1 for session
        expires = cookie.get("expires", -1)
        has_expires = 1 if expires and expires != -1 else 0
        is_persistent = has_expires
        expires_utc = _unix_to_chrome_timestamp(expires) if has_expires else 0

        is_secure = 1 if cookie.get("secure", False) else 0
        is_httponly = 1 if cookie.get("httpOnly", False) else 0

        samesite = _samesite_to_int(cookie.get("sameSite"))
        source_scheme = _source_scheme_to_int(bool(is_secure))

        # Source port - default to -1 (any port) if not specified
        source_port = -1

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO cookies (
                    creation_utc, host_key, top_frame_site_key, name, value,
                    encrypted_value, path, expires_utc, is_secure, is_httponly,
                    last_access_utc, has_expires, is_persistent, priority,
                    samesite, source_scheme, source_port, is_same_party,
                    last_update_utc
                ) VALUES (?, ?, '', ?, ?, X'', ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, 0, ?)
            """, (
                now,  # creation_utc
                host_key,
                name,
                value,
                path,
                expires_utc,
                is_secure,
                is_httponly,
                now,  # last_access_utc
                has_expires,
                is_persistent,
                samesite,
                source_scheme,
                source_port,
                now,  # last_update_utc
            ))
        except sqlite3.Error as e:
            # Skip invalid cookies but log
            print(f"Warning: Could not insert cookie {name}: {e}")

    conn.commit()
    conn.close()


def create_local_storage(ls_path: str, origins: list[dict[str, Any]]) -> None:
    """Create Chrome-compatible Local Storage files.

    Chrome stores localStorage in LevelDB format, but we can use a simpler
    approach with individual JSON files per origin that Playwright can read.

    Args:
        ls_path: Path to the Local Storage directory
        origins: List of origin dictionaries with localStorage data
    """
    os.makedirs(ls_path, exist_ok=True)

    for origin_data in origins:
        origin = origin_data.get("origin", "")
        localStorage = origin_data.get("localStorage", [])

        if not origin or not localStorage:
            continue

        # Create origin-specific directory
        # Chrome uses a hash-based filename, but we'll use the origin name
        # encoded to be filesystem-safe
        safe_origin = origin.replace("://", "_").replace("/", "_").replace(":", "_")
        origin_file = os.path.join(ls_path, f"{safe_origin}.json")

        # Store as JSON - Playwright can read this format
        storage_data = {}
        for item in localStorage:
            name = item.get("name", "")
            value = item.get("value", "")
            if name:
                storage_data[name] = value

        with open(origin_file, "w") as f:
            json.dump(storage_data, f)


def create_preferences_file(prefs_path: str, domains: list[str] | None = None) -> None:
    """Create Chrome preferences file.

    Args:
        prefs_path: Path to the Preferences file
        domains: Optional list of domains for which sessions exist
    """
    prefs = {
        "profile": {
            "name": "Janus Session Profile",
            "created_by_version": "1.0.0",
        },
        "browser": {
            "check_default_browser": False,
            "show_home_button": False,
        },
        "session": {
            "restore_on_startup": 4,  # Open specific URLs
        },
    }

    if domains:
        prefs["janus_session"] = {
            "domains": domains,
            "injected": True,
        }

    os.makedirs(os.path.dirname(prefs_path), exist_ok=True)
    with open(prefs_path, "w") as f:
        json.dump(prefs, f, indent=2)


def create_browser_profile(
    storage_state: dict[str, Any],
    profile_path: str,
    domains: list[str] | None = None,
) -> None:
    """Create a complete Chrome user data directory from Playwright storageState.

    Args:
        storage_state: Playwright storageState dictionary with cookies and origins
        profile_path: Path to create the profile directory
        domains: Optional list of domains for the session (for metadata)

    The profile can be used with:
    - agent-browser --profile {profile_path}
    - Playwright with --user-data-dir={profile_path}
    - Chrome/Chromium with --user-data-dir={profile_path}
    """
    # Create directory structure
    default_path = os.path.join(profile_path, "Default")
    os.makedirs(default_path, exist_ok=True)

    # Create cookies database
    cookies = storage_state.get("cookies", [])
    if cookies:
        cookies_path = os.path.join(default_path, "Cookies")
        create_cookies_database(cookies_path, cookies)

    # Create localStorage
    origins = storage_state.get("origins", [])
    if origins:
        ls_path = os.path.join(default_path, "Local Storage", "leveldb")
        create_local_storage(ls_path, origins)

    # Create preferences file
    prefs_path = os.path.join(default_path, "Preferences")
    create_preferences_file(prefs_path, domains)

    # Also save the original storageState for Playwright compatibility
    state_path = os.path.join(profile_path, "storage_state.json")
    with open(state_path, "w") as f:
        json.dump(storage_state, f, indent=2)


def extract_domains_from_storage_state(storage_state: dict[str, Any]) -> list[str]:
    """Extract unique domains from a storageState.

    Args:
        storage_state: Playwright storageState dictionary

    Returns:
        List of unique domain names
    """
    domains = set()

    # Extract from cookies
    for cookie in storage_state.get("cookies", []):
        domain = cookie.get("domain", "")
        if domain:
            # Remove leading dot
            domain = domain.lstrip(".")
            domains.add(domain)

    # Extract from origins
    for origin_data in storage_state.get("origins", []):
        origin = origin_data.get("origin", "")
        if origin:
            # Parse origin URL to get domain
            try:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                if parsed.netloc:
                    domains.add(parsed.netloc)
            except Exception:
                pass

    return sorted(list(domains))
