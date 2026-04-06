# apps/backend/app/chat/router.py
"""
Chat Agent Router - FastAPI endpoints for the chat system.

Endpoints:
- POST /chat/message - Process a user message
- POST /chat/choice - Handle button choice selection
- POST /chat/terminate - Terminate current session
- GET /chat/session - Get current session state
- GET /chat/health - Check agent health
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.chat.schemas import (
    ChatMessageRequest,
    ChatChoiceRequest,
    ChatTerminateRequest,
    ChatTerminateResponse,
    ChatAgentResponse,
    ChatSessionInfo,
    SessionState,
)
from app.chat.service import ChatAgentService
from app.chat.llm_service import LLMService
from app.chat.prolog_service import get_prolog_service


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatAgentResponse)
async def process_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a natural language message from the user.
    
    The agent will:
    1. Parse the message using LLM to extract intent
    2. Check for conflicts using Prolog
    3. Return appropriate response based on state
    
    The response may include choice buttons for user interaction.
    """
    service = ChatAgentService(db, request.timezone)
    return await service.process_message(request)


@router.post("/choice", response_model=ChatAgentResponse)
async def process_choice(
    request: ChatChoiceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a button choice selection from the user.
    
    This is used when the user clicks a choice button instead of typing.
    """
    service = ChatAgentService(db)
    return await service.process_choice(request)


@router.post("/terminate", response_model=ChatTerminateResponse)
async def terminate_session(
    request: ChatTerminateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Terminate the current chat session.
    
    This will discard all conversation data and reset the state.
    Users can terminate at any time during the conversation.
    """
    service = ChatAgentService(db)
    await service.terminate_session(request.session_id)
    
    return ChatTerminateResponse(
        session_id=request.session_id,
        terminated=True,
        message="Session terminated. All conversation data discarded."
    )


@router.get("/session/{session_id}", response_model=Optional[SessionState])
async def get_session_state(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current state of a chat session.
    
    Returns the current state, intent, event data, and conflict info if any.
    Returns null if session doesn't exist.
    """
    service = ChatAgentService(db)
    state = service.get_session_state(session_id)
    
    if state is None:
        return None
    
    return state


@router.get("/health")
async def chat_health():
    """
    Check the health of the chat agent system.
    
    Returns status of:
    - LLM (Ollama) availability
    - Prolog service availability
    """
    llm = LLMService()
    prolog = get_prolog_service()
    
    llm_available = await llm.check_available()
    prolog_available = prolog.is_available()
    
    overall_status = "healthy" if (llm_available and prolog_available) else "degraded"
    
    # If LLM is down, we can't function
    if not llm_available:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "components": {
            "llm": {
                "status": "healthy" if llm_available else "unhealthy",
                "available": llm_available,
            },
            "prolog": {
                "status": "healthy" if prolog_available else "degraded",
                "available": prolog_available,
                "note": "Python fallback available if Prolog is unavailable"
            }
        }
    }
