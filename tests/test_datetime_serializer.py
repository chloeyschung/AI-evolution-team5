"""Tests for serialize_datetime() utility in datetime_utils.

TDD: these tests are written BEFORE the implementation.
All tests must FAIL initially, then PASS after implementation.
"""

import re
from datetime import UTC, datetime, timezone, timedelta

import pytest

from src.utils.datetime_utils import serialize_datetime


class TestSerializeDatetimeNaiveUtc:
    def test_serialize_datetime_naive_utc_returns_z_suffix(self):
        """Naive datetime is treated as UTC and output ends with Z."""
        dt = datetime(2024, 6, 15, 10, 30, 45)  # naive
        result = serialize_datetime(dt)
        assert result is not None
        assert result.endswith("Z"), f"Expected Z suffix, got: {result!r}"

    def test_serialize_datetime_naive_utc_value_preserved(self):
        """Naive datetime value is not altered when treated as UTC."""
        dt = datetime(2024, 6, 15, 10, 30, 45)
        result = serialize_datetime(dt)
        assert result == "2024-06-15T10:30:45Z"


class TestSerializeDatetimeAwareUtc:
    def test_serialize_datetime_aware_utc_returns_z_suffix(self):
        """Aware UTC datetime output ends with Z."""
        dt = datetime(2024, 6, 15, 10, 30, 45, tzinfo=UTC)
        result = serialize_datetime(dt)
        assert result is not None
        assert result.endswith("Z"), f"Expected Z suffix, got: {result!r}"

    def test_serialize_datetime_aware_utc_value_correct(self):
        """Aware UTC datetime formats correctly."""
        dt = datetime(2024, 6, 15, 10, 30, 45, tzinfo=UTC)
        result = serialize_datetime(dt)
        assert result == "2024-06-15T10:30:45Z"


class TestSerializeDatetimeAwareOtherTz:
    def test_serialize_datetime_aware_other_tz_converts_to_utc(self):
        """Aware datetime with non-UTC timezone is converted to UTC and ends with Z."""
        # UTC+9 (e.g., Korea Standard Time)
        kst = timezone(timedelta(hours=9))
        dt = datetime(2024, 6, 15, 19, 30, 45, tzinfo=kst)  # 19:30 KST = 10:30 UTC
        result = serialize_datetime(dt)
        assert result is not None
        assert result.endswith("Z"), f"Expected Z suffix, got: {result!r}"
        assert result == "2024-06-15T10:30:45Z", f"Expected UTC conversion, got: {result!r}"

    def test_serialize_datetime_aware_negative_offset_converts_to_utc(self):
        """Aware datetime with negative UTC offset converts correctly."""
        # UTC-5 (e.g., US Eastern Standard Time)
        est = timezone(timedelta(hours=-5))
        dt = datetime(2024, 6, 15, 5, 30, 45, tzinfo=est)  # 05:30 EST = 10:30 UTC
        result = serialize_datetime(dt)
        assert result == "2024-06-15T10:30:45Z"


class TestSerializeDatetimeNone:
    def test_serialize_datetime_none_returns_none(self):
        """None input returns None."""
        result = serialize_datetime(None)
        assert result is None


class TestSerializeDatetimeFormat:
    def test_serialize_datetime_format_is_iso8601(self):
        """Output matches YYYY-MM-DDTHH:MM:SSZ exactly (no microseconds, no offset)."""
        dt = datetime(2024, 6, 15, 10, 30, 45, tzinfo=UTC)
        result = serialize_datetime(dt)
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        assert re.match(pattern, result), (
            f"Result {result!r} does not match ISO 8601 pattern {pattern!r}"
        )

    def test_serialize_datetime_no_microseconds(self):
        """Microseconds are stripped from output."""
        dt = datetime(2024, 6, 15, 10, 30, 45, 123456, tzinfo=UTC)
        result = serialize_datetime(dt)
        assert result == "2024-06-15T10:30:45Z"

    def test_serialize_datetime_no_offset_notation(self):
        """Output does not contain +00:00 or other offset notation."""
        dt = datetime(2024, 6, 15, 10, 30, 45, tzinfo=UTC)
        result = serialize_datetime(dt)
        assert "+" not in result
        assert result.count(":") == 2  # only HH:MM:SS colons
