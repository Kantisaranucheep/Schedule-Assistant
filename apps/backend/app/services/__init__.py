# schedule-assistant/apps/backend/app/services/__init__.py
"""Business logic services."""

from app.services.availability import get_available_slots, TimeSlot
from app.services.conflicts import check_event_conflicts

__all__ = [
    "get_available_slots",
    "TimeSlot",
    "check_event_conflicts",
]
