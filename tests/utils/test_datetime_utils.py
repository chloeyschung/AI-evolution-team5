"""Direct unit tests for datetime utility helpers."""

from datetime import UTC, datetime, timezone

from src.utils.datetime_utils import serialize_datetime


def test_serialize_datetime_none_returns_none():
    assert serialize_datetime(None) is None


def test_serialize_datetime_naive_treated_as_utc_with_z_suffix():
    value = datetime(2026, 4, 19, 12, 34, 56)
    assert serialize_datetime(value) == "2026-04-19T12:34:56Z"


def test_serialize_datetime_aware_utc_uses_z_not_offset():
    value = datetime(2026, 4, 19, 12, 34, 56, tzinfo=UTC)
    result = serialize_datetime(value)
    assert result == "2026-04-19T12:34:56Z"
    assert "+00:00" not in result


def test_serialize_datetime_plus_00_00_timezone_normalized_to_z():
    value = datetime(2026, 4, 19, 12, 34, 56, tzinfo=timezone.utc)
    result = serialize_datetime(value)
    assert result.endswith("Z")
    assert "+00:00" not in result
