"""Centralized datetime utilities for Briefly.

This module provides common datetime operations to avoid duplication across the codebase.
All datetime operations should use these utilities for consistency and maintainability.
"""

from datetime import UTC, datetime, timedelta
from datetime import time as time_type


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime.

    Returns:
        Current UTC datetime with timezone info.
    """
    return datetime.now(UTC)


def convert_to_utc(dt: datetime | None) -> datetime | None:
    """Convert datetime to UTC if naive or in different timezone.

    Args:
        dt: Datetime to convert (may be naive or aware)

    Returns:
        UTC datetime or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def convert_to_local(dt: datetime | None) -> datetime | None:
    """Convert datetime to local timezone.

    Args:
        dt: Datetime to convert (may be naive or aware)

    Returns:
        Local datetime with local timezone or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is UTC first
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(time_type.min.tzinfo)


def add_timedelta(
    dt: datetime,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> datetime:
    """Add a timedelta to a datetime.

    Args:
        dt: Base datetime
        days: Days to add
        hours: Hours to add
        minutes: Minutes to add
        seconds: Seconds to add

    Returns:
        Datetime with applied offset
    """
    return dt + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def subtract_timedelta(
    dt: datetime,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> datetime:
    """Subtract a timedelta from a datetime.

    Args:
        dt: Base datetime
        days: Days to subtract
        hours: Hours to subtract
        minutes: Minutes to subtract
        seconds: Seconds to subtract

    Returns:
        Datetime with applied subtraction
    """
    return dt - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def days_since(dt: datetime, reference: datetime | None = None) -> float:
    """Calculate days since a datetime.

    Args:
        dt: Datetime to calculate from
        reference: Reference datetime (defaults to UTC now)

    Returns:
        Days as float (can be negative if dt is in the future)
    """
    if reference is None:
        reference = utc_now()
    delta = reference - dt
    return delta.total_seconds() / (24 * 60 * 60)


def is_expired(dt: datetime, buffer_minutes: int = 0) -> bool:
    """Check if datetime is expired (in the past).

    Args:
        dt: Datetime to check
        buffer_minutes: Optional buffer in minutes

    Returns:
        True if datetime is expired, False otherwise
    """
    check_time = utc_now()
    if buffer_minutes > 0:
        check_time = subtract_timedelta(check_time, minutes=buffer_minutes)
    return dt < check_time


def is_within_time_range(dt: datetime, days: int) -> bool:
    """Check if datetime is within the last N days.

    Args:
        dt: Datetime to check
        days: Number of days to check against

    Returns:
        True if datetime is within the last N days, False otherwise
    """
    cutoff = subtract_timedelta(utc_now(), days=days)
    dt_utc = convert_to_utc(dt)
    return dt_utc is not None and dt_utc >= cutoff


def is_in_time_range(
    dt: datetime,
    start: datetime,
    end: datetime,
) -> bool:
    """Check if datetime is within a range.

    Args:
        dt: Datetime to check
        start: Start of range (inclusive)
        end: End of range (inclusive)

    Returns:
        True if datetime is within range, False otherwise
    """
    dt_utc = convert_to_utc(dt)
    if dt_utc is None:
        return False
    return start <= dt_utc <= end


def get_start_of_day(dt: datetime | None = None) -> datetime:
    """Get the start of the day for a datetime.

    Args:
        dt: Datetime (defaults to UTC now)

    Returns:
        Datetime at start of day (00:00:00)
    """
    if dt is None:
        dt = utc_now()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_end_of_day(dt: datetime | None = None) -> datetime:
    """Get the end of the day for a datetime.

    Args:
        dt: Datetime (defaults to UTC now)

    Returns:
        Datetime at end of day (23:59:59.999999)
    """
    if dt is None:
        dt = utc_now()
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def is_same_day(dt1: datetime, dt2: datetime | None = None) -> bool:
    """Check if two datetimes are on the same day.

    Args:
        dt1: First datetime
        dt2: Second datetime (defaults to UTC now)

    Returns:
        True if both datetimes are on the same day
    """
    if dt2 is None:
        dt2 = utc_now()
    return dt1.date() == dt2.date()


def is_quiet_hours(
    current_time: datetime,
    quiet_start: time_type,
    quiet_end: time_type,
) -> bool:
    """Check if current time is within quiet hours.

    Args:
        current_time: Current datetime
        quiet_start: Start of quiet hours (e.g., 22:00)
        quiet_end: End of quiet hours (e.g., 08:00)

    Returns:
        True if within quiet hours, False otherwise
    """
    current = current_time.time()

    # Handle overnight quiet hours (e.g., 22:00 to 08:00)
    if quiet_start > quiet_end:
        # Quiet hours span midnight: from quiet_start to midnight, and from midnight to quiet_end
        # Use >= for start (inclusive) and < for end (exclusive) to handle boundary correctly
        return current >= quiet_start or current < quiet_end
    else:
        # Quiet hours within same day
        return quiet_start <= current < quiet_end


def parse_iso_datetime(datetime_str: str) -> datetime:
    """Parse ISO format datetime string to datetime.

    Args:
        datetime_str: ISO format datetime string (e.g., "2024-01-15T10:30:00Z")

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If string cannot be parsed
    """
    # Handle 'Z' suffix (UTC)
    if datetime_str.endswith("Z"):
        datetime_str = datetime_str[:-1] + "+00:00"
    return datetime.fromisoformat(datetime_str)


def format_iso_datetime(dt: datetime) -> str:
    """Format datetime as ISO format string.

    Args:
        dt: Datetime to format

    Returns:
        ISO format datetime string (e.g., "2024-01-15T10:30:00+00:00")
    """
    return dt.isoformat()


def serialize_datetime(dt: datetime | None) -> str | None:
    """Serialize datetime to an ISO 8601 string with Z suffix for iOS JSONDecoder.

    iOS ``JSONDecoder`` with ``.iso8601`` strategy requires exactly
    ``YYYY-MM-DDTHH:MM:SSZ`` format — no microseconds, no ``+00:00`` offset.

    Args:
        dt: Datetime to serialize (naive or aware).  Naive datetimes are
            treated as UTC.  Aware datetimes in other timezones are converted
            to UTC before formatting.  ``None`` passes through unchanged.

    Returns:
        ISO 8601 string ending with ``Z``, or ``None`` if *dt* is ``None``.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Naive → assume UTC; no conversion needed
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Aware → convert to UTC first
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def combine_date_and_time(date_part: datetime, time_part: time_type) -> datetime:
    """Combine a date and time into a datetime.

    Args:
        date_part: Datetime providing the date component
        time_part: Time to use for the time component

    Returns:
        Combined datetime (naive)
    """
    return datetime.combine(date_part.date(), time_part)
