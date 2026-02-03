# schedule-assistant/apps/backend/app/routers/chat.py
"""Chat endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionRead,
    ChatMessageCreate,
    ChatMessageRead,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatSession:
    """Create a new chat session."""
    # Verify user exists
    user = await db.get(User, data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {data.user_id} not found",
        )

    session = ChatSession(
        user_id=data.user_id,
        title=data.title,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=List[ChatSessionRead])
async def list_sessions(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[ChatSession]:
    """List all chat sessions for a user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageRead])
async def get_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[ChatMessage]:
    """Get all messages in a chat session."""
    # Verify session exists
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    session_id: UUID,
    data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatMessage:
    """Add a message to a chat session."""
    # Verify session exists
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    message = ChatMessage(
        session_id=session_id,
        role=data.role,
        content=data.content,
        extracted_json=data.extracted_json,
        action_json=data.action_json,
        confidence=data.confidence,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message
