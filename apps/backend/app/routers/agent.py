# apps/backend/app/routers/agent.py
"""Agent API routes - unified chat endpoint with LLM, Prolog, and database integration."""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import ollama

from app.core.db import get_db
from app.agent.config import get_agent_settings
from app.services.event_service import EventService


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    """Chat request from frontend."""
    message: str
    session_id: str = "default"
    calendar_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    execute_intent: bool = True  # If True, execute detected intents


class ChatResponse(BaseModel):
    """Chat response to frontend."""
    reply: str
    intent: Optional[Dict[str, Any]] = None
    action_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# System Prompt for LLM
# =============================================================================

SYSTEM_PROMPT = """You are a helpful scheduling assistant that converts user requests into structured actions.

Your job:
1. Understand the user's intent from their message.
2. If the message is casual conversation (like "hi", "hello"), respond conversationally without JSON.
3. If requesting an action with MISSING required info, ask a follow-up question. Do NOT guess.
4. Once you have ALL required info, output a JSON block wrapped in ```json ... ``` markers.

SUPPORTED INTENTS:

1. create_event
   Required: title (string), date (YYYY-MM-DD), start_time (HH:MM), end_time (HH:MM)
   Optional: location (string), description (string)

2. delete_event
   Required: title (string) OR event_id (string)
   Optional: date (YYYY-MM-DD) - helps find the right event

3. move_event
   Required: title OR event_id, new_date (YYYY-MM-DD), new_start_time (HH:MM), new_end_time (HH:MM)

4. find_free_slots
   Required: date (YYYY-MM-DD) OR date_range (start_date, end_date)
   Optional: duration_minutes (default 60)

RULES:
- Today's date context is provided in each message.
- Resolve relative dates ("tomorrow", "next Monday") to actual dates.
- Ask for missing REQUIRED fields before producing JSON.
- When asking a question, do NOT output JSON.
- Output EXACTLY ONE ```json ... ``` block:
  {
    "intent": "<intent_name>",
    "params": { ... }
  }
- Keep replies short and friendly.
"""


# =============================================================================
# Helper Functions
# =============================================================================

def _get_date_context() -> str:
    """Generate current date context for LLM."""
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    return (
        f"Today is {now.strftime('%A, %Y-%m-%d')}. "
        f"Tomorrow is {tomorrow.strftime('%A, %Y-%m-%d')}. "
        f"Current time is {now.strftime('%H:%M')}."
    )


def _extract_json(response_text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM response."""
    pattern = r"```json\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def _strip_json_block(response_text: str) -> str:
    """Remove JSON block from response text."""
    pattern = r"```json\s*\n?.*?\n?\s*```"
    return re.sub(pattern, "", response_text, flags=re.DOTALL).strip()


router = APIRouter(prefix="/agent", tags=["agent"])


# =============================================================================
# Intent Execution
# =============================================================================

async def execute_intent(
    intent: Dict[str, Any],
    event_service: EventService,
    calendar_id: Optional[UUID],
) -> Dict[str, Any]:
    """Execute a parsed intent using the event service.
    
    Args:
        intent: Parsed intent with 'intent' and 'params' keys
        event_service: EventService instance
        calendar_id: Calendar UUID for operations
        
    Returns:
        Dict with execution result
    """
    intent_type = intent.get("intent", "").lower()
    params = intent.get("params", {})

    if not calendar_id:
        return {
            "success": False,
            "error": "No calendar specified. Please provide a calendar_id."
        }

    try:
        if intent_type == "create_event":
            # Parse datetime from params
            date_str = params.get("date")
            start_time = params.get("start_time")
            end_time = params.get("end_time")

            if not all([date_str, start_time, end_time]):
                return {"success": False, "error": "Missing date or time info"}

            start_at = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
            end_at = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")

            return await event_service.create_event(
                calendar_id=calendar_id,
                title=params.get("title", "Untitled Event"),
                start_at=start_at,
                end_at=end_at,
                description=params.get("description"),
                location=params.get("location"),
                created_by="agent",
            )

        elif intent_type == "delete_event":
            return await event_service.delete_event(
                event_id=UUID(params["event_id"]) if params.get("event_id") else None,
                title=params.get("title"),
                calendar_id=calendar_id,
            )

        elif intent_type == "move_event":
            # First find the event
            find_result = await event_service.find_event(
                calendar_id=calendar_id,
                title=params.get("title"),
                date=params.get("original_date"),
            )
            if not find_result.get("success"):
                return find_result

            event_id = UUID(find_result["event"]["id"])
            
            # Parse new times
            new_date = params.get("new_date")
            new_start = params.get("new_start_time")
            new_end = params.get("new_end_time")

            start_at = datetime.strptime(f"{new_date} {new_start}", "%Y-%m-%d %H:%M") if new_date and new_start else None
            end_at = datetime.strptime(f"{new_date} {new_end}", "%Y-%m-%d %H:%M") if new_date and new_end else None

            return await event_service.update_event(
                event_id=event_id,
                start_at=start_at,
                end_at=end_at,
            )

        elif intent_type == "find_free_slots":
            # Get events for the date range to show busy times
            date_str = params.get("date")
            date_range = params.get("date_range", {})
            start_date = date_str or date_range.get("start_date")
            end_date = date_range.get("end_date", start_date)

            if start_date:
                start_from = datetime.strptime(start_date, "%Y-%m-%d")
                end_to = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59)
                
                events_result = await event_service.get_events(
                    calendar_id=calendar_id,
                    start_from=start_from,
                    end_to=end_to,
                )
                
                return {
                    "success": True,
                    "message": f"Found {len(events_result.get('events', []))} events in this period",
                    "events": events_result.get("events", []),
                }

            return {"success": False, "error": "No date specified for availability search"}

        else:
            return {
                "success": False,
                "error": f"Unknown intent type: {intent_type}"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to execute intent: {str(e)}"
        }


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Main chat endpoint - processes messages through LLM, validates with Prolog, executes via DB.
    
    Flow:
    1. Send user message to LLM with context
    2. Extract intent JSON if present
    3. If execute_intent=True, execute the action
    4. Return response with results
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Empty message")

    settings = get_agent_settings()
    
    # Log incoming request for debugging
    print(f"[AGENT] Received: message='{message[:50]}...', calendar_id={request.calendar_id}, execute_intent={request.execute_intent}")
    
    # Build messages for LLM
    system_msg = {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + _get_date_context()}
    messages = [system_msg, {"role": "user", "content": message}]

    # Call Ollama
    try:
        response = await asyncio.to_thread(
            ollama.chat,
            model=settings.ollama_model,
            messages=messages
        )
        assistant_reply = response["message"]["content"]
        print(f"[AGENT] LLM response: {assistant_reply[:200]}...")
    except Exception as e:
        print(f"[AGENT] LLM error: {e}")
        return ChatResponse(reply="", error=f"LLM error: {e}")

    # Extract intent from response
    intent = _extract_json(assistant_reply)
    display_text = _strip_json_block(assistant_reply) if intent else assistant_reply
    
    print(f"[AGENT] Extracted intent: {intent}")

    # Execute intent if requested and present
    action_result = None
    if intent and request.execute_intent and request.calendar_id:
        print(f"[AGENT] Executing intent with calendar_id={request.calendar_id}")
        event_service = EventService(db)
        action_result = await execute_intent(intent, event_service, request.calendar_id)
        print(f"[AGENT] Action result: {action_result}")
        
        # Add execution result to display text
        if action_result.get("success"):
            display_text = f"{display_text}\n\n✅ {action_result.get('message', 'Action completed successfully')}"
        elif action_result.get("error"):
            display_text = f"{display_text}\n\n❌ {action_result.get('error')}"
    elif not intent:
        print("[AGENT] No intent extracted from LLM response")
    elif not request.calendar_id:
        print("[AGENT] No calendar_id provided - skipping execution")

    return ChatResponse(
        reply=display_text,
        intent=intent,
        action_result=action_result,
    )


@router.get("/health")
async def agent_health() -> dict:
    """Check agent service health including LLM and Prolog availability."""
    settings = get_agent_settings()
    
    # Check Ollama
    llm_available = False
    try:
        models = ollama.list()
        llm_available = any(settings.ollama_model in m.get("name", "") for m in models.get("models", []))
    except Exception:
        pass

    # Check Prolog
    prolog_available = False
    try:
        from app.integrations.prolog_client import get_prolog_client
        prolog_client = get_prolog_client()
        prolog_available = await prolog_client.is_available()
    except Exception:
        pass

    return {
        "status": "ok" if llm_available else "degraded",
        "llm_available": llm_available,
        "llm_model": settings.ollama_model,
        "prolog_available": prolog_available,
    }
