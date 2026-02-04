# apps/backend/app/agent/schemas.py
"""Pydantic models for structured intent parsing."""

from datetime import date, time, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntentType(str, Enum):
    """Supported intent types."""

    CREATE_EVENT = "create_event"
    FIND_FREE_SLOTS = "find_free_slots"
    MOVE_EVENT = "move_event"
    DELETE_EVENT = "delete_event"
    UNKNOWN = "unknown"


# ============================================================================
# Intent-specific data models
# ============================================================================


class CreateEventData(BaseModel):
    """Data for create_event intent."""

    title: str = Field(..., description="Event title")
    date: str = Field(..., description="Event date (YYYY-MM-DD)")
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: str = Field(..., description="End time (HH:MM)")
    location: Optional[str] = Field(None, description="Event location")
    participants: Optional[List[str]] = Field(None, description="List of participant emails/names")
    description: Optional[str] = Field(None, description="Event description")

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        """Validate time format."""
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        return v


class DateRange(BaseModel):
    """Date range for queries."""

    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


class FindFreeSlotsData(BaseModel):
    """Data for find_free_slots intent."""

    date_range: DateRange = Field(..., description="Date range to search")
    duration_minutes: int = Field(..., ge=15, le=480, description="Desired slot duration")
    constraints: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional constraints (e.g., preferred_times, exclude_weekends)",
    )


class MoveEventData(BaseModel):
    """Data for move_event intent."""

    # Identification - either by ID or by title+date
    event_id: Optional[str] = Field(None, description="Event UUID")
    title: Optional[str] = Field(None, description="Event title (if no ID)")
    original_date: Optional[str] = Field(None, description="Original date (if no ID)")

    # New timing
    new_date: str = Field(..., description="New date (YYYY-MM-DD)")
    new_start_time: str = Field(..., description="New start time (HH:MM)")
    new_end_time: str = Field(..., description="New end time (HH:MM)")

    @field_validator("new_date", "original_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format."""
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class DeleteEventData(BaseModel):
    """Data for delete_event intent."""

    # Identification - either by ID or by title+date
    event_id: Optional[str] = Field(None, description="Event UUID")
    title: Optional[str] = Field(None, description="Event title (if no ID)")
    date: Optional[str] = Field(None, description="Event date (if no ID)")


# ============================================================================
# Main Intent model
# ============================================================================


class Intent(BaseModel):
    """Structured intent parsed from user text."""

    model_config = ConfigDict(use_enum_values=True)

    intent_type: IntentType = Field(..., description="Type of intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    data: Optional[Dict[str, Any]] = Field(None, description="Intent-specific data")
    clarification_question: Optional[str] = Field(
        None,
        description="Question to ask user if fields are missing",
    )
    raw_text: Optional[str] = Field(None, description="Original user text (debug)")

    def get_typed_data(self) -> Union[CreateEventData, FindFreeSlotsData, MoveEventData, DeleteEventData, None]:
        """Get data as the appropriate typed model."""
        if self.data is None:
            return None

        type_map = {
            IntentType.CREATE_EVENT: CreateEventData,
            IntentType.FIND_FREE_SLOTS: FindFreeSlotsData,
            IntentType.MOVE_EVENT: MoveEventData,
            IntentType.DELETE_EVENT: DeleteEventData,
        }

        model_class = type_map.get(IntentType(self.intent_type))
        if model_class:
            return model_class(**self.data)
        return None


class CreateEventIntent(Intent):
    """Convenience class for create_event intent."""

    intent_type: IntentType = IntentType.CREATE_EVENT
    data: CreateEventData


class FindFreeSlotsIntent(Intent):
    """Convenience class for find_free_slots intent."""

    intent_type: IntentType = IntentType.FIND_FREE_SLOTS
    data: FindFreeSlotsData


class MoveEventIntent(Intent):
    """Convenience class for move_event intent."""

    intent_type: IntentType = IntentType.MOVE_EVENT
    data: MoveEventData


class DeleteEventIntent(Intent):
    """Convenience class for delete_event intent."""

    intent_type: IntentType = IntentType.DELETE_EVENT
    data: DeleteEventData


# ============================================================================
# API Request/Response models
# ============================================================================


class ParseRequest(BaseModel):
    """Request to parse user text into intent."""

    text: str = Field(..., min_length=1, max_length=2000, description="User input text")
    user_id: Optional[UUID] = Field(None, description="User ID for context")
    calendar_id: Optional[UUID] = Field(None, description="Calendar ID for context")


class ParseResponse(BaseModel):
    """Response from intent parsing."""

    success: bool = Field(..., description="Whether parsing succeeded")
    intent: Optional[Intent] = Field(None, description="Parsed intent if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error info")


class ExecuteRequest(BaseModel):
    """Request to execute a parsed intent."""

    intent: Intent = Field(..., description="Intent to execute")
    user_id: UUID = Field(..., description="User ID")
    calendar_id: UUID = Field(..., description="Calendar ID")
    dry_run: bool = Field(False, description="If true, validate but don't execute")


class ExecuteResponse(BaseModel):
    """Response from intent execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    message: Optional[str] = Field(None, description="Human-readable message")
    error: Optional[str] = Field(None, description="Error message if failed")
    prolog_validation: Optional[Dict[str, Any]] = Field(
        None,
        description="Prolog constraint validation results",
    )
