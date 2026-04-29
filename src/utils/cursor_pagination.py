"""Utilities for opaque cursor pagination tokens."""

import base64
import json
from datetime import datetime
from typing import Any


class CursorTokenError(ValueError):
    """Raised when a cursor token cannot be parsed or validated."""


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(token: str) -> bytes:
    padding = "=" * (-len(token) % 4)
    try:
        return base64.urlsafe_b64decode(token + padding)
    except Exception as exc:  # pragma: no cover - exact b64 errors are implementation-specific
        raise CursorTokenError("Cursor token is not valid base64url") from exc


def encode_cursor(payload: dict[str, Any]) -> str:
    """Encode a JSON payload as an opaque base64url cursor token."""
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _b64url_encode(raw)


def decode_cursor(token: str) -> dict[str, Any]:
    """Decode a base64url cursor token into a JSON payload."""
    try:
        decoded = _b64url_decode(token).decode("utf-8")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CursorTokenError("Cursor token is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise CursorTokenError("Cursor payload must be an object")

    return payload


def make_timestamp_cursor(
    *,
    scope: str,
    sort_ts: datetime,
    tie_breaker_id: int,
    context: dict[str, Any] | None = None,
) -> str:
    """Create a versioned cursor token with timestamp + tie-breaker id."""
    payload: dict[str, Any] = {
        "v": 1,
        "scope": scope,
        "ts": sort_ts.isoformat(),
        "id": tie_breaker_id,
    }
    if context:
        payload["ctx"] = context
    return encode_cursor(payload)


def parse_timestamp_cursor(
    token: str,
    *,
    expected_scope: str,
    expected_context: dict[str, Any] | None = None,
) -> tuple[datetime, int]:
    """Parse and validate a versioned timestamp cursor token."""
    payload = decode_cursor(token)

    if payload.get("v") != 1:
        raise CursorTokenError("Unsupported cursor version")
    if payload.get("scope") != expected_scope:
        raise CursorTokenError("Cursor scope mismatch")

    if expected_context is not None and payload.get("ctx") != expected_context:
        raise CursorTokenError("Cursor context mismatch")

    ts_raw = payload.get("ts")
    cursor_id = payload.get("id")
    if not isinstance(ts_raw, str):
        raise CursorTokenError("Cursor timestamp is missing")
    try:
        sort_ts = datetime.fromisoformat(ts_raw)
    except ValueError as exc:
        raise CursorTokenError("Cursor timestamp is invalid") from exc

    if not isinstance(cursor_id, int):
        raise CursorTokenError("Cursor id is invalid")

    return sort_ts, cursor_id
