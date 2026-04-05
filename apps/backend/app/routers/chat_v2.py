"""Chat v2 router - endpoints for standalone chat feature with conflict resolution."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.agent.chat_state_manager import ConversationStateEnum, get_chat_state_manager
from app.agent.chat_executor import ChatExecutor
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import ChatSessionResponse, ChatMessageResponse

router = APIRouter(prefix="/agent/chat-v2", tags=["agent-chat-v2"])


# ============================================================================
# Request/Response Schema Models
# ============================================================================


class ChatButton:
    """Interactive button in response."""

    def __init__(self, label: str, value: str):
        self.label = label
        self.value = value

    def dict(self):
        return {"label": self.label, "value": self.value}


class ChatV2SendRequest:
    """Request to send message in chat."""

    session_id: str
    user_id: str
    calendar_id: str
    message: str
    timezone: str = "Asia/Bangkok"


class ChatV2Response:
    """Response from chat."""

    reply: str
    state: str
    buttons: Optional[list] = None
    table: Optional[dict] = None
    error: Optional[str] = None

    def dict(self):
        return {
            "reply": self.reply,
            "state": self.state,
            "buttons": self.buttons,
            "table": self.table,
            "error": self.error,
        }


class ChatV2StartResponse:
    """Response when starting new chat."""

    session_id: str
    message: str
    state: str

    def dict(self):
        return {
            "session_id": self.session_id,
            "message": self.message,
            "state": self.state,
        }


class ChatV2StopResponse:
    """Response when stopping chat."""

    session_id: str
    message: str
    message_count: int

    def dict(self):
        return {
            "session_id": self.session_id,
            "message": self.message,
            "message_count": self.message_count,
        }


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/start")
async def start_chat(
    user_id: str,
    calendar_id: str,
    title: str = "New Chat",
    db: AsyncSession = Depends(get_db),
):
    """Start new chat conversation."""
    try:
        # Validate UUIDs
        try:
            user_uuid = uuid.UUID(user_id)
            calendar_uuid = uuid.UUID(calendar_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id or calendar_id format")

        # Create session ID
        session_id = uuid.uuid4()

        # Initialize in-memory state
        state_manager = get_chat_state_manager()
        state_manager.create_session(session_id, user_uuid, calendar_uuid)

        response = ChatV2StartResponse(
            session_id=str(session_id),
            message="Hi! I'm your calendar assistant. You can ask me to add, edit, remove, or list events. What would you like to do?",
            state=ConversationStateEnum.INITIAL.value,
        )

        return response.dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting chat: {str(e)}")


@router.post("/send")
async def send_message(
    session_id: str,
    user_id: str,
    calendar_id: str,
    message: str,
    timezone: str = "Asia/Bangkok",
    db: AsyncSession = Depends(get_db),
):
    """Send message in chat conversation."""
    try:
        # Validate UUIDs
        try:
            session_uuid = uuid.UUID(session_id)
            user_uuid = uuid.UUID(user_id)
            calendar_uuid = uuid.UUID(calendar_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        # Get state manager and chat executor
        state_manager = get_chat_state_manager()
        executor = ChatExecutor(db)

        # Get session state
        session = state_manager.get_session(session_uuid)
        if session is None:
            raise HTTPException(status_code=404, detail="Chat session not found or expired")

        current_state = session.current_state

        # Add user message to in-memory history
        state_manager.add_message(session_uuid, "user", message)

        # Execute message handling
        result = await executor.execute(
            session_id=session_uuid,
            user_id=user_uuid,
            calendar_id=calendar_uuid,
            current_state=current_state,
            user_message=message,
            timezone=timezone,
        )

        # Store agent reply in memory
        state_manager.add_message(session_uuid, "agent", result.get("text", ""))

        # Update session state
        new_state = result.get("state", current_state)
        state_manager.update_state(session_uuid, ConversationStateEnum(new_state))

        response = ChatV2Response()
        response.reply = result.get("text", "")
        response.state = new_state.value if hasattr(new_state, 'value') else str(new_state)
        response.buttons = result.get("buttons")
        response.table = result.get("table")
        response.error = result.get("error")

        return response.dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.post("/stop")
async def stop_chat(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Stop chat and persist conversation to database."""
    try:
        # Validate UUID
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id format")

        # Get state manager
        state_manager = get_chat_state_manager()
        session = state_manager.get_session(session_uuid)

        if session is None:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Save conversation to database
        # Create ChatSession
        db_session = ChatSession(
            id=session.session_id,
            user_id=session.user_id,
            title=f"Chat {session.created_at.strftime('%Y-%m-%d %H:%M')}",
        )
        db.add(db_session)

        # Add all messages from in-memory history
        message_count = 0
        for msg_data in session.messages:
            db_message = ChatMessage(
                session_id=session.session_id,
                role=msg_data.get("role", "user"),
                text=msg_data.get("text", ""),
            )
            db.add(db_message)
            message_count += 1

        # Commit to database
        await db.commit()

        # Delete in-memory session
        state_manager.delete_session(session_uuid)

        response = ChatV2StopResponse(
            session_id=str(session_uuid),
            message="Conversation saved. Thank you for using the calendar assistant!",
            message_count=message_count,
        )

        return response.dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping chat: {str(e)}")


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    """Get current chat status and state."""
    try:
        # Validate UUID
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id format")

        # Get state manager
        state_manager = get_chat_state_manager()
        session = state_manager.get_session(session_uuid)

        if session is None:
            raise HTTPException(status_code=404, detail="Chat session not found or expired")

        # Return status
        last_message = session.messages[-1] if session.messages else None

        return {
            "session_id": str(session_uuid),
            "current_state": session.current_state.value,
            "message_count": len(session.messages),
            "last_message": last_message.get("text") if last_message else None,
            "last_message_role": last_message.get("role") if last_message else None,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.get("/health")
async def health():
    """Health check for chat service."""
    return {
        "status": "healthy",
        "service": "chat-v2",
    }
