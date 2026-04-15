"""Pydantic schemas for user profile/persona API."""

from typing import Optional, Dict
from pydantic import BaseModel, Field


class UserStoryRequest(BaseModel):
    """Request to save user story/persona."""
    user_story: str = Field(
        ..., 
        description="Natural language description of who the user is",
        min_length=10,
        max_length=5000,
        examples=["I'm a software engineering student in my third year, focused on academic success and preparing for internships."]
    )
    extract_priorities: bool = Field(
        default=True,
        description="Whether to extract priorities from the story using LLM"
    )


class PriorityUpdateRequest(BaseModel):
    """Request to manually update priorities."""
    priorities: Dict[str, int] = Field(
        ...,
        description="Dict of event_type -> priority weight (1-10)",
        examples=[{"meeting": 9, "study": 10, "party": 3}]
    )
    strategy: Optional[str] = Field(
        default=None,
        description="Scheduling strategy: minimize_moves, maximize_quality, or balanced"
    )


class StrategyUpdateRequest(BaseModel):
    """Request to update scheduling strategy."""
    strategy: str = Field(
        ...,
        description="Scheduling strategy",
        pattern="^(minimize_moves|maximize_quality|balanced)$"
    )


class PriorityExtractionResponse(BaseModel):
    """Response from priority extraction."""
    success: bool
    priorities: Dict[str, int] = Field(default_factory=dict)
    persona_summary: Optional[str] = None
    reasoning: Optional[str] = None
    recommended_strategy: Optional[str] = None
    error: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Response containing user profile data."""
    id: str
    user_id: str
    user_story: Optional[str] = None
    priority_config: Optional[Dict[str, int]] = None
    default_priorities: Optional[Dict[str, int]] = None
    scheduling_strategy: str = "balanced"
    priorities_extracted_at: Optional[str] = None
    
    # Merged priorities (defaults + extracted)
    merged_priorities: Dict[str, int] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class UserProfileWithExtractionResponse(BaseModel):
    """Response when saving user story with extraction results."""
    profile: UserProfileResponse
    extraction: Optional[PriorityExtractionResponse] = None


class EventPriorityRequest(BaseModel):
    """Request to get priority for an event type."""
    event_type: str = Field(
        ...,
        description="Type of event to get priority for",
        examples=["meeting", "exam", "party"]
    )


class EventPriorityResponse(BaseModel):
    """Response with priority for an event type."""
    event_type: str
    priority: int
    source: str = Field(
        description="Where the priority came from: 'extracted', 'default', or 'fallback'"
    )
