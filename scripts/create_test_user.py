#!/usr/bin/env python
"""Create a test user for E2E testing or get the latest test user.

This script creates uniquely-named test users for tracking test incidents.
The email format encodes the test context, timestamp, and ordinal number.

Usage:
    # Create a new test user
    uv run scripts/create_test_user.py <test-context>

    # Get the latest test user (for E2E tests to auto-discover)
    uv run scripts/create_test_user.py --get-latest

Examples:
    # Debugging a specific bug
    uv run scripts/create_test_user.py "infinite-loading-during-login"

    # Testing after code changes
    uv run scripts/create_test_user.py "iOS-compliance-post-code-change"

    # Feature testing
    uv run scripts/create_test_user.py "oauth-flow-feature-test"

    # Regression testing
    uv run scripts/create_test_user.py "regression-auth-flow-20260419"

    # Get latest for E2E test
    uv run scripts/create_test_user.py --get-latest

Output:
    Email: debug-<context>-<YYYYMMDD>-<NN>@test.com
    Password: testtest

The generated credentials can be used in:
    - Manual browser testing
    - E2E test scripts (via environment variables or inline)
    - API integration tests
"""

import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PASSWORD = "testtest"


def load_env_file() -> None:
    """Load root .env values needed by src.config-backed auth helpers."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key, value)


def sqlite_path_from_database_url() -> Path:
    """Resolve the configured SQLite database path."""
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./briefly.db")
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            raw_path = url[len(prefix) :]
            path = Path(raw_path)
            return path if path.is_absolute() else REPO_ROOT / path
    raise RuntimeError(f"create_test_user.py only supports SQLite DATABASE_URL values, got: {url}")


load_env_file()
if "EMAIL_LOOKUP_KEY" not in os.environ:
    raise RuntimeError("EMAIL_LOOKUP_KEY is required. Run ./start-dev.sh setup first.")
sys.path.insert(0, str(REPO_ROOT))

from src.auth.email_auth import encrypt_email, hash_password, hmac_email  # noqa: E402


def get_latest_test_user() -> str | None:
    """Get the most recently created test user with @test.com domain.

    Returns:
        Email of the latest test user, or None if no test user exists.
    """
    conn = sqlite3.connect(sqlite_path_from_database_url())
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email FROM user_profile
        WHERE email LIKE '%@test.com'
        ORDER BY created_at DESC
        LIMIT 1
    """)

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def sanitize_context(context: str) -> str:
    """Convert context description to valid email local-part.

    The sanitized string:
    - Uses lowercase letters, digits, and hyphens only
    - Is limited to 40 characters to leave room for timestamp and ordinal
    - Preserves readability for tracking test incidents
    """
    # Replace spaces and special chars with hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", context.lower())
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip("-")
    # Limit to 40 chars to leave room for timestamp and ordinal in 320-char email
    return sanitized[:40]


def create_test_user(context: str) -> tuple[str, str]:
    """Create a test user with a descriptive email based on the test context.

    The email format is: debug-<context>-<YYYYMMDD>-<NN>@test.com

    This allows tracking:
    - What test/feature/incident this user is for (context)
    - When it was created (timestamp)
    - Which iteration if multiple users needed (ordinal)

    Args:
        context: Description of the test context (e.g., "iOS-compliance", "login-bug")

    Returns:
        Tuple of (email, password)
    """
    conn = sqlite3.connect(sqlite_path_from_database_url())
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y%m%d")
    sanitized = sanitize_context(context)

    # Find next available ordinal for this context/date
    ordinal = 1
    while True:
        email = f"debug-{sanitized}-{timestamp}-{ordinal:02d}@test.com"
        cursor.execute("SELECT id FROM user_profile WHERE email = ?", (email,))
        if not cursor.fetchone():
            break
        ordinal += 1

    hashed = hash_password(DEFAULT_PASSWORD)

    # Create user
    cursor.execute(
        """
        INSERT INTO user_profile (email, display_name, created_at, updated_at, is_deleted)
        VALUES (?, ?, datetime("now"), datetime("now"), 0)
    """,
        (email, f"E2E: {context}"),
    )

    user_id = cursor.lastrowid
    print(f"Created user {email} with id={user_id}")

    # Create auth method
    provider_id = hmac_email(email)

    cursor.execute(
        """
        INSERT INTO user_auth_methods (user_id, provider, provider_id, password_hash, email_encrypted, email_verified, verified_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, datetime("now"), datetime("now"), datetime("now"))
    """,
        (user_id, "EMAIL_PASSWORD", provider_id, hashed, encrypt_email(email)),
    )

    print(f"Created auth method with provider_id={provider_id[:20]}...")

    conn.commit()
    conn.close()

    return email, DEFAULT_PASSWORD


if __name__ == "__main__":
    # Handle --get-latest flag for E2E tests
    if len(sys.argv) == 2 and sys.argv[1] == "--get-latest":
        latest = get_latest_test_user()
        if latest:
            print(latest)
        sys.exit(0)

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    context = " ".join(sys.argv[1:])
    print(f"Creating test user for context: {context}\n")

    email, password = create_test_user(context)

    print(f"\n{'='*60}")
    print("Test credentials:")
    print(f"  Email:    {email}")
    print(f"  Password: {password}")
    print(f"{'='*60}")
    print("\nUsage in E2E tests:")
    print(f"  TEST_EMAIL={email} TEST_PASSWORD={password} npx playwright test")
