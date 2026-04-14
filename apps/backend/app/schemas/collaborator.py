from datetime import datetime
from typing import Optional, List
import uuid
from pydantic import BaseModel

class EventCollaboratorBase(BaseModel):
    event_id: uuid.UUID
    user_id: uuid.UUID
    role: str = "editor"

class EventCollaboratorCreate(EventCollaboratorBase):
    pass

class EventCollaboratorRead(EventCollaboratorBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class EventCollaborationInvitationBase(BaseModel):
    event_id: uuid.UUID
    inviter_id: uuid.UUID
    invitee_id: uuid.UUID
    status: str = "pending"
    responded_at: Optional[datetime] = None

class EventCollaborationInvitationCreate(EventCollaborationInvitationBase):
    pass

class EventCollaborationInvitationRead(EventCollaborationInvitationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class EventCollaborationInvitationWithDetailsRead(EventCollaborationInvitationRead):
    event_title: str
    event_date: str
    inviter_username: str

    model_config = {"from_attributes": True}
