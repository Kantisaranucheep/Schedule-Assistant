from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.collaborator import (
    EventCollaborationInvitationCreate,
    EventCollaborationInvitationRead,
    EventCollaborationInvitationWithDetailsRead,
    EventCollaboratorRead,
    AcceptInvitationResponse,
    ForceAcceptRequest,
    ReportConflictRequest,
    ReportConflictResponse,
    ConflictReportRead,
)
from app.services.collaborator_service import CollaboratorService

router = APIRouter(prefix="/collaborators", tags=["collaborators"])

@router.post("/invite", response_model=EventCollaborationInvitationRead)
async def invite_collaborator(
    data: EventCollaborationInvitationCreate,
    db: AsyncSession = Depends(get_db),
):
    service = CollaboratorService(db)
    return await service.invite(data)

@router.post("/invitation/{invitation_id}/accept", response_model=AcceptInvitationResponse)
async def accept_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation. Returns conflict info if the invitee has overlapping events."""
    service = CollaboratorService(db)
    return await service.accept_invitation(invitation_id)

@router.post("/invitation/{invitation_id}/force-accept", response_model=AcceptInvitationResponse)
async def force_accept_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Force-accept an invitation despite conflicts (user chose to reschedule their own events)."""
    service = CollaboratorService(db)
    return await service.accept_invitation(invitation_id, force=True)

@router.post("/invitation/{invitation_id}/report-conflict", response_model=ReportConflictResponse)
async def report_conflict(
    invitation_id: UUID,
    data: ReportConflictRequest,
    db: AsyncSession = Depends(get_db),
):
    """Report a conflict back to the event creator."""
    service = CollaboratorService(db)
    return await service.report_conflict(invitation_id, data.message)

@router.post("/invitation/{invitation_id}/decline", response_model=EventCollaborationInvitationRead)
async def decline_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CollaboratorService(db)
    return await service.decline_invitation(invitation_id)

@router.get("/event/{event_id}", response_model=List[EventCollaboratorRead])
async def list_event_collaborators(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CollaboratorService(db)
    return await service.list_event_collaborators(event_id)

@router.get("/invitations/{user_id}", response_model=List[EventCollaborationInvitationWithDetailsRead])
async def list_user_invitations(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CollaboratorService(db)
    return await service.list_user_invitations(user_id)

@router.get("/conflict-reports/{user_id}", response_model=List[ConflictReportRead])
async def get_conflict_reports(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get conflict reports for events created by this user."""
    service = CollaboratorService(db)
    return await service.list_conflict_reports(user_id)

@router.post("/conflict-reports/{invitation_id}/dismiss")
async def dismiss_conflict_report(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a conflict report."""
    service = CollaboratorService(db)
    await service.dismiss_conflict_report(invitation_id)
    return {"status": "dismissed"}
