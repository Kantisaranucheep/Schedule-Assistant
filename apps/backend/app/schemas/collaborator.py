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


# --- Conflict checking response models ---

class ConflictingEventInfo(BaseModel):
    """Info about an existing event that conflicts with the collaboration event."""
    event_id: uuid.UUID
    title: str
    start_time: str
    end_time: str
    calendar_id: uuid.UUID

class AcceptInvitationResponse(BaseModel):
    """Response when accepting an invitation — may contain conflict info."""
    status: str  # "accepted" or "conflict"
    collaborator: Optional[EventCollaboratorRead] = None
    # Conflict fields (only present when status == "conflict")
    has_conflict: bool = False
    conflicts: List[ConflictingEventInfo] = []
    collab_event_title: Optional[str] = None
    collab_event_start: Optional[str] = None
    collab_event_end: Optional[str] = None
    invitation_id: Optional[uuid.UUID] = None
    message: Optional[str] = None

class ForceAcceptRequest(BaseModel):
    """User confirms accepting invitation despite conflict."""
    invitation_id: uuid.UUID

class ReportConflictRequest(BaseModel):
    """Invitee reports conflict back to the event creator."""
    invitation_id: uuid.UUID
    message: Optional[str] = None

class ReportConflictResponse(BaseModel):
    status: str  # "reported"
    message: str

class ConflictReportRead(BaseModel):
    """Conflict report displayed to the event creator."""
    invitation_id: uuid.UUID
    event_id: uuid.UUID
    event_title: str
    reporter_username: str
    message: str
