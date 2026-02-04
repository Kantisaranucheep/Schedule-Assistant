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
