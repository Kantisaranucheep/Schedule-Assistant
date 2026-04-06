# apps/backend/app/chat/date_parser.py
"""
Date parsing utilities - Convert date references to actual dates.

The LLM extracts raw date references like "tomorrow", "next_monday".
This module converts them to actual day/month/year values.
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
import re


def parse_date_reference(date_ref: str) -> Tuple[int, int, int]:
    """
    Parse a date reference string to (day, month, year).
    
    Args:
        date_ref: String like "tomorrow", "next_monday", "15/4", "15/4/2026"
    
    Returns:
        Tuple of (day, month, year)
    
    Raises:
        ValueError: If date_ref cannot be parsed
    """
    if not date_ref:
        raise ValueError("Empty date reference")
    
    date_ref_lower = date_ref.lower().strip()
    now = datetime.now()
    
    # Handle simple relative dates
    if date_ref_lower == "today":
        return (now.day, now.month, now.year)
    
    if date_ref_lower == "tomorrow":
        tomorrow = now + timedelta(days=1)
        return (tomorrow.day, tomorrow.month, tomorrow.year)
    
    if date_ref_lower == "day_after_tomorrow":
        day_after = now + timedelta(days=2)
        return (day_after.day, day_after.month, day_after.year)
    
    if date_ref_lower == "yesterday":
        yesterday = now - timedelta(days=1)
        return (yesterday.day, yesterday.month, yesterday.year)
    
    if date_ref_lower == "next_week":
        next_week = now + timedelta(days=7)
        return (next_week.day, next_week.month, next_week.year)
    
    # Handle weekday names (this week or next week)
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    
    # Check for "next_monday", "next_tuesday", etc.
    if date_ref_lower.startswith("next_"):
        weekday_name = date_ref_lower[5:]  # Remove "next_"
        if weekday_name in weekdays:
            target_weekday = weekdays[weekday_name]
            days_until = (target_weekday - now.weekday()) % 7
            if days_until == 0:
                days_until = 7  # Next occurrence, not today
            target_date = now + timedelta(days=days_until)
            return (target_date.day, target_date.month, target_date.year)
    
    # Check for plain weekday name (this week if not passed, next week otherwise)
    if date_ref_lower in weekdays:
        target_weekday = weekdays[date_ref_lower]
        days_until = (target_weekday - now.weekday()) % 7
        
        # If the day has already passed this week, go to next week
        if days_until == 0:
            # If it's the same weekday and it's past noon, assume next week
            if now.hour >= 12:
                days_until = 7
            # Otherwise it's today (days_until = 0)
        
        target_date = now + timedelta(days=days_until)
        return (target_date.day, target_date.month, target_date.year)
    
    # Handle "this_monday", "this_tuesday", etc.
    if date_ref_lower.startswith("this_"):
        weekday_name = date_ref_lower[5:]
        if weekday_name in weekdays:
            target_weekday = weekdays[weekday_name]
            days_until = (target_weekday - now.weekday()) % 7
            target_date = now + timedelta(days=days_until)
            return (target_date.day, target_date.month, target_date.year)
    
    # Handle date formats: "15/4", "15/4/2026", "15-4", "15-4-2026"
    # Try DD/MM/YYYY
    match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_ref_lower)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return (day, month, year)
    
    # Try DD/MM (assume current year)
    match = re.match(r'(\d{1,2})[/-](\d{1,2})$', date_ref_lower)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = now.year
        # If the date has passed this year, assume next year
        try:
            target_date = datetime(year, month, day)
            if target_date < now:
                year += 1
        except ValueError:
            # Invalid date, just use current year
            pass
        return (day, month, year)
    
    raise ValueError(f"Cannot parse date reference: {date_ref}")


def parse_date_reference_safe(date_ref: Optional[str]) -> Optional[Tuple[int, int, int]]:
    """
    Safe version of parse_date_reference that returns None on error.
    
    Args:
        date_ref: Date reference string or None
    
    Returns:
        Tuple of (day, month, year) or None if parsing fails
    """
    if not date_ref:
        return None
    
    try:
        return parse_date_reference(date_ref)
    except ValueError:
        return None
