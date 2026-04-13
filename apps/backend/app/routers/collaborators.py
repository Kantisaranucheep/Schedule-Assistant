from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.collaborator import (
    EventCollaborationInvitationCreate,
    EventCollaborationInvitationRead,
    EventCollaboratorRead,
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

@router.post("/invitation/{invitation_id}/accept", response_model=EventCollaboratorRead)
async def accept_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CollaboratorService(db)
    return await service.accept_invitation(invitation_id)

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

@router.get("/invitations/{user_id}", response_model=List[EventCollaborationInvitationRead])
async def list_user_invitations(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CollaboratorService(db)
    return await service.list_user_invitations(user_id)
