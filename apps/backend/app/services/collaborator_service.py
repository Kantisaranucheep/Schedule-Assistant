from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from datetime import datetime
from app.models import EventCollaborator, EventCollaborationInvitation
from app.schemas.collaborator import (
    EventCollaborationInvitationCreate,
    EventCollaborationInvitationRead,
    EventCollaboratorRead,
)

class CollaboratorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def invite(self, data: EventCollaborationInvitationCreate) -> EventCollaborationInvitationRead:
        invitation = EventCollaborationInvitation(**data.dict())
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return EventCollaborationInvitationRead.from_orm(invitation)

    async def accept_invitation(self, invitation_id: UUID) -> EventCollaboratorRead:
        q = await self.db.execute(select(EventCollaborationInvitation).where(EventCollaborationInvitation.id == invitation_id))
        invitation = q.scalar_one_or_none()
        if not invitation or invitation.status != "pending":
            raise Exception("Invalid or already handled invitation")
        invitation.status = "accepted"
        invitation.responded_at = datetime.utcnow()
        collaborator = EventCollaborator(event_id=invitation.event_id, user_id=invitation.invitee_id, role="editor")
        self.db.add(collaborator)
        await self.db.commit()
        await self.db.refresh(collaborator)
        await self.db.refresh(invitation)
        return EventCollaboratorRead.from_orm(collaborator)

    async def decline_invitation(self, invitation_id: UUID) -> EventCollaborationInvitationRead:
        q = await self.db.execute(select(EventCollaborationInvitation).where(EventCollaborationInvitation.id == invitation_id))
        invitation = q.scalar_one_or_none()
        if not invitation or invitation.status != "pending":
            raise Exception("Invalid or already handled invitation")
        invitation.status = "declined"
        invitation.responded_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(invitation)
        return EventCollaborationInvitationRead.from_orm(invitation)

    async def list_event_collaborators(self, event_id: UUID) -> List[EventCollaboratorRead]:
        q = await self.db.execute(select(EventCollaborator).where(EventCollaborator.event_id == event_id))
        return [EventCollaboratorRead.from_orm(row) for row in q.scalars().all()]

    async def list_user_invitations(self, user_id: UUID) -> List[EventCollaborationInvitationRead]:
        q = await self.db.execute(select(EventCollaborationInvitation).where(EventCollaborationInvitation.invitee_id == user_id, EventCollaborationInvitation.status == "pending"))
        return [EventCollaborationInvitationRead.from_orm(row) for row in q.scalars().all()]
