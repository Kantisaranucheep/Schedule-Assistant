# apps/backend/app/routers/chat_endpoint.py
"""Simple chat endpoint connecting frontend directly to LLM_Engine."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from app.agent.LLM_Engine import LLM_Engine

router = APIRouter(prefix="/agent", tags=["agent-chat"])


class ChatRequest(BaseModel):
    message: str
    current_datetime: str  # ISO 8601 string from frontend


class ChatResponse(BaseModel):
    reply: str
    intent_data: Dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """
    Process a user message using LLM_Engine.
    
    Args:
        request: Contains user 'message' and 'current_datetime'
        
    Returns:
        Structured response with 'reply' text and raw 'intent_data'
    """
    try:
        # Initialize engine
        engine = LLM_Engine()
        
        # Parse intent
        intent = engine.parse(request.message, request.current_datetime)
        
        # Generate reply
        reply = engine.generate_reply(intent)
        
        return ChatResponse(
            reply=reply,
            intent_data=intent
        )
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        # LLM returned invalid JSON
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # General server error
        raise HTTPException(status_code=500, detail=str(e))
