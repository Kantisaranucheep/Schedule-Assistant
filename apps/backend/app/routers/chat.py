"""Chat endpoint - connects frontend to LLM agent."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, IntentData, ActionResult
from app.services import ChatService, EventService
from app.agent import IntentParser, IntentExecutor, ParseRequest, ExecuteRequest, IntentType

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process chat message - parse intent and optionally execute."""
    try:
        # Validate session_id is a UUID
        try:
            session_uuid = uuid.UUID(request.session_id)
        except ValueError:
            session_uuid = uuid.uuid4()

        # Parse user message to get intent
        parser = IntentParser()
        parse_request = ParseRequest(text=request.message)
        parse_result = await parser.parse(parse_request)

        # Build response
        response = ChatResponse(reply="")

        if not parse_result.success:
            response.reply = parse_result.error or "I couldn't understand your request. Could you rephrase?"
            response.error = parse_result.error
            return response

        intent = parse_result.intent
        if not intent:
            response.reply = "I'm not sure what you'd like me to do. Could you be more specific?"
            return response

        # Include intent in response
        response.intent = IntentData(
            intent=intent.intent_type.value if hasattr(intent.intent_type, 'value') else str(intent.intent_type),
            params=intent.data or {},
        )

        # If low confidence, ask for clarification
        if intent.confidence < 0.7:
            response.reply = intent.clarification_question or "Could you provide more details?"
            return response

        # If execute_intent is False, just return the parsed intent
        if not request.execute_intent:
            response.reply = f"I understood your request: {intent.intent_type}"
            return response

        # Execute the intent
        calendar_id = request.calendar_id or "00000000-0000-0000-0000-000000000001"
        user_id = request.user_id or "00000000-0000-0000-0000-000000000001"

        try:
            calendar_uuid = uuid.UUID(calendar_id)
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            response.reply = "Invalid calendar or user ID."
            response.error = "Invalid UUID format"
            return response

        executor = IntentExecutor(db=db)
        execute_request = ExecuteRequest(
            intent=intent,
            calendar_id=calendar_uuid,
            user_id=user_uuid,
            dry_run=False,
        )

        # Handle different intent types with actual DB operations
        intent_type = IntentType(intent.intent_type) if isinstance(intent.intent_type, str) else intent.intent_type
        
        # Get timezone from request
        user_timezone = request.timezone or "Asia/Bangkok"
        
        if intent_type == IntentType.CREATE_EVENT:
            # Add timezone to intent data for proper handling
            intent_data = intent.data or {}
            intent_data["timezone"] = user_timezone
            result = await _handle_create_event(db, calendar_uuid, intent_data)
        elif intent_type == IntentType.DELETE_EVENT:
            result = await _handle_delete_event(db, calendar_uuid, intent.data or {})
        elif intent_type == IntentType.MOVE_EVENT:
            # Add timezone to intent data for proper handling
            intent_data = intent.data or {}
            intent_data["timezone"] = user_timezone
            result = await _handle_move_event(db, calendar_uuid, intent_data)
        elif intent_type == IntentType.FIND_FREE_SLOTS:
            result = await _handle_find_free_slots(db, calendar_uuid, user_uuid, intent.data or {})
        else:
            # Fallback to executor for unknown types
            exec_result = await executor.execute(execute_request)
            result = ActionResult(
                success=exec_result.success,
                message=exec_result.message,
                error=exec_result.error,
            )

        response.action_result = result
        response.reply = result.message or ("Done!" if result.success else "Sorry, something went wrong.")

        # Store chat messages if we have valid UUIDs
        try:
            chat_service = ChatService(db)
            await chat_service.get_or_create_session(session_uuid, user_uuid)
            await chat_service.add_message(session_uuid, "user", request.message)
            await chat_service.add_message(session_uuid, "agent", response.reply)
        except Exception:
            # Don't fail the request if chat logging fails
            pass

        return response

    except Exception as e:
        return ChatResponse(
            reply="Sorry, an error occurred. Please try again.",
            error=str(e),
        )


async def _handle_create_event(
    db: AsyncSession,
    calendar_id: uuid.UUID,
    data: dict,
) -> ActionResult:
    """Handle create_event intent."""
    from datetime import datetime, timezone as dt_timezone
    from zoneinfo import ZoneInfo
    from app.schemas import EventCreate
    
    try:
        # Parse datetime from intent data
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        start_time = data.get("start_time", "09:00")
        end_time = data.get("end_time", "10:00")
        
        # Get user's timezone - default to Asia/Bangkok if not provided
        user_timezone = data.get("timezone", "Asia/Bangkok")
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("Asia/Bangkok")
        
        # Parse as naive datetime first, then localize to user's timezone
        naive_start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        naive_end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
        
        # Make timezone-aware in user's local timezone
        start_dt = naive_start.replace(tzinfo=tz)
        end_dt = naive_end.replace(tzinfo=tz)
        
        event_service = EventService(db)
        
        # Check for conflicts
        conflicts = await event_service.check_conflicts(calendar_id, start_dt, end_dt)
        if conflicts:
            return ActionResult(
                success=False,
                message=f"Conflict with existing event: {conflicts[0].title}",
                error="scheduling_conflict",
            )
        
        # Create the event
        event_data = EventCreate(
            calendar_id=calendar_id,
            title=data.get("title", "New Event"),
            start_time=start_dt,
            end_time=end_dt,
            location=data.get("location"),
            notes=data.get("notes"),
            color=data.get("color", "#3B82F6"),
        )
        
        event = await event_service.create(event_data)
        
        return ActionResult(
            success=True,
            message=f"Created event '{event.title}' on {date} from {start_time} to {end_time}",
            event={
                "id": str(event.id),
                "title": event.title,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
            },
        )
    except Exception as e:
        return ActionResult(
            success=False,
            message=f"Failed to create event: {str(e)}",
            error=str(e),
        )


async def _handle_delete_event(
    db: AsyncSession,
    calendar_id: uuid.UUID,
    data: dict,
) -> ActionResult:
    """Handle delete_event intent."""
    from datetime import datetime
    
    try:
        event_service = EventService(db)
        
        event_id = data.get("event_id")
        if event_id:
            try:
                event_uuid = uuid.UUID(event_id)
                deleted = await event_service.delete(event_uuid, soft=True)
                if deleted:
                    return ActionResult(success=True, message="Event deleted successfully")
                return ActionResult(success=False, message="Event not found", error="not_found")
            except ValueError:
                pass
        
        # Try to find by title and date
        title = data.get("title")
        date_str = data.get("date")
        if title and date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                event = await event_service.find_by_title_and_date(calendar_id, title, date)
                if event:
                    await event_service.delete(event.id, soft=True)
                    return ActionResult(success=True, message=f"Deleted event '{event.title}'")
            except Exception:
                pass
        
        return ActionResult(success=False, message="Could not find the event to delete", error="not_found")
        
    except Exception as e:
        return ActionResult(success=False, message=f"Failed to delete event: {str(e)}", error=str(e))


async def _handle_move_event(
    db: AsyncSession,
    calendar_id: uuid.UUID,
    data: dict,
) -> ActionResult:
    """Handle move_event intent."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app.schemas import EventUpdate
    
    try:
        event_service = EventService(db)
        
        # Find the event
        event = None
        event_id = data.get("event_id")
        if event_id:
            try:
                event = await event_service.get(uuid.UUID(event_id))
            except ValueError:
                pass
        
        if not event:
            title = data.get("title") or data.get("original_title")
            date_str = data.get("original_date") or data.get("date")
            if title and date_str:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    event = await event_service.find_by_title_and_date(calendar_id, title, date)
                except Exception:
                    pass
        
        if not event:
            return ActionResult(success=False, message="Could not find the event to move", error="not_found")
        
        # Get user's timezone - default to Asia/Bangkok if not provided
        user_timezone = data.get("timezone", "Asia/Bangkok")
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("Asia/Bangkok")
        
        # Parse new timing
        new_date = data.get("new_date", datetime.now().strftime("%Y-%m-%d"))
        new_start = data.get("new_start_time", "09:00")
        new_end = data.get("new_end_time", "10:00")
        
        # Parse as naive datetime first, then localize to user's timezone
        naive_start = datetime.strptime(f"{new_date} {new_start}", "%Y-%m-%d %H:%M")
        naive_end = datetime.strptime(f"{new_date} {new_end}", "%Y-%m-%d %H:%M")
        
        # Make timezone-aware in user's local timezone
        new_start_dt = naive_start.replace(tzinfo=tz)
        new_end_dt = naive_end.replace(tzinfo=tz)
        
        # Check for conflicts
        conflicts = await event_service.check_conflicts(
            calendar_id, new_start_dt, new_end_dt, exclude_event_id=event.id
        )
        if conflicts:
            return ActionResult(
                success=False,
                message=f"Conflict with existing event: {conflicts[0].title}",
                error="scheduling_conflict",
            )
        
        # Update the event
        update_data = EventUpdate(start_time=new_start_dt, end_time=new_end_dt)
        updated = await event_service.update(event.id, update_data)
        
        return ActionResult(
            success=True,
            message=f"Moved event '{updated.title}' to {new_date} from {new_start} to {new_end}",
            event={
                "id": str(updated.id),
                "title": updated.title,
                "start_time": updated.start_time.isoformat(),
                "end_time": updated.end_time.isoformat(),
            },
        )
        
    except Exception as e:
        return ActionResult(success=False, message=f"Failed to move event: {str(e)}", error=str(e))


async def _handle_find_free_slots(
    db: AsyncSession,
    calendar_id: uuid.UUID,
    user_id: uuid.UUID,
    data: dict,
) -> ActionResult:
    """Handle find_free_slots intent."""
    from datetime import datetime
    from app.services import AvailabilityService
    
    try:
        availability_service = AvailabilityService(db)
        
        # Parse date range
        date_range = data.get("date_range", {})
        start_date_str = date_range.get("start_date", datetime.now().strftime("%Y-%m-%d"))
        end_date_str = date_range.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        duration = data.get("duration_minutes", 60)
        
        slots = await availability_service.find_free_slots(
            calendar_id, start_date, end_date, duration
        )
        
        if not slots:
            return ActionResult(
                success=True,
                message=f"No {duration}-minute free slots found between {start_date_str} and {end_date_str}",
                events=[],
            )
        
        # Format slots for response
        formatted_slots = []
        for slot in slots[:5]:  # Limit to 5 slots
            formatted_slots.append({
                "start": slot["start"],
                "end": slot["end"],
                "duration_minutes": slot["duration_minutes"],
            })
        
        return ActionResult(
            success=True,
            message=f"Found {len(slots)} free slots. Here are some options:",
            events=formatted_slots,
        )
        
    except Exception as e:
        return ActionResult(success=False, message=f"Failed to find free slots: {str(e)}", error=str(e))


@router.get("/health")
async def agent_health():
    """Check agent/LLM availability."""
    try:
        parser = IntentParser()
        llm_available = await parser.check_llm_available()
        return {
            "status": "healthy" if llm_available else "degraded",
            "llm_available": llm_available,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
