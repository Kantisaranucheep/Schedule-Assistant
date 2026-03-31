# apps/backend/app/routers/agent.py
"""Agent API routes for intent parsing and execution."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.agent.parser import IntentParser
from app.agent.executor import IntentExecutor
from app.agent.schemas import (
    ParseRequest,
    ParseResponse,
    ExecuteRequest,
    ExecuteResponse,
    Intent,
)
from app.agent.exceptions import AgentError, UnsupportedIntentError
from app.agent.config import get_agent_settings
import httpx
import json
import re
from datetime import datetime, timedelta
import io
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import ollama

# In-memory store for chat sessions prototype
conversations: Dict[str, List[Dict[str, str]]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    current_datetime: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    error: Optional[str] = None
    intent_json: Optional[Dict[str, Any]] = None

class TTSRequest(BaseModel):
    text: str

SYSTEM_PROMPT = """You are a helpful assistant that converts user requests into structured actions.

Your job:
1. Understand the user's intent from their message.
2. If the message is just casual conversation (like "hi", "hello", "how are you"), respond conversationally without any JSON.
3. If the message seems to be requesting an action (like creating an event, setting a reminder, etc.), and any required information is MISSING or AMBIGUOUS, ask a clear follow-up question to get the missing details. Do NOT guess or make up information.
4. Once you have ALL required information for an action, output the structured intent as a JSON block wrapped in ```json ... ``` markers, followed by a short confirmation message.

SUPPORTED INTENTS:

1. create_event
   Required fields: title (string), date (YYYY-MM-DD), time (HH:MM)
   Optional fields: location (string), description (string)

2. set_reminder
   Required fields: title (string), datetime (YYYY-MM-DDTHH:MM)
   Optional fields: notes (string)

3. send_message
   Required fields: recipient (string), content (string)
   Optional fields: urgency ("low" | "normal" | "high")

4. create_task
   Required fields: title (string)
   Optional fields: due_date (YYYY-MM-DD), priority ("low" | "medium" | "high"), description (string)

RULES:
- Today's date context will be provided in each message.
- When the user says "tomorrow", "next Monday", etc., resolve it to an actual date.
- Always ask for missing REQUIRED fields before producing JSON.
- When asking a question, do NOT output any JSON block.
- When you have all the info, output EXACTLY ONE ```json ... ``` block with this structure:
  {
    "intent": "<intent_name>",
    "params": { ... }
  }
- Keep your conversational replies short and friendly.
"""

def extract_json(response_text: str) -> Optional[Dict[str, Any]]:
    pattern = r"```json\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if not match: return None
    json_str = match.group(1).strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

def strip_json_block(response_text: str) -> str:
    pattern = r"```json\s*\n?.*?\n?\s*```"
    cleaned = re.sub(pattern, "", response_text, flags=re.DOTALL)
    return cleaned.strip()

def _today_context() -> str:
    from datetime import datetime
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    return f"Today is {now.strftime('%A, %Y-%m-%d')}. Tomorrow is {tomorrow.strftime('%A, %Y-%m-%d')}. Current time is {now.strftime('%H:%M')}."

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/parse", response_model=ParseResponse)
async def parse_intent(
    request: ParseRequest,
    timezone: str = "Asia/Bangkok",
) -> ParseResponse:
    """Parse user text into structured intent.

    Args:
        request: ParseRequest with user text
        timezone: User's timezone for date resolution

    Returns:
        ParseResponse with parsed intent or error
    """
    parser = IntentParser()
    return await parser.parse(request, timezone=timezone)


@router.post("/execute", response_model=ExecuteResponse)
async def execute_intent(
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    """Execute a parsed intent.

    Args:
        request: ExecuteRequest with intent and context
        db: Database session

    Returns:
        ExecuteResponse with result or error
    """
    try:
        executor = IntentExecutor(db=db)
        return await executor.execute(request)
    except UnsupportedIntentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.message,
                "supported_types": e.supported_types,
            },
        )
    except AgentError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": e.message,
                "details": e.details,
            },
        )


@router.get("/health")
async def agent_health() -> dict:
    """Check agent service health including LLM availability."""
    parser = IntentParser()
    llm_available = await parser.check_llm_available()

    # Check Prolog availability
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
        "prolog_available": prolog_available,
    }


@router.post("/parse-and-execute", response_model=ExecuteResponse)
async def parse_and_execute(
    text: str,
    user_id: UUID,
    calendar_id: UUID,
    timezone: str = "Asia/Bangkok",
    dry_run: bool = False,
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    """Convenience endpoint to parse and execute in one call.

    Args:
        text: User's natural language request
        user_id: User ID for context
        calendar_id: Calendar ID for operations
        timezone: User's timezone
        dry_run: If true, validate but don't execute
        db: Database session

    Returns:
        ExecuteResponse with result
    """
    # Parse
    parser = IntentParser()
    parse_request = ParseRequest(text=text, user_id=user_id, calendar_id=calendar_id)
    parse_response = await parser.parse(parse_request, timezone=timezone)

    if not parse_response.success or not parse_response.intent:
        return ExecuteResponse(
            success=False,
            error=parse_response.error or "Failed to parse intent",
            result=parse_response.error_details,
        )

    # Execute
    executor = IntentExecutor(db=db)
    execute_request = ExecuteRequest(
        intent=parse_response.intent,
        user_id=user_id,
        calendar_id=calendar_id,
        dry_run=dry_run,
    )

    return await executor.execute(execute_request)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Conversational endpoint storing history in-memory and returning agent intent."""
    user_message = request.message.strip()
    session_id = request.session_id
    current_datetime = request.current_datetime or datetime.now().strftime("%Y-%m-%d %H:%M")

    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

    if session_id not in conversations:
        conversations[session_id] = []

    history = conversations[session_id]

    system_msg = {
        "role": "system",
        "content": SYSTEM_PROMPT + "\n\n" + _today_context(),
    }
    messages = [system_msg] + history + [{"role": "user", "content": user_message}]

    # Call Ollama using the library
    try:
        settings = get_agent_settings()
        response = await asyncio.to_thread(
            ollama.chat,
            model=settings.ollama_model,
            messages=messages
        )
        assistant_reply = response["message"]["content"]
    except Exception as e:
        return ChatResponse(reply="", error=f"Ollama error: {e}")

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_reply})

    try:
        intent_json = extract_json(assistant_reply)
        display_text = strip_json_block(assistant_reply) if intent_json else assistant_reply
    except Exception as e:
        # If parsing fails, just use the raw reply
        intent_json = None
        display_text = assistant_reply

    return ChatResponse(
        reply=display_text,
        error=None,
        intent_json=intent_json
    )


@router.post("/tts")
async def tts_endpoint(request: TTSRequest):
    """Text-to-speech endpoint returning mp3 streams via gTTS."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    try:
        from gtts import gTTS
        audio_io = io.BytesIO()
        gTTS(text=text, lang="en").write_to_fp(audio_io)
        audio_io.seek(0)
        return StreamingResponse(audio_io, media_type="audio/mpeg")
    except ImportError:
        raise HTTPException(status_code=500, detail="gTTS is not installed or available.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")
