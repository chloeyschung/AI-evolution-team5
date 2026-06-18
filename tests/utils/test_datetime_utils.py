"""Direct unit tests for datetime utility helpers."""

from datetime import UTC, datetime

from src.utils.datetime_utils import naive_utc_now, serialize_datetime, utc_now


def test_serialize_datetime_none_returns_none():
    assert serialize_datetime(None) is None


def test_naive_utc_now_is_tz_naive():
    """naive_utc_now must be tz-naive (for PostgreSQL `timestamp` columns)."""
    n = naive_utc_now()
    assert n.tzinfo is None


def test_utc_now_is_tz_aware():
    """utc_now stays tz-aware (regression guard against the two diverging)."""
    assert utc_now().tzinfo is not None


def test_naive_and_aware_represent_same_instant():
    """Both should be UTC 'now' — within a small delta, ignoring tzinfo."""
    delta = abs((utc_now().replace(tzinfo=None) - naive_utc_now()).total_seconds())
    assert delta < 5


def test_serialize_datetime_naive_treated_as_utc_with_z_suffix():
    value = datetime(2026, 4, 19, 12, 34, 56)
    assert serialize_datetime(value) == "2026-04-19T12:34:56Z"


def test_serialize_datetime_aware_utc_uses_z_not_offset():
    value = datetime(2026, 4, 19, 12, 34, 56, tzinfo=UTC)
    result = serialize_datetime(value)
    assert result == "2026-04-19T12:34:56Z"
    assert "+00:00" not in result


def test_serialize_datetime_plus_00_00_timezone_normalized_to_z():
    value = datetime(2026, 4, 19, 12, 34, 56, tzinfo=UTC)
    result = serialize_datetime(value)
    assert result.endswith("Z")
    assert "+00:00" not in result
