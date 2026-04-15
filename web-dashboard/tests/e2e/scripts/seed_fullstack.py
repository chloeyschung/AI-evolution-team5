"""Seed data for circle-3 full-stack browser test."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

REPO_ROOT = Path(__file__).resolve().parents[4]
DB_PATH = REPO_ROOT / "briefly.db"
OUTPUT_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "web-dashboard" / "tests" / "e2e" / ".circle3-seed.json"

USER_ID = 4242
USER_EMAIL = "circle3@briefly.local"
CONTENT_URL = "https://example.com/briefly-circle-3"
CONTENT_TITLE = "Circle 3: DB to Backend to Frontend"
CONTENT_SUMMARY = "Seeded from SQLite, served by FastAPI, rendered by React dashboard."


def create_access_token(user_id: int) -> str:
  secret = os.environ["JWT_SECRET_KEY"]
  now = datetime.now(timezone.utc)
  payload = {
    "sub": str(user_id),
    "exp": now + timedelta(hours=1),
    "iat": now,
    "type": "access",
  }
  return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token() -> str:
  return "circle3-refresh-token-fixed"


def main() -> None:
  now = datetime.now(timezone.utc)
  expires_at = now + timedelta(hours=1)

  access_token = create_access_token(USER_ID)
  refresh_token = create_refresh_token()

  with sqlite3.connect(DB_PATH) as conn:
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
      """
      INSERT INTO user_profile (id, email, display_name, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        email=excluded.email,
        display_name=excluded.display_name,
        updated_at=excluded.updated_at
      """,
      (USER_ID, USER_EMAIL, "Circle 3 User", now.isoformat(), now.isoformat()),
    )

    conn.execute("DELETE FROM authentication_tokens WHERE user_id = ?", (USER_ID,))
    conn.execute("DELETE FROM swipe_history WHERE user_id = ?", (USER_ID,))
    conn.execute("DELETE FROM content WHERE user_id = ?", (USER_ID,))

    conn.execute(
      """
      INSERT INTO authentication_tokens (user_id, access_token, refresh_token, expires_at, created_at, revoked_at)
      VALUES (?, ?, ?, ?, ?, NULL)
      """,
      (USER_ID, hashlib.sha256(access_token.encode()).hexdigest(), refresh_token, expires_at.isoformat(), now.isoformat()),
    )

    conn.execute(
      """
      INSERT INTO content
      (user_id, platform, content_type, url, title, author, summary, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """,
      (
        USER_ID,
        "web",
        "article",
        CONTENT_URL,
        CONTENT_TITLE,
        "Briefly QA",
        CONTENT_SUMMARY,
        "INBOX",
        now.isoformat(),
        now.isoformat(),
      ),
    )

    conn.commit()

  OUTPUT_PATH.write_text(
    json.dumps(
      {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": USER_ID,
        "email": USER_EMAIL,
      },
      indent=2,
    ),
    encoding="utf-8",
  )

  print(OUTPUT_PATH)


if __name__ == "__main__":
  main()
