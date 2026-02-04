# apps/backend/app/agent/executor.py
"""Intent executor - executes parsed intents against backend services."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.config import get_agent_settings
from app.agent.exceptions import ExecutionError, UnsupportedIntentError
from app.agent.schemas import (
    Intent,
    IntentType,
    ExecuteRequest,
    ExecuteResponse,
    CreateEventData,
    FindFreeSlotsData,
    MoveEventData,
    DeleteEventData,
)


class IntentExecutor:
    """Executes parsed intents by calling appropriate backend services."""

    SUPPORTED_INTENTS = [
        IntentType.CREATE_EVENT,
        IntentType.FIND_FREE_SLOTS,
        IntentType.MOVE_EVENT,
        IntentType.DELETE_EVENT,
    ]

    def __init__(self, db: Optional[AsyncSession] = None):
        """Initialize executor.

        Args:
            db: Database session for operations
        """
        self.db = db
        self.settings = get_agent_settings()
        # Lazy import to avoid circular dependencies
        self._prolog_client = None

    @property
    def prolog_client(self):
        """Lazy load prolog client."""
        if self._prolog_client is None:
            from app.integrations.prolog_client import get_prolog_client
            self._prolog_client = get_prolog_client()
        return self._prolog_client

    async def execute(self, request: ExecuteRequest) -> ExecuteResponse:
        """Execute an intent.

        Args:
            request: Execution request with intent and context

        Returns:
            ExecuteResponse with result or error
        """
        intent = request.intent
        intent_type = IntentType(intent.intent_type)

        # Validate intent type
        if intent_type not in self.SUPPORTED_INTENTS:
            raise UnsupportedIntentError(
                intent_type=intent_type.value,
                supported_types=[t.value for t in self.SUPPORTED_INTENTS],
            )

        # Check confidence threshold
        if intent.confidence < self.settings.agent_default_confidence_threshold:
            return ExecuteResponse(
                success=False,
                error="Low confidence intent",
                message=intent.clarification_question or "Could you please clarify your request?",
            )

        # Route to appropriate handler
        try:
            handler_map = {
                IntentType.CREATE_EVENT: self._execute_create_event,
                IntentType.FIND_FREE_SLOTS: self._execute_find_free_slots,
                IntentType.MOVE_EVENT: self._execute_move_event,
                IntentType.DELETE_EVENT: self._execute_delete_event,
            }

            handler = handler_map.get(intent_type)
            if handler:
                return await handler(intent, request)
            else:
                return ExecuteResponse(
                    success=False,
                    error=f"No handler for intent type: {intent_type.value}",
                )

        except ExecutionError as e:
            return ExecuteResponse(
                success=False,
                error=e.message,
                result=e.details,
            )
        except Exception as e:
            return ExecuteResponse(
                success=False,
                error=f"Execution failed: {str(e)}",
            )

    async def _execute_create_event(
        self,
        intent: Intent,
        request: ExecuteRequest,
    ) -> ExecuteResponse:
        """Execute create_event intent."""
        if not intent.data:
            return ExecuteResponse(
                success=False,
                error="No event data provided",
                message="What event would you like to create?",
            )

        try:
            data = CreateEventData(**intent.data)
        except Exception as e:
            return ExecuteResponse(
                success=False,
                error=f"Invalid event data: {str(e)}",
            )

        # Parse datetime
        start_dt = datetime.strptime(f"{data.date} {data.start_time}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{data.date} {data.end_time}", "%Y-%m-%d %H:%M")

        # Validate with Prolog (check for conflicts)
        prolog_result = await self._check_prolog_constraints(
            "check_overlap",
            calendar_id=str(request.calendar_id),
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
        )

        if request.dry_run:
            return ExecuteResponse(
                success=True,
                result={
                    "action": "create_event",
                    "dry_run": True,
                    "event_data": data.model_dump(),
                    "would_create": {
                        "title": data.title,
                        "start_at": start_dt.isoformat(),
                        "end_at": end_dt.isoformat(),
                        "location": data.location,
                    },
                },
                message=f"Would create event: {data.title}",
                prolog_validation=prolog_result,
            )

        # Actual creation would call the events service
        # For now, return a stub response
        return ExecuteResponse(
            success=True,
            result={
                "action": "create_event",
                "event_data": data.model_dump(),
                "note": "Event creation would be performed here via events service",
            },
            message=f"Event '{data.title}' would be created on {data.date} from {data.start_time} to {data.end_time}",
            prolog_validation=prolog_result,
        )

    async def _execute_find_free_slots(
        self,
        intent: Intent,
        request: ExecuteRequest,
    ) -> ExecuteResponse:
        """Execute find_free_slots intent."""
        if not intent.data:
            return ExecuteResponse(
                success=False,
                error="No search criteria provided",
                message="What date range would you like to search?",
            )

        try:
            data = FindFreeSlotsData(**intent.data)
        except Exception as e:
            return ExecuteResponse(
                success=False,
                error=f"Invalid search data: {str(e)}",
            )

        # Query Prolog for free slots
        prolog_result = await self._query_prolog_free_slots(
            calendar_id=str(request.calendar_id),
            start_date=data.date_range.start_date,
            end_date=data.date_range.end_date,
            duration_minutes=data.duration_minutes,
        )

        return ExecuteResponse(
            success=True,
            result={
                "action": "find_free_slots",
                "search_criteria": data.model_dump(),
                "note": "Free slots query would be performed via availability service",
            },
            message=f"Searching for {data.duration_minutes}-minute slots from {data.date_range.start_date} to {data.date_range.end_date}",
            prolog_validation=prolog_result,
        )

    async def _execute_move_event(
        self,
        intent: Intent,
        request: ExecuteRequest,
    ) -> ExecuteResponse:
        """Execute move_event intent."""
        if not intent.data:
            return ExecuteResponse(
                success=False,
                error="No move data provided",
                message="Which event would you like to move?",
            )

        try:
            data = MoveEventData(**intent.data)
        except Exception as e:
            return ExecuteResponse(
                success=False,
                error=f"Invalid move data: {str(e)}",
            )

        # Validate new timing with Prolog
        new_start = datetime.strptime(f"{data.new_date} {data.new_start_time}", "%Y-%m-%d %H:%M")
        new_end = datetime.strptime(f"{data.new_date} {data.new_end_time}", "%Y-%m-%d %H:%M")

        prolog_result = await self._check_prolog_constraints(
            "check_overlap",
            calendar_id=str(request.calendar_id),
            start_time=new_start.isoformat(),
            end_time=new_end.isoformat(),
            exclude_event_id=data.event_id,
        )

        if request.dry_run:
            return ExecuteResponse(
                success=True,
                result={
                    "action": "move_event",
                    "dry_run": True,
                    "move_data": data.model_dump(),
                },
                message=f"Would move event to {data.new_date} at {data.new_start_time}",
                prolog_validation=prolog_result,
            )

        return ExecuteResponse(
            success=True,
            result={
                "action": "move_event",
                "move_data": data.model_dump(),
                "note": "Event move would be performed via events service",
            },
            message=f"Event would be moved to {data.new_date} from {data.new_start_time} to {data.new_end_time}",
            prolog_validation=prolog_result,
        )

    async def _execute_delete_event(
        self,
        intent: Intent,
        request: ExecuteRequest,
    ) -> ExecuteResponse:
        """Execute delete_event intent."""
        if not intent.data:
            return ExecuteResponse(
                success=False,
                error="No deletion target provided",
                message="Which event would you like to delete?",
            )

        try:
            data = DeleteEventData(**intent.data)
        except Exception as e:
            return ExecuteResponse(
                success=False,
                error=f"Invalid delete data: {str(e)}",
            )

        if request.dry_run:
            return ExecuteResponse(
                success=True,
                result={
                    "action": "delete_event",
                    "dry_run": True,
                    "delete_data": data.model_dump(),
                },
                message=f"Would delete event: {data.event_id or data.title}",
            )

        return ExecuteResponse(
            success=True,
            result={
                "action": "delete_event",
                "delete_data": data.model_dump(),
                "note": "Event deletion would be performed via events service",
            },
            message=f"Event '{data.event_id or data.title}' would be deleted",
        )

    async def _check_prolog_constraints(
        self,
        constraint_type: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Check constraints using Prolog.

        Args:
            constraint_type: Type of constraint to check
            **kwargs: Constraint parameters

        Returns:
            Prolog validation result
        """
        try:
            result = await self.prolog_client.query(
                f"{constraint_type}({', '.join(f'{k}={v}' for k, v in kwargs.items())})"
            )
            return {
                "checked": True,
                "constraint": constraint_type,
                "result": result,
                "conflicts": [],
            }
        except Exception as e:
            return {
                "checked": False,
                "error": str(e),
                "note": "Prolog validation skipped due to error",
            }

    async def _query_prolog_free_slots(
        self,
        calendar_id: str,
        start_date: str,
        end_date: str,
        duration_minutes: int,
    ) -> Dict[str, Any]:
        """Query Prolog for free time slots.

        Args:
            calendar_id: Calendar to search
            start_date: Start of search range
            end_date: End of search range
            duration_minutes: Required slot duration

        Returns:
            Prolog query result with free slots
        """
        try:
            query = f"find_free_slots('{calendar_id}', '{start_date}', '{end_date}', {duration_minutes}, Slots)"
            result = await self.prolog_client.query(query)
            return {
                "queried": True,
                "slots": result,
            }
        except Exception as e:
            return {
                "queried": False,
                "error": str(e),
                "note": "Free slots query via Prolog failed",
            }
