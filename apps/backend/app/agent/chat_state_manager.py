"""Chat conversation state management - tracks state and session data in-memory."""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field


class ConversationStateEnum(str, Enum):
    """Conversation states during chat flow."""
    INITIAL = "initial"
    CHECK_CONFLICT = "check_conflict"
    STRATEGY_CHOICE = "strategy_choice"
    PREFERENCE_SELECT = "preference_select"
    SELECTING_OPTION = "selecting_option"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ChatConversationState:
    """In-memory conversation state for a single chat session."""

    session_id: uuid.UUID
    user_id: uuid.UUID
    calendar_id: uuid.UUID
    current_state: ConversationStateEnum
    intent_data: Dict[str, Any] = field(default_factory=dict)  # Accumulated intent data
    conflict_info: Dict[str, Any] = field(default_factory=dict)  # Conflicting event info
    options: List[Dict[str, Any]] = field(default_factory=list)  # Current available options
    messages: List[Dict[str, str]] = field(default_factory=list)  # In-memory message history
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def is_active(self, timeout_minutes: int = 30) -> bool:
        """Check if session is still active (not timed out)."""
        elapsed = datetime.now() - self.last_activity
        return elapsed < timedelta(minutes=timeout_minutes)

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def add_message(self, role: str, text: str) -> None:
        """Add message to in-memory history."""
        self.messages.append({
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat(),
        })

    def set_conflict_info(self, event_id: str, title: str, start: str, end: str) -> None:
        """Store conflicting event information."""
        self.conflict_info = {
            "event_id": event_id,
            "title": title,
            "start_time": start,
            "end_time": end,
        }

    def set_options(self, options: List[Dict[str, Any]]) -> None:
        """Store available options for user selection."""
        self.options = options


class ChatStateManager:
    """Singleton managing all active chat sessions."""

    _instance: Optional['ChatStateManager'] = None
    _sessions: Dict[uuid.UUID, ChatConversationState] = {}
    _timeout_minutes: int = 30

    def __new__(cls) -> 'ChatStateManager':
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ChatStateManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls, timeout_minutes: int = 30) -> 'ChatStateManager':
        """Get singleton instance."""
        instance = cls()
        instance._timeout_minutes = timeout_minutes
        return instance

    def create_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
    ) -> ChatConversationState:
        """Create new chat session."""
        state = ChatConversationState(
            session_id=session_id,
            user_id=user_id,
            calendar_id=calendar_id,
            current_state=ConversationStateEnum.INITIAL,
        )
        self._sessions[session_id] = state
        return state

    def get_session(self, session_id: uuid.UUID) -> Optional[ChatConversationState]:
        """Get session by ID, return None if not found or timed out."""
        session = self._sessions.get(session_id)

        if session is None:
            return None

        # Check if session has timed out
        if not session.is_active(self._timeout_minutes):
            # Auto-cleanup expired session
            self.delete_session(session_id)
            return None

        return session

    def get_or_create_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
    ) -> ChatConversationState:
        """Get existing session or create new one."""
        session = self.get_session(session_id)

        if session is None:
            session = self.create_session(session_id, user_id, calendar_id)

        session.touch()
        return session

    def update_state(
        self,
        session_id: uuid.UUID,
        new_state: ConversationStateEnum,
    ) -> Optional[ChatConversationState]:
        """Transition session to new state."""
        session = self.get_session(session_id)

        if session is None:
            return None

        session.current_state = new_state
        session.touch()
        return session

    def delete_session(self, session_id: uuid.UUID) -> bool:
        """Delete session (cleanup on close or timeout)."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        text: str,
    ) -> Optional[ChatConversationState]:
        """Add message to session's in-memory history."""
        session = self.get_session(session_id)

        if session is None:
            return None

        session.add_message(role, text)
        session.touch()
        return session

    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions. Call periodically."""
        expired_sessions = [
            sid for sid, session in self._sessions.items()
            if not session.is_active(self._timeout_minutes)
        ]

        for sid in expired_sessions:
            del self._sessions[sid]

        return len(expired_sessions)

    def get_all_sessions(self) -> Dict[uuid.UUID, ChatConversationState]:
        """Get all active sessions (for debugging/monitoring)."""
        return {
            sid: session for sid, session in self._sessions.items()
            if session.is_active(self._timeout_minutes)
        }

    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self.get_all_sessions())


# Singleton instance
_state_manager: Optional[ChatStateManager] = None


def get_chat_state_manager(timeout_minutes: int = 30) -> ChatStateManager:
    """Get or create chat state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = ChatStateManager(timeout_minutes)
    return _state_manager
