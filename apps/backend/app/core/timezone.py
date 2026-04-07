# apps/backend/app/core/timezone.py
"""
Timezone utilities for consistent time handling throughout the application.

This module provides a single source of truth for timezone-aware datetime operations.
It automatically detects the system timezone at startup and provides utility functions
to get the current time with proper timezone awareness.

On Windows without the tzdata package, it uses the system's local timezone directly.
On systems with tzdata (Linux, Docker, or Windows with tzdata installed), it uses IANA timezones.
"""

from datetime import datetime, timezone as dt_timezone, timedelta
from typing import Optional, Union

# Try to import ZoneInfo - available in Python 3.9+
try:
    from zoneinfo import ZoneInfo
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZoneInfo = None
    ZONEINFO_AVAILABLE = False


def _try_zoneinfo(tz_name: str) -> Optional["ZoneInfo"]:
    """Try to create a ZoneInfo object, returning None if it fails."""
    if not ZONEINFO_AVAILABLE:
        return None
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return None


def _detect_system_timezone() -> Union["ZoneInfo", dt_timezone]:
    """
    Detect the system's local timezone.
    
    Returns:
        ZoneInfo or timezone object representing the system timezone.
        Uses the system's actual local timezone, not a hardcoded default.
    """
    # Get the local timezone from the system
    # datetime.now().astimezone() returns a datetime with the local timezone
    local_dt = datetime.now().astimezone()
    local_tz = local_dt.tzinfo
    
    if local_tz is None:
        # Shouldn't happen, but fallback to UTC
        return dt_timezone.utc
    
    # Try to get IANA timezone name if available
    if hasattr(local_tz, 'key') and local_tz.key:
        # Python 3.9+ ZoneInfo has a key attribute
        tz = _try_zoneinfo(local_tz.key)
        if tz:
            return tz
    
    # Try to get the timezone name directly
    tz_name = str(local_tz)
    if tz_name and not tz_name.startswith('UTC'):
        tz = _try_zoneinfo(tz_name)
        if tz:
            return tz
    
    # Calculate the offset and try to find a matching IANA timezone
    offset = local_tz.utcoffset(datetime.now())
    if offset is not None:
        offset_hours = offset.total_seconds() / 3600
        
        # Map common offsets to IANA timezones (for systems with tzdata)
        offset_map = {
            7.0: "Asia/Bangkok",
            8.0: "Asia/Singapore", 
            9.0: "Asia/Tokyo",
            0.0: "UTC",
            1.0: "Europe/Paris",
            -5.0: "America/New_York",
            -6.0: "America/Chicago",
            -7.0: "America/Denver",
            -8.0: "America/Los_Angeles",
        }
        
        if offset_hours in offset_map:
            tz = _try_zoneinfo(offset_map[offset_hours])
            if tz:
                return tz
        
        # If IANA timezone lookup failed, create a fixed offset timezone
        # This works on Windows without tzdata
        return dt_timezone(offset)
    
    # Last resort: use UTC
    return dt_timezone.utc


def _get_timezone_name(tz: Union["ZoneInfo", dt_timezone]) -> str:
    """Get a human-readable name for a timezone."""
    if ZONEINFO_AVAILABLE and isinstance(tz, ZoneInfo):
        return str(tz)
    elif isinstance(tz, dt_timezone):
        offset = tz.utcoffset(datetime.now())
        if offset:
            total_seconds = int(offset.total_seconds())
            hours, remainder = divmod(abs(total_seconds), 3600)
            minutes = remainder // 60
            sign = '+' if total_seconds >= 0 else '-'
            if minutes:
                return f"UTC{sign}{hours}:{minutes:02d}"
            else:
                return f"UTC{sign}{hours}"
        return "UTC"
    return str(tz)


# Detect system timezone at module load time (startup)
SYSTEM_TIMEZONE: Union["ZoneInfo", dt_timezone] = _detect_system_timezone()
SYSTEM_TIMEZONE_NAME: str = _get_timezone_name(SYSTEM_TIMEZONE)


def get_system_timezone() -> Union["ZoneInfo", dt_timezone]:
    """
    Get the detected system timezone.
    
    Returns:
        ZoneInfo or timezone object representing the system timezone.
    """
    return SYSTEM_TIMEZONE


def get_system_timezone_name() -> str:
    """
    Get the name of the detected system timezone.
    
    Returns:
        String name of the timezone (e.g., "Asia/Bangkok" or "UTC+7").
    """
    return SYSTEM_TIMEZONE_NAME


def now(tz: Optional[Union["ZoneInfo", dt_timezone]] = None) -> datetime:
    """
    Get the current datetime with timezone awareness.
    
    This function should be used instead of datetime.now() throughout the application
    to ensure consistent timezone handling.
    
    Args:
        tz: Optional timezone to use. If None, uses the system timezone.
    
    Returns:
        Timezone-aware datetime object.
    """
    if tz is None:
        tz = SYSTEM_TIMEZONE
    return datetime.now(tz)


def now_utc() -> datetime:
    """
    Get the current datetime in UTC.
    
    Returns:
        Timezone-aware datetime object in UTC.
    """
    return datetime.now(dt_timezone.utc)


def localize(dt: datetime, tz: Optional[Union["ZoneInfo", dt_timezone]] = None) -> datetime:
    """
    Add timezone info to a naive datetime or convert a timezone-aware datetime.
    
    Args:
        dt: The datetime to localize or convert.
        tz: Target timezone. If None, uses the system timezone.
    
    Returns:
        Timezone-aware datetime in the specified timezone.
    """
    if tz is None:
        tz = SYSTEM_TIMEZONE
    
    if dt.tzinfo is None:
        # Naive datetime - assume it's in the target timezone
        return dt.replace(tzinfo=tz)
    else:
        # Already has timezone - convert to target
        return dt.astimezone(tz)


def to_local(dt: datetime) -> datetime:
    """
    Convert a datetime to the system's local timezone.
    
    Args:
        dt: The datetime to convert (can be naive or aware).
    
    Returns:
        Timezone-aware datetime in the system timezone.
    """
    return localize(dt, SYSTEM_TIMEZONE)
