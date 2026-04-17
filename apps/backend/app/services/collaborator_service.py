from uuid import UUID
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, and_
from datetime import datetime
from app.models import EventCollaborator, EventCollaborationInvitation
from app.schemas.collaborator import (
    EventCollaborationInvitationCreate,
    EventCollaborationInvitationRead,
    EventCollaborationInvitationWithDetailsRead,
    EventCollaboratorRead,
    AcceptInvitationResponse,
    ConflictingEventInfo,
    ReportConflictResponse,
    ConflictReportRead,
)
from app.models import Event, User, Calendar
from app.core.websockets import manager

class CollaboratorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def invite(self, data: EventCollaborationInvitationCreate) -> EventCollaborationInvitationRead:
        invitation = EventCollaborationInvitation(**data.dict())
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return EventCollaborationInvitationRead.model_validate(invitation)

    async def _get_invitation(self, invitation_id: UUID) -> EventCollaborationInvitation:
        q = await self.db.execute(
            select(EventCollaborationInvitation).where(EventCollaborationInvitation.id == invitation_id)
        )
        invitation = q.scalar_one_or_none()
        if not invitation or invitation.status != "pending":
            raise Exception("Invalid or already handled invitation")
        return invitation

    async def _get_invitee_conflicts(self, invitee_id: UUID, collab_event: Event) -> List[Event]:
        """Find invitee's events that overlap with the collaboration event."""
        # Get all calendars for the invitee
        cal_q = await self.db.execute(
            select(Calendar.id).where(Calendar.user_id == invitee_id)
        )
        calendar_ids = [cid for (cid,) in cal_q.all()]
        if not calendar_ids:
            return []

        # Find events in those calendars that overlap with the collab event
        events_q = await self.db.execute(
            select(Event).where(
                and_(
                    Event.calendar_id.in_(calendar_ids),
                    Event.status != "cancelled",
                    Event.start_time < collab_event.end_time,
                    Event.end_time > collab_event.start_time,
                )
            )
        )
        return list(events_q.scalars().all())

    async def accept_invitation(self, invitation_id: UUID, force: bool = False) -> AcceptInvitationResponse:
        """Accept an invitation with conflict checking.
        
        If force=False and conflicts exist, returns conflict info instead of accepting.
        If force=True, accepts regardless of conflicts.
        """
        invitation = await self._get_invitation(invitation_id)

        # Get the collaboration event
        event_q = await self.db.execute(select(Event).where(Event.id == invitation.event_id))
        collab_event = event_q.scalar_one_or_none()
        if not collab_event:
            raise Exception("Collaboration event not found")

        # Check for conflicts unless force-accepting
        if not force:
            conflicts = await self._get_invitee_conflicts(invitation.invitee_id, collab_event)
            if conflicts:
                conflict_infos = [
                    ConflictingEventInfo(
                        event_id=ev.id,
                        title=ev.title,
                        start_time=ev.start_time.isoformat(),
                        end_time=ev.end_time.isoformat(),
                        calendar_id=ev.calendar_id,
                    )
                    for ev in conflicts
                ]
                return AcceptInvitationResponse(
                    status="conflict",
                    has_conflict=True,
                    conflicts=conflict_infos,
                    collab_event_title=collab_event.title,
                    collab_event_start=collab_event.start_time.isoformat(),
                    collab_event_end=collab_event.end_time.isoformat(),
                    invitation_id=invitation.id,
                    message=f"You have {len(conflicts)} conflicting event(s) during this time.",
                )

        # No conflicts or force-accepting: proceed
        invitation.status = "accepted"
        invitation.responded_at = datetime.utcnow()
        collaborator = EventCollaborator(
            event_id=invitation.event_id,
            user_id=invitation.invitee_id,
            role="editor",
        )
        self.db.add(collaborator)
        await self.db.commit()
        await self.db.refresh(collaborator)
        await self.db.refresh(invitation)
        return AcceptInvitationResponse(
            status="accepted",
            collaborator=EventCollaboratorRead.model_validate(collaborator),
        )

    async def report_conflict(self, invitation_id: UUID, message: Optional[str] = None) -> ReportConflictResponse:
        """Invitee reports conflict back to event creator.
        
        The invitation status is set to 'conflict_reported' and the message is stored in DB.
        The creator can then fetch conflict reports via the API.
        """
        invitation = await self._get_invitation(invitation_id)
        
        # Get invitee username for the stored message
        invitee_q = await self.db.execute(select(User.username).where(User.id == invitation.invitee_id))
        invitee_username = invitee_q.scalar_one_or_none() or "A user"

        event_q = await self.db.execute(select(Event.title).where(Event.id == invitation.event_id))
        event_title = event_q.scalar_one_or_none() or "an event"
        
        invitation.status = "conflict_reported"
        invitation.responded_at = datetime.utcnow()
        invitation.conflict_message = message or f"{invitee_username} reported a scheduling conflict for '{event_title}'. Please create a new event at a different time."
        await self.db.commit()
        await self.db.refresh(invitation)

        # Also send WebSocket notification for real-time update
        try:
            await manager.send_personal_message(
                {"type": "conflict_reported"},
                invitation.inviter_id,
            )
        except Exception:
            pass  # WebSocket notification is best-effort

        return ReportConflictResponse(
            status="reported",
            message="Conflict reported to the event creator. They will need to create a new event at a different time.",
        )

    async def list_conflict_reports(self, user_id: UUID) -> List[ConflictReportRead]:
        """Get conflict reports for events created by this user."""
        query = (
            select(EventCollaborationInvitation, Event.title, User.username)
            .join(Event, Event.id == EventCollaborationInvitation.event_id)
            .join(User, User.id == EventCollaborationInvitation.invitee_id)
            .join(Calendar, Calendar.id == Event.calendar_id)
            .where(
                Calendar.user_id == user_id,
                EventCollaborationInvitation.status == "conflict_reported"
            )
        )
        result = await self.db.execute(query)
        rows = result.all()
        return [
            ConflictReportRead(
                invitation_id=inv.id,
                event_id=inv.event_id,
                event_title=title,
                reporter_username=username,
                message=inv.conflict_message or f"{username} reported a conflict.",
            )
            for inv, title, username in rows
        ]

    async def dismiss_conflict_report(self, invitation_id: UUID) -> None:
        """Dismiss a conflict report by changing status to 'dismissed'."""
        q = await self.db.execute(
            select(EventCollaborationInvitation).where(EventCollaborationInvitation.id == invitation_id)
        )
        invitation = q.scalar_one_or_none()
        if invitation and invitation.status == "conflict_reported":
            invitation.status = "dismissed"
            await self.db.commit()

    async def decline_invitation(self, invitation_id: UUID) -> EventCollaborationInvitationRead:
        q = await self.db.execute(select(EventCollaborationInvitation).where(EventCollaborationInvitation.id == invitation_id))
        invitation = q.scalar_one_or_none()
        if not invitation or invitation.status != "pending":
            raise Exception("Invalid or already handled invitation")
        invitation.status = "declined"
        invitation.responded_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(invitation)
        return EventCollaborationInvitationRead.model_validate(invitation)

    async def list_event_collaborators(self, event_id: UUID) -> List[EventCollaboratorRead]:
        q = await self.db.execute(select(EventCollaborator).where(EventCollaborator.event_id == event_id))
        return [EventCollaboratorRead.model_validate(row) for row in q.scalars().all()]

    async def list_user_invitations(self, user_id: UUID) -> List[EventCollaborationInvitationWithDetailsRead]:
        query = (
            select(EventCollaborationInvitation, Event.title, Event.start_time, User.username)
            .join(Event, Event.id == EventCollaborationInvitation.event_id)
            .join(User, User.id == EventCollaborationInvitation.inviter_id)
            .where(
                EventCollaborationInvitation.invitee_id == user_id,
                EventCollaborationInvitation.status == "pending"
            )
        )
        result = await self.db.execute(query)
        rows = result.all()
        return [
            EventCollaborationInvitationWithDetailsRead(
                **EventCollaborationInvitationRead.model_validate(inv).model_dump(),
                event_title=title,
                event_date=start_time.isoformat(),
                inviter_username=username
            )
            for inv, title, start_time, username in rows
        ]
