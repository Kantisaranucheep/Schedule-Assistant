"""Pydantic schemas for the scheduling/rescheduling API."""

from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request Schemas ───────────────────────────────────────────────────────────

class RescheduleRequest(BaseModel):
    """Request to reschedule or analyse conflicts for a new event."""
    calendar_id: UUID
    title: str = Field(..., max_length=255)
    start_time: datetime
    end_time: datetime
    category_name: Optional[str] = None
    strategy: str = Field(
        default="balanced",
        pattern=r"^(minimize_moves|maximize_quality|balanced)$",
    )
    min_hour: int = Field(default=6, ge=0, le=23)
    max_hour: int = Field(default=23, ge=1, le=24)


class EventPriorityCheckRequest(BaseModel):
    """Request to check priority of an event title."""
    title: str
    category_name: Optional[str] = None


# ── Response Schemas ──────────────────────────────────────────────────────────

class MoveActionResponse(BaseModel):
    """A single event move action."""
    event_id: str
    event_title: str
    original_start_time: str  # "HH:MM"
    original_end_time: str
    new_start_time: str
    new_end_time: str
    priority: int
    cost: float
    reason: str


class RescheduleOptionResponse(BaseModel):
    """One possible rescheduling option."""
    action: str
    moves: List[MoveActionResponse]
    total_cost: float
    explanation: str
    strategy: str


class RescheduleResponse(BaseModel):
    """Full rescheduling analysis response."""
    has_conflict: bool
    conflicting_events: List[Dict]
    options: List[RescheduleOptionResponse]
    recommended: Optional[RescheduleOptionResponse] = None


class EventPriorityCheckResponse(BaseModel):
    """Priority info for an event."""
    event_type: str
    priority: int
    is_critical: bool
    is_movable: bool
    priority_config: Dict[str, int]


# ── Conflict Resolution Suggestion Schemas ────────────────────────────────────

class ConflictSuggestionRequest(BaseModel):
    """Request to get AI-suggested reschedule times for conflicting events."""
    event_ids: List[UUID]
    collab_event_start: datetime
    collab_event_end: datetime
    collab_event_title: str = ""


class TimeSuggestion(BaseModel):
    """A single time suggestion for rescheduling."""
    new_start: str  # ISO datetime string
    new_end: str
    cost: float
    explanation: str


class EventSuggestions(BaseModel):
    """Suggestions for one conflicting event."""
    event_id: str
    event_title: str
    original_start: str
    original_end: str
    suggestions: List[TimeSuggestion]


class ConflictSuggestionResponse(BaseModel):
    """Response with AI-suggested reschedule times."""
    event_suggestions: List[EventSuggestions]
