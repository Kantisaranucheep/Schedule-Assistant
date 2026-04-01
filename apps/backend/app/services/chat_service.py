"""Chat service - session and message management."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ChatSession, ChatMessage


class ChatService:
    """Chat session and message operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self, session_id: UUID, user_id: UUID, title: str = "New Chat"
    ) -> ChatSession:
        """Get existing session or create new one."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        session = result.scalar_one_or_none()

        if not session:
            session = ChatSession(id=session_id, user_id=user_id, title=title)
            self.db.add(session)
            await self.db.flush()
            await self.db.refresh(session)

        return session

    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Get session with messages."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(self, user_id: UUID) -> List[ChatSession]:
        """Get all sessions for a user."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def add_message(
        self, session_id: UUID, role: str, text: str
    ) -> ChatMessage:
        """Add a message to a session."""
        message = ChatMessage(session_id=session_id, role=role, text=text)
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def update_session_title(
        self, session_id: UUID, title: str
    ) -> Optional[ChatSession]:
        """Update session title."""
        session = await self.get_session(session_id)
        if not session:
            return None

        session.title = title
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session and all messages."""
        session = await self.get_session(session_id)
        if not session:
            return False

        await self.db.delete(session)
        await self.db.flush()
        return True
