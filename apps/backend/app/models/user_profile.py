"""User Profile model for storing user persona and priority preferences."""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User


class UserProfile(BaseModel):
    """User profile with persona story and extracted priority preferences.
    
    This model stores:
    - user_story: The natural language description of who the user is
    - priority_config: JSON with event_type -> weight mapping (1-10 scale)
    - scheduling_strategy: User's preferred conflict resolution strategy
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        unique=True,
        index=True
    )
    
    # The user's story/persona in natural language
    # e.g., "I'm a software engineering student focused on academic success..."
    user_story: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Extracted priority configuration from LLM analysis
    # Format: {"meeting": 9, "study": 10, "party": 3, "exam": 10, ...}
    priority_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Default event type priorities (if LLM extraction hasn't run yet)
    # This provides baseline weights for common event types
    default_priorities: Mapped[Optional[dict]] = mapped_column(
        JSON, 
        nullable=True,
        default=lambda: {
            "meeting": 7,
            "exam": 10,
            "study": 8,
            "deadline": 10,
            "appointment": 7,
            "class": 8,
            "work": 8,
            "exercise": 5,
            "social": 4,
            "party": 3,
            "personal": 5,
            "travel": 6,
            "other": 5
        }
    )
    
    # User's preferred scheduling/conflict resolution strategy
    # Options: "minimize_moves", "maximize_quality", "balanced"
    scheduling_strategy: Mapped[str] = mapped_column(
        String(50), 
        default="balanced"
    )
    
    # Cache validity - timestamp when priorities were last extracted
    # Used to determine if re-extraction is needed
    priorities_extracted_at: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True
    )
    
    # Relationship back to user
    user: Mapped["User"] = relationship("User", back_populates="profile")
    
    def get_priority(self, event_type: str) -> int:
        """Get priority weight for an event type.
        
        Checks priority_config first, then falls back to default_priorities.
        Returns 5 if event type is not found in either.
        """
        event_type_lower = event_type.lower()
        
        # Check extracted priorities first
        if self.priority_config and event_type_lower in self.priority_config:
            return self.priority_config[event_type_lower]
        
        # Fall back to defaults
        if self.default_priorities and event_type_lower in self.default_priorities:
            return self.default_priorities[event_type_lower]
        
        # Default weight for unknown types
        return 5
    
    def merge_priorities(self) -> dict:
        """Get merged priority config (defaults + extracted).
        
        Extracted priorities override defaults.
        """
        merged = dict(self.default_priorities or {})
        if self.priority_config:
            merged.update(self.priority_config)
        return merged
