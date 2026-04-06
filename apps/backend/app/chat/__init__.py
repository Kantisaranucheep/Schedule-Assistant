# apps/backend/app/chat/__init__.py
"""
Chat Agent Module - State-based conversational AI for schedule management.

This module provides a complete chat agent that:
- Uses Ollama LLM to parse natural language into structured intents
- Uses Prolog for conflict detection and time slot finding
- Implements a state machine for multi-turn conversations
- Handles event CRUD operations through natural conversation
"""

from app.chat.states import AgentState, StateTransition
from app.chat.schemas import (
    ChatMessageRequest,
    ChatAgentResponse,
    ChoiceOption,
    AgentMessage,
    SessionState,
)

__all__ = [
    "AgentState",
    "StateTransition",
    "ChatMessageRequest",
    "ChatAgentResponse",
    "ChoiceOption",
    "AgentMessage",
    "SessionState",
]
