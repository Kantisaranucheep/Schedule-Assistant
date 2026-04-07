"""User settings schemas."""

import json
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, EmailStr


class NotificationTimePreference(BaseModel):
    """A single notification time preference."""
    minutes_before: int = Field(
        ..., 
        ge=10,  # Minimum 10 minutes before
        le=1440,  # Maximum 1 day (1440 minutes) before
        description="Minutes before event to send notification (10-1440)"
    )
    label: Optional[str] = None  # e.g., "1 day before", "30 minutes before"


class UserSettingsBase(BaseModel):
    """Base settings fields."""

    working_hours_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    working_hours_end: str = Field(default="18:00", pattern=r"^\d{2}:\d{2}$")
    buffer_minutes: int = Field(default=10, ge=0, le=120)


class UserSettingsCreate(UserSettingsBase):
    """Create settings request."""

    user_id: UUID
    notification_email: Optional[str] = None
    notifications_enabled: bool = False
    window_notifications_enabled: bool = True
    notification_times: List[NotificationTimePreference] = Field(default_factory=list)
    
    @field_validator('notification_times')
    @classmethod
    def validate_notification_times(cls, v):
        if len(v) > 2:
            raise ValueError('Maximum 2 notification times allowed')
        return v
    
    @field_validator('notification_email')
    @classmethod
    def validate_email(cls, v):
        if v is not None and v != '':
            # Basic email validation
            if '@' not in v or '.' not in v:
                raise ValueError('Invalid email format')
        return v


class UserSettingsUpdate(BaseModel):
    """Update settings request."""

    working_hours_start: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    working_hours_end: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    buffer_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    notification_email: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    window_notifications_enabled: Optional[bool] = None
    notification_times: Optional[List[NotificationTimePreference]] = None
    
    @field_validator('notification_times')
    @classmethod
    def validate_notification_times(cls, v):
        if v is not None and len(v) > 2:
            raise ValueError('Maximum 2 notification times allowed')
        return v


class UserSettingsResponse(UserSettingsBase):
    """Settings response."""

    id: UUID
    user_id: UUID
    notification_email: Optional[str] = None
    notifications_enabled: bool = False
    window_notifications_enabled: bool = True
    notification_times: List[NotificationTimePreference] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
    
    @classmethod
    def from_orm_with_times(cls, obj):
        """Create response from ORM object, parsing notification_times_json."""
        data = {
            "id": obj.id,
            "user_id": obj.user_id,
            "working_hours_start": obj.working_hours_start,
            "working_hours_end": obj.working_hours_end,
            "buffer_minutes": obj.buffer_minutes,
            "notification_email": obj.notification_email,
            "notifications_enabled": obj.notifications_enabled,
            "window_notifications_enabled": obj.window_notifications_enabled,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "notification_times": [],
        }
        
        # Parse notification_times_json
        if obj.notification_times_json:
            try:
                times_data = json.loads(obj.notification_times_json)
                data["notification_times"] = [
                    NotificationTimePreference(**t) if isinstance(t, dict) else NotificationTimePreference(minutes_before=t)
                    for t in times_data
                ]
            except (json.JSONDecodeError, TypeError):
                data["notification_times"] = []
        
        return cls(**data)
