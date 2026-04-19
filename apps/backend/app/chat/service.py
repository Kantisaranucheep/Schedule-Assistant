# apps/backend/app/chat/service.py
"""
Chat Agent Service - Main state machine for the conversational AI.

This service orchestrates:
- LLM for natural language understanding
- Prolog for conflict detection and slot finding
- Event repository for database operations
- State machine for multi-turn conversations

The agent generates fixed-format responses (not LLM-generated text).
"""

import uuid
from datetime import timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.states import (
    AgentState, IntentType, PreferenceType, ResolutionType, EditFieldType,
    RescheduleStrategy,
    EventData, ConflictInfo, TimeSlot, FreeTimeRange, ExistingEvent, SessionContext
)
from app.chat.schemas import (
    ChatAgentResponse, AgentMessage, ChoiceOption, SessionState,
    ChatMessageRequest, ChatChoiceRequest
)
from app.chat.llm_service import LLMService
from app.chat.prolog_service import get_prolog_service, PrologService, RescheduleOption, AddEventResult, TimeSuggestion
from app.chat.event_repository import EventRepository
from app.core.timezone import now as tz_now


# In-memory session storage (for simplicity - not persistent)
_sessions: Dict[str, SessionContext] = {}


class ChatAgentService:
    """
    Main chat agent service implementing the state machine.
    
    State Flow:
    INIT -> [COLLECT_INFO] -> CONFIRM_CONFLICT -> CHOOSE_RESOLUTION 
         -> SELECT_PREFERENCE -> SELECT_SLOT -> CONFIRM_ACTION -> INIT
    """
    
    def __init__(self, db: AsyncSession, timezone: str = "Asia/Bangkok", user_id: str | None = None):
        self.db = db
        self.timezone = timezone
        self.llm = LLMService()
        self.prolog = get_prolog_service()
        # Parse user_id and pass to repository so events go to the correct calendar
        import uuid as _uuid
        parsed_user_id = None
        if user_id:
            try:
                parsed_user_id = _uuid.UUID(user_id)
            except ValueError:
                pass
        self.repo = EventRepository(db, timezone, user_id=parsed_user_id)
    
    def _get_session(self, session_id: str) -> SessionContext:
        """Get or create session context."""
        if session_id not in _sessions:
            _sessions[session_id] = SessionContext()
        return _sessions[session_id]
    
    def _save_session(self, session_id: str, context: SessionContext):
        """Save session context."""
        _sessions[session_id] = context
    
    def _clear_session(self, session_id: str):
        """Clear session and reset to init."""
        if session_id in _sessions:
            _sessions[session_id].reset()
    
    async def process_message(self, request: ChatMessageRequest) -> ChatAgentResponse:
        """
        Process a user message and return agent response.
        
        This is the main entry point for handling user messages.
        """
        session_id = request.session_id or str(uuid.uuid4())
        context = self._get_session(session_id)
        
        try:
            # Route based on current state
            if context.state == AgentState.INIT:
                response = await self._handle_init_state(session_id, context, request.message)
            elif context.state == AgentState.COLLECT_INFO:
                response = await self._handle_collect_info_state(session_id, context, request.message)
            elif context.state == AgentState.CONFIRM_CONFLICT:
                response = await self._handle_confirm_conflict_state(session_id, context, request.message)
            elif context.state == AgentState.CHOOSE_RESOLUTION:
                response = await self._handle_choose_resolution_state(session_id, context, request.message)
            elif context.state == AgentState.SELECT_PREFERENCE:
                response = await self._handle_select_preference_state(session_id, context, request.message)
            elif context.state == AgentState.SELECT_SLOT:
                response = await self._handle_select_slot_state(session_id, context, request.message)
            elif context.state == AgentState.SELECT_TIME_IN_RANGE:
                response = await self._handle_select_time_in_range_state(session_id, context, request.message)
            elif context.state == AgentState.CONFIRM_ACTION:
                response = await self._handle_confirm_action_state(session_id, context, request.message)
            # Edit/Remove flow states
            elif context.state == AgentState.SELECT_EVENT_DAY:
                response = await self._handle_select_event_day_state(session_id, context, request.message)
            elif context.state == AgentState.SELECT_EVENT:
                response = await self._handle_select_event_state(session_id, context, request.message)
            elif context.state == AgentState.SELECT_EDIT_FIELD:
                response = await self._handle_select_edit_field_state(session_id, context, request.message)
            elif context.state == AgentState.ENTER_EDIT_VALUE:
                response = await self._handle_enter_edit_value_state(session_id, context, request.message)
            elif context.state == AgentState.CONFIRM_EDIT:
                response = await self._handle_confirm_edit_state(session_id, context, request.message)
            elif context.state == AgentState.CONFIRM_REMOVE:
                response = await self._handle_confirm_remove_state(session_id, context, request.message)
            # Phase 3: Strategy selection for smart reschedule
            elif context.state == AgentState.SELECT_STRATEGY:
                response = await self._handle_select_strategy_state(session_id, context, request.message)
            # Phase 2: Constraint solver reschedule states
            elif context.state == AgentState.SELECT_RESCHEDULE_OPTION:
                response = await self._handle_select_reschedule_option_state(session_id, context, request.message)
            elif context.state == AgentState.CONFIRM_RESCHEDULE:
                response = await self._handle_confirm_reschedule_state(session_id, context, request.message)
            else:
                # Unknown state - reset
                context.reset()
                response = self._build_response(
                    session_id, context,
                    "Something went wrong. Please start over.",
                )
            
            self._save_session(session_id, context)
            return response
            
        except Exception as e:
            # On error, reset state
            context.reset()
            self._save_session(session_id, context)
            return self._build_response(
                session_id, context,
                f"An error occurred: {str(e)}. Please try again.",
                success=False,
                error=str(e)
            )
    
    async def process_choice(self, request: ChatChoiceRequest) -> ChatAgentResponse:
        """
        Process a button choice selection.
        
        This handles when users click choice buttons instead of typing.
        """
        context = self._get_session(request.session_id)
        
        # Convert choice to a message and process
        message_request = ChatMessageRequest(
            message=request.choice_value,
            session_id=request.session_id,
            timezone=self.timezone
        )
        
        return await self.process_message(message_request)
    
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a session and discard all data."""
        self._clear_session(session_id)
        return True
    
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """Get current session state."""
        if session_id not in _sessions:
            return None
        
        context = _sessions[session_id]
        return SessionState(
            state=context.state.value,
            intent=context.intent.value if context.intent else None,
            event_data=context.event_data.to_dict() if context.event_data else None,
            conflict_info=context.conflict_info.to_dict() if context.conflict_info else None,
        )
    
    # =========================================================================
    # State Handlers
    # =========================================================================
    
    async def _handle_init_state(
        self, 
        session_id: str, 
        context: SessionContext, 
        message: str
    ) -> ChatAgentResponse:
        """
        Handle INIT state - parse user intent.
        
        Possible transitions:
        - COLLECT_INFO: If fields are missing
        - CONFIRM_CONFLICT: If conflict detected
        - INIT: Success without conflict
        """
        # Parse intent using LLM
        success, data, error = await self.llm.parse_intent(message)
        
        if not success or data is None:
            return self._build_response(
                session_id, context,
                "I couldn't understand that. Could you rephrase? For example: 'Add a meeting tomorrow 9-10AM'",
            )
        
        intent_str = data.get("intent", "unknown")
        
        try:
            context.intent = IntentType(intent_str)
        except ValueError:
            context.intent = IntentType.UNKNOWN
        
        # Handle different intents
        if context.intent == IntentType.ADD_EVENT:
            return await self._handle_add_event_intent(session_id, context, data)
        elif context.intent == IntentType.EDIT_EVENT:
            return await self._handle_edit_event_intent(session_id, context, data)
        elif context.intent == IntentType.REMOVE_EVENT:
            return await self._handle_remove_event_intent(session_id, context, data)
        elif context.intent == IntentType.QUERY_EVENTS:
            return await self._handle_query_events_intent(session_id, context, data)
        else:
            return self._build_response(
                session_id, context,
                "I can help you add, edit, remove, or view events. What would you like to do?",
            )
    
    async def _handle_add_event_intent(
        self,
        session_id: str,
        context: SessionContext,
        data: Dict[str, Any]
    ) -> ChatAgentResponse:
        """Handle add event intent - check for conflicts."""
        event_data = data.get("event", {})
        missing_fields = data.get("missing_fields", [])
        
        # Fill in defaults for missing month/year
        now = tz_now()
        if event_data.get("month") is None:
            event_data["month"] = now.month
        if event_data.get("year") is None:
            event_data["year"] = now.year
        
        context.event_data = EventData.from_dict(event_data)
        
        # Check for missing required fields
        actual_missing = context.event_data.get_missing_fields()
        
        if actual_missing:
            # Transition to COLLECT_INFO
            context.state = AgentState.COLLECT_INFO
            context.missing_field = actual_missing[0]
            
            return self._build_response(
                session_id, context,
                self._get_field_prompt(actual_missing[0]),
            )
        
        # All fields present - check for conflicts
        return await self._check_and_handle_conflicts(session_id, context)
    
    async def _check_and_handle_conflicts(
        self,
        session_id: str,
        context: SessionContext
    ) -> ChatAgentResponse:
        """
        Check for conflicts and handle appropriately.
        
        Uses the BLACK BOX KRR approach: sends all data to Prolog's
        handle_add_event solver and lets Prolog autonomously decide
        whether the event can be added, has conflicts, or is invalid.
        
        Python does NOT call check_conflict or valid_placement directly —
        Prolog handles all reasoning internally.
        """
        event = context.event_data
        
        # Get existing events on that date
        existing_events = await self.repo.get_events_on_date(
            event.day, event.month, event.year
        )
        
        # BLACK BOX: Ask Prolog to handle the entire add-event reasoning
        result = self.prolog.handle_add_event(
            event.start_hour, event.start_minute,
            event.end_hour, event.end_minute,
            existing_events
        )
        
        if result.status == 'invalid':
            # Prolog detected constraint violations (e.g., negative duration)
            context.reset()
            violations_str = ", ".join(result.violations)
            return self._build_response(
                session_id, context,
                f"Cannot create event: constraint violations detected ({violations_str}). Please check the time and try again.",
                success=False
            )
        
        if result.status == 'conflict':
            # Prolog detected time conflicts
            conflict = result.conflicts[0]
            context.conflict_info = ConflictInfo(
                event_id=conflict["id"],
                title=conflict["title"],
                day=event.day,
                month=event.month,
                year=event.year,
                start_hour=conflict["start_hour"],
                start_minute=conflict["start_minute"],
                end_hour=conflict["end_hour"],
                end_minute=conflict["end_minute"],
            )
            
            context.state = AgentState.CONFIRM_CONFLICT
            
            conflict_time = f"{conflict['start_hour']:02d}:{conflict['start_minute']:02d} - {conflict['end_hour']:02d}:{conflict['end_minute']:02d}"
            
            return self._build_response(
                session_id, context,
                f"I found a conflict with existing event \"{conflict['title']}\" at {conflict_time} on {event.day}/{event.month}/{event.year}. Would you like help rescheduling?",
                choices=[
                    ChoiceOption(id="yes", label="Yes, help me", value="yes"),
                    ChoiceOption(id="no", label="No, cancel", value="no"),
                ],
                timeout=30
            )
        
        # result.status == 'ok' — Prolog says all good, create the event
        created = await self.repo.create_event(
            title=event.title,
            day=event.day,
            month=event.month,
            year=event.year,
            start_hour=event.start_hour,
            start_minute=event.start_minute,
            end_hour=event.end_hour,
            end_minute=event.end_minute,
            location=event.location,
            notes=event.notes,
        )
        
        context.reset()
        
        return self._build_response(
            session_id, context,
            f"✓ Event \"{event.title}\" created on {event.day}/{event.month}/{event.year} from {event.start_hour:02d}:{event.start_minute:02d} to {event.end_hour:02d}:{event.end_minute:02d}",
            event_created=created
        )
    
    async def _handle_edit_event_intent(
        self,
        session_id: str,
        context: SessionContext,
        data: Dict[str, Any]
    ) -> ChatAgentResponse:
        """Handle edit event intent - start the interactive edit flow."""
        target = data.get("target_event", {})
        
        # Check if user specified a day
        day = target.get("day")
        month = target.get("month")
        year = target.get("year")
        
        if day is not None:
            # User specified a day - show events on that day
            return await self._show_events_for_selection(session_id, context, day, month, year)
        
        # No day specified - ask user which day
        context.state = AgentState.SELECT_EVENT_DAY
        
        now = tz_now()
        tomorrow = now + timedelta(days=1)
        
        return self._build_response(
            session_id, context,
            "Which day is the event you want to edit on?",
            choices=[
                ChoiceOption(id="today", label=f"Today ({now.day}/{now.month})", value="today"),
                ChoiceOption(id="tomorrow", label=f"Tomorrow ({tomorrow.day}/{tomorrow.month})", value="tomorrow"),
                ChoiceOption(id="this_week", label="This week", value="this_week"),
            ],
            timeout=60
        )
    
    async def _show_events_for_selection(
        self,
        session_id: str,
        context: SessionContext,
        day: int,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> ChatAgentResponse:
        """Show events on a specific day for user to select."""
        now = tz_now()
        month = month or now.month
        year = year or now.year
        
        # Store the query date for later
        context.query_date = {"day": day, "month": month, "year": year}
        
        events = await self.repo.get_events_on_date(day, month, year)
        
        if not events:
            context.state = AgentState.SELECT_EVENT_DAY
            return self._build_response(
                session_id, context,
                f"No events found on {day}/{month}/{year}. Please try another day.",
                choices=[
                    ChoiceOption(id="today", label="Today", value="today"),
                    ChoiceOption(id="tomorrow", label="Tomorrow", value="tomorrow"),
                    ChoiceOption(id="other", label="Enter a date", value="other"),
                ],
                timeout=60
            )
        
        # Store events for selection
        context.events_on_day = [
            ExistingEvent(
                event_id=e["id"],
                title=e["title"],
                day=e["day"],
                month=e["month"],
                year=e["year"],
                start_hour=e["start_hour"],
                start_minute=e["start_minute"],
                end_hour=e["end_hour"],
                end_minute=e["end_minute"],
            ) for e in events
        ]
        
        context.state = AgentState.SELECT_EVENT
        
        # Build choices
        choices = []
        for i, evt in enumerate(context.events_on_day):
            label = f"{i+1}. {evt.title} ({evt.start_hour:02d}:{evt.start_minute:02d} - {evt.end_hour:02d}:{evt.end_minute:02d})"
            choices.append(ChoiceOption(id=f"event_{i}", label=label, value=str(i+1)))
        
        action_word = "edit" if context.intent == IntentType.EDIT_EVENT else "remove"
        return self._build_response(
            session_id, context,
            f"Events on {day}/{month}/{year}. Which one would you like to {action_word}?",
            choices=choices,
            timeout=60
        )
    
    async def _handle_legacy_edit_event(
        self,
        session_id: str,
        context: SessionContext,
        data: Dict[str, Any]
    ) -> ChatAgentResponse:
        """Legacy edit handler - kept for backwards compatibility with full event info."""
        target = data.get("target_event", {})
        event_data = data.get("event", {})
        
        # Find the event
        now = tz_now()
        day = target.get("day", now.day)
        month = target.get("month", now.month)
        year = target.get("year", now.year)
        
        found_event = await self.repo.find_event_by_title_and_date(
            target["title"], day, month, year
        )
        
        if not found_event:
            context.reset()
            return self._build_response(
                session_id, context,
                f"I couldn't find an event matching \"{target['title']}\" on {day}/{month}/{year}.",
            )
        
        # Store target for editing
        context.target_event_id = found_event["id"]
        context.event_data = EventData.from_dict(event_data)
        
        # If new time is provided, check for conflicts
        if event_data.get("start_hour") is not None:
            # Fill in missing time data from original event
            if context.event_data.day is None:
                context.event_data.day = found_event["day"]
            if context.event_data.month is None:
                context.event_data.month = found_event["month"]
            if context.event_data.year is None:
                context.event_data.year = found_event["year"]
            
            return await self._check_and_handle_edit_conflicts(session_id, context, found_event)
        
        # If no time change, just update title/location/notes
        updated = await self.repo.update_event(
            found_event["id"],
            title=event_data.get("title"),
            location=event_data.get("location"),
            notes=event_data.get("notes"),
        )
        
        context.reset()
        return self._build_response(
            session_id, context,
            f"✓ Event updated successfully.",
            event_updated=updated
        )
    
    async def _check_and_handle_edit_conflicts(
        self,
        session_id: str,
        context: SessionContext,
        original_event: Dict[str, Any]
    ) -> ChatAgentResponse:
        """Check conflicts for edit operation."""
        event = context.event_data
        
        # Get existing events excluding the one being edited
        existing_events = await self.repo.get_events_on_date(
            event.day, event.month, event.year
        )
        existing_events = [e for e in existing_events if e["id"] != context.target_event_id]
        
        result = self.prolog.check_conflict(
            event.start_hour, event.start_minute,
            event.end_hour, event.end_minute,
            existing_events
        )
        
        if result.has_conflict:
            conflict = result.conflicts[0]
            context.conflict_info = ConflictInfo(
                event_id=conflict["id"],
                title=conflict["title"],
                day=event.day,
                month=event.month,
                year=event.year,
                start_hour=conflict["start_hour"],
                start_minute=conflict["start_minute"],
                end_hour=conflict["end_hour"],
                end_minute=conflict["end_minute"],
            )
            context.state = AgentState.CONFIRM_CONFLICT
            
            return self._build_response(
                session_id, context,
                f"The new time conflicts with \"{conflict['title']}\". Would you like help finding another time?",
                choices=[
                    ChoiceOption(id="yes", label="Yes, help me", value="yes"),
                    ChoiceOption(id="no", label="No, cancel", value="no"),
                ],
                timeout=30
            )
        
        # No conflict - update the event
        updated = await self.repo.update_event(
            context.target_event_id,
            day=event.day,
            month=event.month,
            year=event.year,
            start_hour=event.start_hour,
            start_minute=event.start_minute,
            end_hour=event.end_hour,
            end_minute=event.end_minute,
        )
        
        context.reset()
        return self._build_response(
            session_id, context,
            f"✓ Event moved to {event.day}/{event.month}/{event.year} {event.start_hour:02d}:{event.start_minute:02d} - {event.end_hour:02d}:{event.end_minute:02d}",
            event_updated=updated
        )
    
    async def _handle_remove_event_intent(
        self,
        session_id: str,
        context: SessionContext,
        data: Dict[str, Any]
    ) -> ChatAgentResponse:
        """Handle remove event intent - start the interactive remove flow."""
        target = data.get("target_event", {})
        
        # Check if user specified a day
        day = target.get("day")
        month = target.get("month")
        year = target.get("year")
        
        if day is not None:
            # User specified a day - show events on that day
            return await self._show_events_for_selection(session_id, context, day, month, year)
        
        # No day specified - ask user which day
        context.state = AgentState.SELECT_EVENT_DAY
        
        now = tz_now()
        tomorrow = now + timedelta(days=1)
        
        return self._build_response(
            session_id, context,
            "Which day is the event you want to remove on?",
            choices=[
                ChoiceOption(id="today", label=f"Today ({now.day}/{now.month})", value="today"),
                ChoiceOption(id="tomorrow", label=f"Tomorrow ({tomorrow.day}/{tomorrow.month})", value="tomorrow"),
                ChoiceOption(id="this_week", label="This week", value="this_week"),
            ],
            timeout=60
        )
    
    async def _handle_query_events_intent(
        self,
        session_id: str,
        context: SessionContext,
        data: Dict[str, Any]
    ) -> ChatAgentResponse:
        """Handle query events intent."""
        query = data.get("query", {})
        query_type = query.get("type", "day")
        
        now = tz_now()
        day = query.get("day", now.day)
        month = query.get("month", now.month)
        year = query.get("year", now.year)
        
        events = await self.repo.get_events_for_query(
            query_type, day, month, year
        )
        
        context.reset()
        
        if not events:
            if query_type == "day":
                return self._build_response(
                    session_id, context,
                    f"No events scheduled for {day}/{month}/{year}.",
                    events_list=[]
                )
            elif query_type == "week":
                return self._build_response(
                    session_id, context,
                    f"No events scheduled for the week starting {day}/{month}/{year}.",
                    events_list=[]
                )
            else:
                return self._build_response(
                    session_id, context,
                    f"No events scheduled for {month}/{year}.",
                    events_list=[]
                )
        
        # Format events list
        events_text = self._format_events_list(events, query_type)
        
        return self._build_response(
            session_id, context,
            events_text,
            events_list=events
        )
    
    async def _handle_collect_info_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle COLLECT_INFO state - gather missing information."""
        field = context.missing_field
        
        # Parse the field value using LLM
        success, data, error = await self.llm.parse_field(field, message)
        
        if not success or data is None:
            return self._build_response(
                session_id, context,
                f"I couldn't understand that. {self._get_field_prompt(field)}",
            )
        
        # Update event data with parsed value
        if field == "title" and "title" in data:
            context.event_data.title = data["title"]
        elif field == "start_time":
            if "start_hour" in data:
                context.event_data.start_hour = data["start_hour"]
            if "start_minute" in data:
                context.event_data.start_minute = data["start_minute"]
        elif field == "end_time":
            if "end_hour" in data:
                context.event_data.end_hour = data["end_hour"]
            if "end_minute" in data:
                context.event_data.end_minute = data["end_minute"]
        elif field == "day":
            if "day" in data:
                context.event_data.day = data["day"]
            if "month" in data:
                context.event_data.month = data["month"]
            if "year" in data:
                context.event_data.year = data["year"]
        
        # Check for remaining missing fields
        missing = context.event_data.get_missing_fields()
        
        if missing:
            context.missing_field = missing[0]
            return self._build_response(
                session_id, context,
                self._get_field_prompt(missing[0]),
            )
        
        # All fields collected - check for conflicts
        context.state = AgentState.INIT  # Temporarily to reuse conflict check
        return await self._check_and_handle_conflicts(session_id, context)
    
    async def _handle_confirm_conflict_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle CONFIRM_CONFLICT state - ask if user needs help."""
        # First check if message is a direct button value (yes/no)
        message_lower = message.strip().lower()
        
        # Direct button responses or obvious yes/no words
        if message_lower in ["yes", "yes, help me", "help", "sure", "please", "pls", "ok", "okay", "y"]:
            answer = True
        elif message_lower in ["no", "no, cancel", "cancel", "nope", "n", "exit", "quit"]:
            answer = False
        else:
            # Use LLM to parse more complex responses
            success, answer, error = await self.llm.parse_yes_no(message)
            
            if not success:
                return self._build_response(
                    session_id, context,
                    "Please answer yes or no. Would you like help rescheduling?",
                    choices=[
                        ChoiceOption(id="yes", label="Yes, help me", value="yes"),
                        ChoiceOption(id="no", label="No, cancel", value="no"),
                    ],
                    timeout=30
                )
        
        if not answer:
            # User doesn't want help - reset
            context.reset()
            return self._build_response(
                session_id, context,
                "Okay, no changes made. What else can I help with?",
            )
        
        # User wants help - transition to CHOOSE_RESOLUTION
        context.state = AgentState.CHOOSE_RESOLUTION
        
        conflict_title = context.conflict_info.title if context.conflict_info else "the conflicting event"
        event_title = context.event_data.title if context.event_data else "your event"
        
        return self._build_response(
            session_id, context,
            f"I can help you in three ways:\n"
            f"1. Find a time slot that fits \"{event_title}\"\n"
            f"2. Move \"{conflict_title}\" to make room\n"
            f"3. Smart reschedule (AI-optimized)",
            choices=[
                ChoiceOption(id="find", label=f"Find slot for \"{event_title}\"", value="1"),
                ChoiceOption(id="move", label=f"Move \"{conflict_title}\"", value="2"),
                ChoiceOption(id="smart", label="Smart reschedule (AI-optimized)", value="3"),
            ],
            timeout=30
        )
    
    async def _handle_choose_resolution_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle CHOOSE_RESOLUTION state - find slot, move event, or smart reschedule."""
        choice = message.strip()
        
        if choice in ["1", "find", "first"]:
            context.resolution_type = ResolutionType.FIND_SLOT_FOR_NEW
        elif choice in ["2", "move", "second"]:
            context.resolution_type = ResolutionType.MOVE_CONFLICTING
        elif choice in ["3", "smart", "third", "smart reschedule", "ai"]:
            context.resolution_type = ResolutionType.SMART_RESCHEDULE
            context.state = AgentState.SELECT_STRATEGY
            return self._build_response(
                session_id, context,
                "Which rescheduling strategy would you prefer?",
                choices=[
                    ChoiceOption(id="minimize", label="1. Minimize moves", value="1"),
                    ChoiceOption(id="quality", label="2. Maximize time quality", value="2"),
                    ChoiceOption(id="balanced", label="3. Balanced (Recommended)", value="3"),
                ],
                timeout=30
            )
        else:
            conflict_title = context.conflict_info.title if context.conflict_info else "the conflicting event"
            event_title = context.event_data.title if context.event_data else "your event"
            return self._build_response(
                session_id, context,
                "Please select option 1, 2, or 3.",
                choices=[
                    ChoiceOption(id="find", label=f"1. Find slot for \"{event_title}\"", value="1"),
                    ChoiceOption(id="move", label=f"2. Move \"{conflict_title}\"", value="2"),
                    ChoiceOption(id="smart", label="3. Smart reschedule (AI-optimized)", value="3"),
                ],
                timeout=30
            )
        
        # Transition to SELECT_PREFERENCE
        context.state = AgentState.SELECT_PREFERENCE
        
        return self._build_response(
            session_id, context,
            "What's your preference for the new time?",
            choices=[
                ChoiceOption(id="same_time", label="1. Same time on different day", value="1"),
                ChoiceOption(id="specific_day", label="2. I want a specific day", value="2"),
                ChoiceOption(id="specific_both", label="3. Specific day and time", value="3"),
                ChoiceOption(id="any_free", label="4. Any time I'm free", value="4"),
            ],
            timeout=30
        )
    
    async def _handle_select_preference_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle SELECT_PREFERENCE state - user selecting preference."""
        # First check for direct numeric button values
        message_stripped = message.strip()
        
        # Direct numeric choice
        if message_stripped in ["1", "2", "3", "4"]:
            choice = int(message_stripped)
            pref_data = {"choice": choice}
        else:
            # Use LLM to parse more complex responses
            success, pref_data, error = await self.llm.parse_preference(message)
            
            if not success or pref_data is None:
                return self._build_response(
                    session_id, context,
                    "Please select one of the options (1-4).",
                    choices=[
                        ChoiceOption(id="same_time", label="1. Same time on different day", value="1"),
                        ChoiceOption(id="specific_day", label="2. I want a specific day", value="2"),
                        ChoiceOption(id="specific_both", label="3. Specific day and time", value="3"),
                        ChoiceOption(id="any_free", label="4. Any time I'm free", value="4"),
                    ],
                    timeout=30
                )
        
        choice = pref_data.get("choice", 1)
        
        if choice == 1:
            context.preference_type = PreferenceType.SAME_TIME_DIFFERENT_DAY
            return await self._find_same_time_different_days(session_id, context)
        elif choice == 2:
            context.preference_type = PreferenceType.SPECIFIC_DAY
            # Check if day was provided
            if pref_data.get("day"):
                return await self._find_slots_on_day(
                    session_id, context,
                    pref_data["day"], pref_data.get("month"), pref_data.get("year")
                )
            return self._build_response(
                session_id, context,
                "Which day would you prefer? (e.g., 'Monday', 'next Tuesday', '15/4')",
            )
        elif choice == 3:
            context.preference_type = PreferenceType.SPECIFIC_DAY_AND_TIME
            # Check if full details provided
            if pref_data.get("day") and pref_data.get("start_hour") is not None:
                return await self._check_specific_time(
                    session_id, context, pref_data
                )
            return self._build_response(
                session_id, context,
                "Please specify the day and time (e.g., 'Tuesday at 2pm').",
            )
        else:  # choice == 4
            context.preference_type = PreferenceType.ANY_FREE_TIME
            return await self._find_any_free_slots(session_id, context)
    
    async def _find_same_time_different_days(
        self,
        session_id: str,
        context: SessionContext
    ) -> ChatAgentResponse:
        """Find 3 days where the same time slot is free."""
        event = context.event_data
        duration = (event.end_hour * 60 + event.end_minute) - (event.start_hour * 60 + event.start_minute)
        
        # Get events for next 7 days
        now = tz_now()
        events_by_day = await self.repo.get_events_for_week(
            now.day, now.month, now.year
        )
        
        # Find days where the preferred time is free
        free_slots = self.prolog.find_free_days(
            duration, events_by_day,
            event.start_hour, event.start_minute,
            max_results=3 + context.slot_offset
        )
        
        if len(free_slots) <= context.slot_offset:
            context.slot_offset = 0
            context.state = AgentState.SELECT_PREFERENCE
            return self._build_response(
                session_id, context,
                "No free days found at that time. Please try a different preference.",
                choices=[
                    ChoiceOption(id="specific_day", label="2. Choose a specific day", value="2"),
                    ChoiceOption(id="any_free", label="4. Any time I'm free", value="4"),
                ],
                timeout=30
            )
        
        # Get slots after offset
        display_slots = free_slots[context.slot_offset:context.slot_offset + 3]
        context.suggested_slots = [TimeSlot(
            day=s.day, month=s.month, year=s.year,
            start_hour=s.start_hour, start_minute=s.start_minute,
            end_hour=s.end_hour, end_minute=s.end_minute
        ) for s in display_slots]
        
        context.state = AgentState.SELECT_SLOT
        
        choices = []
        for i, slot in enumerate(display_slots):
            label = f"{i+1}. {slot.day}/{slot.month}/{slot.year} {slot.start_hour:02d}:{slot.start_minute:02d}"
            choices.append(ChoiceOption(id=f"slot_{i}", label=label, value=str(i+1)))
        choices.append(ChoiceOption(id="more", label="4. Show more options", value="4"))
        
        return self._build_response(
            session_id, context,
            f"Here are {len(display_slots)} available days at {event.start_hour:02d}:{event.start_minute:02d}:",
            choices=choices,
            timeout=30
        )
    
    async def _find_slots_on_day(
        self,
        session_id: str,
        context: SessionContext,
        day: int,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> ChatAgentResponse:
        """Find free time ranges on a specific day and let user pick a time."""
        now = tz_now()
        month = month or now.month
        year = year or now.year
        
        event = context.event_data
        duration = (event.end_hour * 60 + event.end_minute) - (event.start_hour * 60 + event.start_minute)
        
        existing_events = await self.repo.get_events_on_date(day, month, year)
        
        # Use new range-based finding with past time filtering
        free_ranges = self.prolog.find_free_ranges_on_date(
            day, month, year, existing_events,
            duration_minutes=duration,
            filter_past_times=True,
            timezone=self.timezone
        )
        
        if not free_ranges:
            context.slot_offset = 0
            context.state = AgentState.SELECT_PREFERENCE
            return self._build_response(
                session_id, context,
                f"No free time available on {day}/{month}/{year} for a {duration}-minute event. Please try a different day.",
                choices=[
                    ChoiceOption(id="same_time", label="1. Same time on different day", value="1"),
                    ChoiceOption(id="specific_day", label="2. Try another day", value="2"),
                    ChoiceOption(id="any_free", label="4. Any time I'm free", value="4"),
                ],
                timeout=30
            )
        
        # Store free ranges in context for validation
        context.free_ranges = [FreeTimeRange(
            day=r.day, month=r.month, year=r.year,
            start_hour=r.start_hour, start_minute=r.start_minute,
            end_hour=r.end_hour, end_minute=r.end_minute
        ) for r in free_ranges]
        
        context.state = AgentState.SELECT_TIME_IN_RANGE
        
        # Build display message showing free ranges
        range_lines = []
        for i, r in enumerate(free_ranges):
            range_lines.append(f"  {i+1}. {r.format_time_range()} ({r.duration_minutes()} mins available)")
        
        ranges_display = "\n".join(range_lines)
        
        return self._build_response(
            session_id, context,
            f"Free time on {day}/{month}/{year}:\n{ranges_display}\n\nPlease type your preferred start time (e.g., \"10:00\" or \"14:30\"):",
            timeout=60
        )
    
    async def _check_specific_time(
        self,
        session_id: str,
        context: SessionContext,
        time_data: Dict[str, Any]
    ) -> ChatAgentResponse:
        """Check if a specific time slot is available."""
        day = time_data["day"]
        month = time_data.get("month") or tz_now().month
        year = time_data.get("year") or tz_now().year
        start_hour = time_data["start_hour"]
        start_minute = time_data.get("start_minute", 0)
        
        # Calculate end time based on original duration
        event = context.event_data
        duration = (event.end_hour * 60 + event.end_minute) - (event.start_hour * 60 + event.start_minute)
        end_minutes = start_hour * 60 + start_minute + duration
        end_hour = end_minutes // 60
        end_minute = end_minutes % 60
        
        existing_events = await self.repo.get_events_on_date(day, month, year)
        
        result = self.prolog.check_conflict(
            start_hour, start_minute, end_hour, end_minute, existing_events
        )
        
        if result.has_conflict:
            conflict = result.conflicts[0]
            return self._build_response(
                session_id, context,
                f"That time conflicts with \"{conflict['title']}\". Please choose another time.",
                choices=[
                    ChoiceOption(id="same_time", label="1. Same time, different day", value="1"),
                    ChoiceOption(id="specific_day", label="2. Different time, same day", value="2"),
                    ChoiceOption(id="any_free", label="4. Any free time", value="4"),
                ],
                timeout=30
            )
        
        # Time is available - set selected slot and confirm
        context.selected_slot = TimeSlot(
            day=day, month=month, year=year,
            start_hour=start_hour, start_minute=start_minute,
            end_hour=end_hour, end_minute=end_minute
        )
        context.state = AgentState.CONFIRM_ACTION
        
        return await self._show_confirmation(session_id, context)
    
    async def _find_any_free_slots(
        self,
        session_id: str,
        context: SessionContext
    ) -> ChatAgentResponse:
        """Find any free time ranges in the next 7 days, showing 3 days at a time."""
        event = context.event_data
        duration = (event.end_hour * 60 + event.end_minute) - (event.start_hour * 60 + event.start_minute)
        
        now = tz_now()
        all_ranges_by_day = []  # List of (date_tuple, ranges_for_day)
        
        # Search through next 14 days and collect free ranges grouped by day
        for i in range(14):
            check_date = now + timedelta(days=i)
            events = await self.repo.get_events_on_date(
                check_date.day, check_date.month, check_date.year
            )
            
            day_ranges = self.prolog.find_free_ranges_on_date(
                check_date.day, check_date.month, check_date.year,
                events,
                duration_minutes=duration,
                filter_past_times=True,
                timezone=self.timezone
            )
            
            if day_ranges:
                all_ranges_by_day.append((
                    (check_date.day, check_date.month, check_date.year),
                    day_ranges
                ))
            
            # Stop if we have enough days
            if len(all_ranges_by_day) >= 6 + context.slot_offset:
                break
        
        if not all_ranges_by_day:
            context.slot_offset = 0
            return self._build_response(
                session_id, context,
                f"No free time found in the next 14 days for a {duration}-minute event. Your schedule is quite full!",
            )
        
        # Apply offset and limit to 3 days
        if len(all_ranges_by_day) <= context.slot_offset:
            context.slot_offset = 0  # Reset if offset exceeds available days
        
        display_days = all_ranges_by_day[context.slot_offset:context.slot_offset + 3]
        has_more = len(all_ranges_by_day) > context.slot_offset + 3
        
        # Flatten ranges for storage in context (for validation)
        all_display_ranges = []
        for _, ranges in display_days:
            all_display_ranges.extend(ranges)
        
        context.free_ranges = [FreeTimeRange(
            day=r.day, month=r.month, year=r.year,
            start_hour=r.start_hour, start_minute=r.start_minute,
            end_hour=r.end_hour, end_minute=r.end_minute
        ) for r in all_display_ranges]
        
        context.state = AgentState.SELECT_TIME_IN_RANGE
        
        # Build display message showing free ranges grouped by day
        range_lines = []
        for i, ((day, month, year), ranges) in enumerate(display_days):
            range_lines.append(f"{i+1}. 📅 {day}/{month}/{year}:")
            for r in ranges:
                range_lines.append(f"   • {r.format_time_range()} ({r.duration_minutes()} mins)")
        
        ranges_display = "\n".join(range_lines)
        
        # Build choices
        choices = []
        if has_more:
            choices.append(ChoiceOption(id="more", label="Show more days", value="more"))
        
        return self._build_response(
            session_id, context,
            f"Available time slots:\n{ranges_display}\n\nType your preferred time (e.g., \"10:00\") or date+time (e.g., \"{display_days[0][0][0]}/{display_days[0][0][1]} 10:00\"):",
            choices=choices if choices else None,
            timeout=60
        )
    
    async def _handle_select_slot_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle SELECT_SLOT state - user selecting from suggested slots."""
        # First check for direct numeric button values
        message_stripped = message.strip()
        
        # Direct numeric choice (1, 2, 3, 4)
        if message_stripped in ["1", "2", "3", "4"]:
            choice = int(message_stripped)
        else:
            # Use LLM to parse more complex responses
            success, choice, error = await self.llm.parse_slot_selection(message)
            
            if not success:
                return self._build_response(
                    session_id, context,
                    "Please select a slot number (1-3) or 4 for more options.",
                )
        
        if choice == 4:
            # Show more slots
            context.slot_offset += 3
            
            if context.preference_type == PreferenceType.SAME_TIME_DIFFERENT_DAY:
                return await self._find_same_time_different_days(session_id, context)
            elif context.preference_type == PreferenceType.SPECIFIC_DAY:
                slot = context.suggested_slots[0] if context.suggested_slots else None
                if slot:
                    return await self._find_slots_on_day(session_id, context, slot.day, slot.month, slot.year)
            else:
                return await self._find_any_free_slots(session_id, context)
        
        if choice < 1 or choice > len(context.suggested_slots):
            return self._build_response(
                session_id, context,
                f"Please select a valid option (1-{len(context.suggested_slots)}).",
            )
        
        # User selected a slot
        context.selected_slot = context.suggested_slots[choice - 1]
        context.state = AgentState.CONFIRM_ACTION
        
        return await self._show_confirmation(session_id, context)
    
    async def _handle_select_time_in_range_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle SELECT_TIME_IN_RANGE state - user entering a specific time within free ranges."""
        import re
        
        message = message.strip().lower()
        
        # Handle "show more" button
        if message == "more" or message == "show more" or message == "show more days":
            context.slot_offset += 3
            return await self._find_any_free_slots(session_id, context)
        
        event = context.event_data
        duration = (event.end_hour * 60 + event.end_minute) - (event.start_hour * 60 + event.start_minute)
        
        # Parse the user's time input
        # Supported formats:
        # - "10:00" or "10:30" (time only - use first range's date)
        # - "10/4 14:00" (date and time)
        # - "10/4/2026 14:00" (full date and time)
        
        day = None
        month = None
        year = None
        start_hour = None
        start_minute = 0
        
        # Try to parse date and time: "10/4 14:00" or "10/4/2026 14:00"
        date_time_match = re.match(r'(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+(\d{1,2}):(\d{2})', message)
        if date_time_match:
            day = int(date_time_match.group(1))
            month = int(date_time_match.group(2))
            year = int(date_time_match.group(3)) if date_time_match.group(3) else tz_now().year
            start_hour = int(date_time_match.group(4))
            start_minute = int(date_time_match.group(5))
        else:
            # Try to parse time only: "10:00" or "14:30"
            time_match = re.match(r'(\d{1,2}):(\d{2})', message)
            if time_match:
                start_hour = int(time_match.group(1))
                start_minute = int(time_match.group(2))
                # Use the date from the first free range
                if context.free_ranges:
                    first_range = context.free_ranges[0]
                    day = first_range.day
                    month = first_range.month
                    year = first_range.year
            else:
                # Try hour only: "10" or "14"
                hour_match = re.match(r'^(\d{1,2})$', message)
                if hour_match:
                    start_hour = int(hour_match.group(1))
                    if context.free_ranges:
                        first_range = context.free_ranges[0]
                        day = first_range.day
                        month = first_range.month
                        year = first_range.year
        
        if start_hour is None or day is None:
            return self._build_response(
                session_id, context,
                "I couldn't understand that time. Please enter a time like \"10:00\" or \"14:30\", or with a date like \"10/4 14:00\".",
            )
        
        # Validate hour and minute
        if start_hour < 0 or start_hour > 23 or start_minute < 0 or start_minute > 59:
            return self._build_response(
                session_id, context,
                "Please enter a valid time (hour 0-23, minute 0-59).",
            )
        
        # Calculate end time
        end_minutes = start_hour * 60 + start_minute + duration
        end_hour = end_minutes // 60
        end_minute = end_minutes % 60
        
        if end_hour >= 24:
            return self._build_response(
                session_id, context,
                f"This event would end after midnight. Please choose an earlier start time.",
            )
        
        # Validate that the time fits within one of the free ranges
        time_fits = False
        for r in context.free_ranges:
            if r.day == day and r.month == month and r.year == year:
                range_start = r.start_hour * 60 + r.start_minute
                range_end = r.end_hour * 60 + r.end_minute
                proposed_start = start_hour * 60 + start_minute
                proposed_end = proposed_start + duration
                
                if proposed_start >= range_start and proposed_end <= range_end:
                    time_fits = True
                    break
        
        if not time_fits:
            # Build helpful error message
            available_on_day = [r for r in context.free_ranges if r.day == day and r.month == month and r.year == year]
            if available_on_day:
                ranges_str = ", ".join([r.format_time_range() for r in available_on_day])
                return self._build_response(
                    session_id, context,
                    f"The time {start_hour:02d}:{start_minute:02d} doesn't fit in the available ranges on {day}/{month}/{year}.\n"
                    f"Available free time: {ranges_str}\n"
                    f"Please choose a different time that fits within the free ranges.",
                )
            else:
                return self._build_response(
                    session_id, context,
                    f"No free time available on {day}/{month}/{year}. Please check the available dates above.",
                )
        
        # Time is valid - set selected slot and proceed to confirmation
        context.selected_slot = TimeSlot(
            day=day, month=month, year=year,
            start_hour=start_hour, start_minute=start_minute,
            end_hour=end_hour, end_minute=end_minute
        )
        context.state = AgentState.CONFIRM_ACTION
        
        return await self._show_confirmation(session_id, context)
    
    async def _show_confirmation(
        self,
        session_id: str,
        context: SessionContext
    ) -> ChatAgentResponse:
        """Show confirmation dialog."""
        slot = context.selected_slot
        event = context.event_data
        
        if context.resolution_type == ResolutionType.MOVE_CONFLICTING:
            # Moving the conflicting event
            conflict = context.conflict_info
            text = f"Please confirm:\n"
            text += f"• Move \"{conflict.title}\" to {slot.day}/{slot.month}/{slot.year} {slot.start_hour:02d}:{slot.start_minute:02d}\n"
            text += f"• Add \"{event.title}\" at original time"
        else:
            # Moving the new event
            text = f"Please confirm:\n"
            text += f"• Add \"{event.title}\" on {slot.day}/{slot.month}/{slot.year} {slot.start_hour:02d}:{slot.start_minute:02d} - {slot.end_hour:02d}:{slot.end_minute:02d}"
        
        return self._build_response(
            session_id, context,
            text,
            choices=[
                ChoiceOption(id="confirm", label="✓ Confirm", value="yes"),
                ChoiceOption(id="back", label="← Go back", value="no"),
            ],
            timeout=30
        )
    
    async def _handle_confirm_action_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle CONFIRM_ACTION state - final confirmation."""
        # First check if message is a direct button value
        message_lower = message.strip().lower()
        
        # Direct button responses
        if message_lower in ["yes", "confirm", "✓ confirm", "ok", "okay", "sure", "y"]:
            confirmed = True
        elif message_lower in ["no", "back", "← go back", "go back", "cancel", "n"]:
            confirmed = False
        else:
            # Use LLM to parse more complex responses
            success, confirmed, error = await self.llm.parse_confirmation(message)
            
            if not success:
                return self._build_response(
                    session_id, context,
                    "Please confirm or go back.",
                    choices=[
                        ChoiceOption(id="confirm", label="✓ Confirm", value="yes"),
                        ChoiceOption(id="back", label="← Go back", value="no"),
                    ],
                    timeout=30
                )
        
        if not confirmed:
            # Go back to preference selection
            context.state = AgentState.SELECT_PREFERENCE
            context.slot_offset = 0
            return self._build_response(
                session_id, context,
                "What's your preference for the new time?",
                choices=[
                    ChoiceOption(id="same_time", label="1. Same time on different day", value="1"),
                    ChoiceOption(id="specific_day", label="2. I want a specific day", value="2"),
                    ChoiceOption(id="specific_both", label="3. Specific day and time", value="3"),
                    ChoiceOption(id="any_free", label="4. Any time I'm free", value="4"),
                ],
                timeout=30
            )
        
        # Execute the action
        slot = context.selected_slot
        event = context.event_data
        
        if context.resolution_type == ResolutionType.MOVE_CONFLICTING:
            # Move the conflicting event first
            conflict = context.conflict_info
            await self.repo.update_event(
                conflict.event_id,
                day=slot.day,
                month=slot.month,
                year=slot.year,
                start_hour=slot.start_hour,
                start_minute=slot.start_minute,
                end_hour=slot.end_hour,
                end_minute=slot.end_minute,
            )
            
            # Then create the new event at original time
            created = await self.repo.create_event(
                title=event.title,
                day=event.day,
                month=event.month,
                year=event.year,
                start_hour=event.start_hour,
                start_minute=event.start_minute,
                end_hour=event.end_hour,
                end_minute=event.end_minute,
                location=event.location,
                notes=event.notes,
            )
            
            context.reset()
            return self._build_response(
                session_id, context,
                f"✓ Done! \"{conflict.title}\" moved and \"{event.title}\" created.",
                event_created=created
            )
        else:
            # Create new event at selected slot
            created = await self.repo.create_event(
                title=event.title,
                day=slot.day,
                month=slot.month,
                year=slot.year,
                start_hour=slot.start_hour,
                start_minute=slot.start_minute,
                end_hour=slot.end_hour,
                end_minute=slot.end_minute,
                location=event.location,
                notes=event.notes,
            )
            
            context.reset()
            return self._build_response(
                session_id, context,
                f"✓ Event \"{event.title}\" created on {slot.day}/{slot.month}/{slot.year} {slot.start_hour:02d}:{slot.start_minute:02d} - {slot.end_hour:02d}:{slot.end_minute:02d}",
                event_created=created
            )
    
    # =========================================================================
    # Phase 2: Smart Reschedule (Constraint Solver) Handlers
    # =========================================================================
    
    async def _handle_select_strategy_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle SELECT_STRATEGY state — user picks a rescheduling strategy."""
        choice = message.strip().lower()
        
        if choice in ["1", "minimize", "minimize moves"]:
            context.reschedule_strategy = RescheduleStrategy.MINIMIZE_MOVES
        elif choice in ["2", "quality", "maximize", "maximize time quality"]:
            context.reschedule_strategy = RescheduleStrategy.MAXIMIZE_QUALITY
        elif choice in ["3", "balanced", "recommended"]:
            context.reschedule_strategy = RescheduleStrategy.BALANCED
        else:
            return self._build_response(
                session_id, context,
                "Please select a strategy (1-3).",
                choices=[
                    ChoiceOption(id="minimize", label="1. Minimize moves", value="1"),
                    ChoiceOption(id="quality", label="2. Maximize time quality", value="2"),
                    ChoiceOption(id="balanced", label="3. Balanced (Recommended)", value="3"),
                ],
                timeout=30
            )
        
        return await self._start_smart_reschedule(session_id, context)
    
    async def _start_smart_reschedule(
        self,
        session_id: str,
        context: SessionContext
    ) -> ChatAgentResponse:
        """Start the smart reschedule flow — generate options and show them."""
        event = context.event_data
        conflict = context.conflict_info
        
        if not event or not conflict:
            context.reset()
            return self._build_response(
                session_id, context,
                "Sorry, something went wrong. Please start over.",
            )
        
        # Fetch all events on the conflict date to feed the solver
        existing_events = await self.repo.get_events_on_date(
            day=event.day, month=event.month, year=event.year
        )
        
        # Build the new event dict for the solver
        new_event = {
            "title": event.title,
            "start_hour": event.start_hour,
            "start_minute": event.start_minute,
            "end_hour": event.end_hour,
            "end_minute": event.end_minute,
        }
        
        # Use balanced strategy by default
        strategy = context.reschedule_strategy or RescheduleStrategy.BALANCED

        # Fetch the user's persona priority map so the solver uses personal weights
        priority_map = await self.repo.get_user_priority_map()

        # Call the constraint solver
        prolog = get_prolog_service()
        options = prolog.suggest_reschedule_options(
            new_event=new_event,
            existing_events=existing_events,
            strategy=strategy.value,
            priority_map=priority_map,
        )
        
        if not options:
            # Fallback: no options found — go back to basic choices
            context.state = AgentState.CHOOSE_RESOLUTION
            return self._build_response(
                session_id, context,
                "I couldn't find optimal reschedule options. Please try another approach:",
                choices=[
                    ChoiceOption(id="find", label="1. Find slot for new event", value="1"),
                    ChoiceOption(id="move", label="2. Move conflicting event", value="2"),
                ],
                timeout=30
            )
        
        # Store options in context
        context.reschedule_options = options
        context.state = AgentState.SELECT_RESCHEDULE_OPTION
        
        # Format options for display
        text = "🧠 Here are the AI-optimized reschedule options:\n\n"
        for i, opt in enumerate(options, 1):
            text += f"**Option {i}** (score: {opt.cost:.1f})\n"
            for move in opt.moves:
                sh = move.get("new_start_hour", move.get("start_hour", 0))
                sm = move.get("new_start_minute", move.get("start_minute", 0))
                eh = move.get("new_end_hour", move.get("end_hour", 0))
                em = move.get("new_end_minute", move.get("end_minute", 0))
                if move.get("action") == "place_new":
                    text += f"  📌 Place \"{move['title']}\" at {sh:02d}:{sm:02d} - {eh:02d}:{em:02d}\n"
                else:
                    text += f"  🔄 Move \"{move['title']}\" → {sh:02d}:{sm:02d} - {eh:02d}:{em:02d}\n"
            text += f"  {opt.description}\n\n"
        
        choices = []
        for i, opt in enumerate(options, 1):
            choices.append(ChoiceOption(
                id=f"option_{i}",
                label=f"Option {i}: {opt.description}",
                value=str(i)
            ))
        choices.append(ChoiceOption(id="back", label="← Go back", value="back"))
        
        return self._build_response(
            session_id, context,
            text,
            choices=choices,
            timeout=60
        )
    
    async def _handle_select_reschedule_option_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle SELECT_RESCHEDULE_OPTION — user picks from A* options."""
        message_lower = message.strip().lower()
        
        # Direct button handling
        if message_lower == "back":
            choice = "back"
        elif message_lower in ["1", "2", "3"]:
            choice = int(message_lower)
        else:
            success, choice, error = await self.llm.parse_reschedule_option(message)
            if not success:
                choices = []
                for i, opt in enumerate(context.reschedule_options or [], 1):
                    choices.append(ChoiceOption(
                        id=f"option_{i}",
                        label=f"Option {i}: {opt.description}",
                        value=str(i)
                    ))
                choices.append(ChoiceOption(id="back", label="← Go back", value="back"))
                return self._build_response(
                    session_id, context,
                    "Please select an option number (1-3) or go back.",
                    choices=choices,
                    timeout=60
                )
        
        if choice == "back":
            context.state = AgentState.CHOOSE_RESOLUTION
            conflict_title = context.conflict_info.title if context.conflict_info else "the conflicting event"
            event_title = context.event_data.title if context.event_data else "your event"
            return self._build_response(
                session_id, context,
                f"How would you like to resolve the conflict?",
                choices=[
                    ChoiceOption(id="find", label=f"1. Find slot for \"{event_title}\"", value="1"),
                    ChoiceOption(id="move", label=f"2. Move \"{conflict_title}\"", value="2"),
                    ChoiceOption(id="smart", label="3. Smart reschedule (AI-optimized)", value="3"),
                ],
                timeout=30
            )
        
        options = context.reschedule_options or []
        if not isinstance(choice, int) or choice < 1 or choice > len(options):
            return self._build_response(
                session_id, context,
                f"Please pick a valid option (1-{len(options)}).",
                timeout=30
            )
        
        selected = options[choice - 1]
        context.selected_reschedule = selected
        context.state = AgentState.CONFIRM_RESCHEDULE
        
        # Show confirmation
        text = f"Please confirm these changes:\n"
        for move in selected.moves:
            sh = move.get("new_start_hour", move.get("start_hour", 0))
            sm = move.get("new_start_minute", move.get("start_minute", 0))
            eh = move.get("new_end_hour", move.get("end_hour", 0))
            em = move.get("new_end_minute", move.get("end_minute", 0))
            if move.get("action") == "place_new":
                text += f"  📌 Add \"{move['title']}\" at {sh:02d}:{sm:02d} - {eh:02d}:{em:02d}\n"
            else:
                text += f"  🔄 Move \"{move['title']}\" → {sh:02d}:{sm:02d} - {eh:02d}:{em:02d}\n"
        
        return self._build_response(
            session_id, context,
            text,
            choices=[
                ChoiceOption(id="confirm", label="✓ Confirm", value="yes"),
                ChoiceOption(id="back", label="← Go back", value="no"),
            ],
            timeout=30
        )
    
    async def _handle_confirm_reschedule_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle CONFIRM_RESCHEDULE — execute the selected option's moves."""
        message_lower = message.strip().lower()
        
        if message_lower in ["yes", "confirm", "✓ confirm", "ok", "okay", "sure", "y"]:
            confirmed = True
        elif message_lower in ["no", "back", "← go back", "go back", "cancel", "n"]:
            confirmed = False
        else:
            success, confirmed, error = await self.llm.parse_confirmation(message)
            if not success:
                return self._build_response(
                    session_id, context,
                    "Please confirm or go back.",
                    choices=[
                        ChoiceOption(id="confirm", label="✓ Confirm", value="yes"),
                        ChoiceOption(id="back", label="← Go back", value="no"),
                    ],
                    timeout=30
                )
        
        if not confirmed:
            # Go back to option selection
            return await self._start_smart_reschedule(session_id, context)
        
        # Execute all moves
        selected = context.selected_reschedule
        if not selected:
            context.reset()
            return self._build_response(
                session_id, context,
                "Something went wrong. Please start over.",
            )
        
        event = context.event_data
        created_event = None
        summary_lines = []
        
        if selected.action == "move_new":
            # The new event is moved to a different time; conflicting events stay
            for move in selected.moves:
                sh = move.get("new_start_hour", move.get("start_hour", 0))
                sm = move.get("new_start_minute", move.get("start_minute", 0))
                eh = move.get("new_end_hour", move.get("end_hour", 0))
                em = move.get("new_end_minute", move.get("end_minute", 0))
                created_event = await self.repo.create_event(
                    title=move["title"],
                    day=event.day,
                    month=event.month,
                    year=event.year,
                    start_hour=sh,
                    start_minute=sm,
                    end_hour=eh,
                    end_minute=em,
                    location=event.location,
                    notes=event.notes,
                )
                summary_lines.append(
                    f"📌 Created \"{move['title']}\" at {sh:02d}:{sm:02d}-{eh:02d}:{em:02d}"
                )
        elif selected.action == "move_existing":
            # Move the conflicting event(s) out of the way, then create the new event at its original time
            for move in selected.moves:
                sh = move.get("new_start_hour", move.get("start_hour", 0))
                sm = move.get("new_start_minute", move.get("start_minute", 0))
                eh = move.get("new_end_hour", move.get("end_hour", 0))
                em = move.get("new_end_minute", move.get("end_minute", 0))
                await self.repo.update_event(
                    event_id=move["event_id"],
                    day=event.day,
                    month=event.month,
                    year=event.year,
                    start_hour=sh,
                    start_minute=sm,
                    end_hour=eh,
                    end_minute=em,
                )
                summary_lines.append(
                    f"🔄 Moved \"{move['title']}\" → {sh:02d}:{sm:02d}-{eh:02d}:{em:02d}"
                )
            # Now create the new event at its originally requested time
            created_event = await self.repo.create_event(
                title=event.title,
                day=event.day,
                month=event.month,
                year=event.year,
                start_hour=event.start_hour,
                start_minute=event.start_minute,
                end_hour=event.end_hour,
                end_minute=event.end_minute,
                location=event.location,
                notes=event.notes,
            )
            summary_lines.append(
                f"📌 Created \"{event.title}\" at {event.start_hour:02d}:{event.start_minute:02d}-{event.end_hour:02d}:{event.end_minute:02d}"
            )
        
        context.reset()
        summary = "\n".join(summary_lines)
        return self._build_response(
            session_id, context,
            f"✓ Done! Smart reschedule applied:\n{summary}",
            event_created=created_event
        )
    
    # =========================================================================
    # Edit/Remove Flow State Handlers
    # =========================================================================
    
    async def _handle_select_event_day_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle SELECT_EVENT_DAY state - user is specifying which day to list events from."""
        message_lower = message.strip().lower()
        now = tz_now()
        
        # Handle button clicks
        if message_lower in ["today", "1"]:
            day, month, year = now.day, now.month, now.year
        elif message_lower in ["tomorrow", "2"]:
            tomorrow = now + timedelta(days=1)
            day, month, year = tomorrow.day, tomorrow.month, tomorrow.year
        elif message_lower in ["this_week", "this week", "3"]:
            # Show events for the whole week
            return await self._show_week_events_for_selection(session_id, context)
        elif message_lower == "other":
            return self._build_response(
                session_id, context,
                "Please enter a date (e.g., '25/4' or '25/4/2025'):",
                timeout=60
            )
        else:
            # Try to parse as date
            parsed_date = self._parse_date_input(message)
            if parsed_date:
                day, month, year = parsed_date
            else:
                return self._build_response(
                    session_id, context,
                    "I didn't understand that date. Please try again or select an option:",
                    choices=[
                        ChoiceOption(id="today", label=f"Today ({now.day}/{now.month})", value="today"),
                        ChoiceOption(id="tomorrow", label="Tomorrow", value="tomorrow"),
                        ChoiceOption(id="this_week", label="This week", value="this_week"),
                    ],
                    timeout=60
                )
        
        return await self._show_events_for_selection(session_id, context, day, month, year)
    
    async def _show_week_events_for_selection(
        self,
        session_id: str,
        context: SessionContext
    ) -> ChatAgentResponse:
        """Show events for the current week for user to select."""
        now = tz_now()
        all_events = []
        
        # Get events for next 7 days
        for i in range(7):
            date = now + timedelta(days=i)
            events = await self.repo.get_events_on_date(date.day, date.month, date.year)
            for e in events:
                all_events.append(ExistingEvent(
                    event_id=e["id"],
                    title=e["title"],
                    day=e["day"],
                    month=e["month"],
                    year=e["year"],
                    start_hour=e["start_hour"],
                    start_minute=e["start_minute"],
                    end_hour=e["end_hour"],
                    end_minute=e["end_minute"],
                ))
        
        if not all_events:
            context.reset()
            action_word = "edit" if context.intent == IntentType.EDIT_EVENT else "remove"
            return self._build_response(
                session_id, context,
                f"No events found this week. There's nothing to {action_word}.",
            )
        
        # Store events for selection
        context.events_on_day = all_events
        context.state = AgentState.SELECT_EVENT
        
        # Build choices
        choices = []
        for i, evt in enumerate(all_events):
            label = f"{i+1}. {evt.title} ({evt.day}/{evt.month} {evt.start_hour:02d}:{evt.start_minute:02d})"
            choices.append(ChoiceOption(id=f"event_{i}", label=label, value=str(i+1)))
        
        action_word = "edit" if context.intent == IntentType.EDIT_EVENT else "remove"
        return self._build_response(
            session_id, context,
            f"Events this week. Which one would you like to {action_word}?",
            choices=choices,
            timeout=60
        )
    
    def _parse_date_input(self, message: str) -> Optional[Tuple[int, int, int]]:
        """Parse a date input from user message."""
        import re
        now = tz_now()
        
        # Try format: d/m or dd/mm
        match = re.match(r'^(\d{1,2})/(\d{1,2})$', message.strip())
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            return (day, month, now.year)
        
        # Try format: d/m/y or dd/mm/yyyy
        match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', message.strip())
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3))
            if year < 100:
                year += 2000
            return (day, month, year)
        
        return None
    
    async def _handle_select_event_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle SELECT_EVENT state - user is selecting an event from the list."""
        if not context.events_on_day:
            context.reset()
            return self._build_response(
                session_id, context,
                "Session expired. Please start over.",
            )
        
        # Parse selection (number or event_N format)
        selection = None
        message_clean = message.strip().lower()
        
        # Check for button value format "event_N"
        if message_clean.startswith("event_"):
            try:
                selection = int(message_clean.replace("event_", ""))
            except ValueError:
                pass
        else:
            # Try to parse as number
            try:
                selection = int(message_clean) - 1  # Convert 1-based to 0-based
            except ValueError:
                pass
        
        # Validate selection
        if selection is None or selection < 0 or selection >= len(context.events_on_day):
            # Rebuild choices
            choices = []
            for i, evt in enumerate(context.events_on_day):
                label = f"{i+1}. {evt.title} ({evt.start_hour:02d}:{evt.start_minute:02d})"
                choices.append(ChoiceOption(id=f"event_{i}", label=label, value=str(i+1)))
            
            return self._build_response(
                session_id, context,
                "Please select a valid event number:",
                choices=choices,
                timeout=60
            )
        
        # Store selected event
        context.selected_event = context.events_on_day[selection]
        
        # Route based on intent
        if context.intent == IntentType.EDIT_EVENT:
            context.state = AgentState.SELECT_EDIT_FIELD
            return self._build_response(
                session_id, context,
                f"What would you like to change about \"{context.selected_event.title}\"?",
                choices=[
                    ChoiceOption(id="date", label="📅 Change date", value="date"),
                    ChoiceOption(id="time", label="🕐 Change time", value="time"),
                    ChoiceOption(id="title", label="✏️ Change title", value="title"),
                    ChoiceOption(id="cancel", label="❌ Cancel", value="cancel"),
                ],
                timeout=60
            )
        elif context.intent == IntentType.REMOVE_EVENT:
            context.state = AgentState.CONFIRM_REMOVE
            evt = context.selected_event
            return self._build_response(
                session_id, context,
                f"Are you sure you want to remove \"{evt.title}\" on {evt.day}/{evt.month}/{evt.year} at {evt.start_hour:02d}:{evt.start_minute:02d}?",
                choices=[
                    ChoiceOption(id="confirm", label="✓ Yes, remove it", value="yes"),
                    ChoiceOption(id="cancel", label="✗ No, keep it", value="no"),
                ],
                timeout=30
            )
        else:
            context.reset()
            return self._build_response(
                session_id, context,
                "Something went wrong. Please start over.",
            )
    
    async def _handle_select_edit_field_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle SELECT_EDIT_FIELD state - user is choosing what to edit."""
        if not context.selected_event:
            context.reset()
            return self._build_response(
                session_id, context,
                "Session expired. Please start over.",
            )
        
        message_lower = message.strip().lower()
        
        # Map user input to edit field
        if message_lower in ["date", "1", "📅 change date", "change date"]:
            context.edit_field = EditFieldType.DATE
            context.state = AgentState.ENTER_EDIT_VALUE
            return self._build_response(
                session_id, context,
                f"Current date: {context.selected_event.day}/{context.selected_event.month}/{context.selected_event.year}\n"
                "What's the new date? (e.g., '25/4' or 'tomorrow')",
                timeout=60
            )
        elif message_lower in ["time", "2", "🕐 change time", "change time"]:
            context.edit_field = EditFieldType.TIME
            context.state = AgentState.ENTER_EDIT_VALUE
            evt = context.selected_event
            return self._build_response(
                session_id, context,
                f"Current time: {evt.start_hour:02d}:{evt.start_minute:02d} - {evt.end_hour:02d}:{evt.end_minute:02d}\n"
                "What's the new time? (e.g., '10:00-11:00' or '14:00 to 15:30')",
                timeout=60
            )
        elif message_lower in ["title", "3", "✏️ change title", "change title"]:
            context.edit_field = EditFieldType.TITLE
            context.state = AgentState.ENTER_EDIT_VALUE
            return self._build_response(
                session_id, context,
                f"Current title: \"{context.selected_event.title}\"\n"
                "What's the new title?",
                timeout=60
            )
        elif message_lower in ["cancel", "4", "❌ cancel"]:
            context.reset()
            return self._build_response(
                session_id, context,
                "Edit cancelled. How can I help you?",
            )
        else:
            # Try to detect if user provided actual values directly
            # e.g., "change it to 10 at 20:00-23:00" or "move to tomorrow 14:00-16:00"
            combined_result = self._parse_combined_edit_input(message)
            if combined_result:
                # User provided both date and time in one message
                new_date, new_time = combined_result
                evt = context.selected_event
                
                # Build new_event_data with parsed values
                context.new_event_data = {
                    "day": new_date[0] if new_date else evt.day,
                    "month": new_date[1] if new_date else evt.month,
                    "year": new_date[2] if new_date else evt.year,
                    "start_hour": new_time[0] if new_time else evt.start_hour,
                    "start_minute": new_time[1] if new_time else evt.start_minute,
                    "end_hour": new_time[2] if new_time else evt.end_hour,
                    "end_minute": new_time[3] if new_time else evt.end_minute,
                }
                
                return await self._check_edit_conflict_and_apply(session_id, context)
            
            # Check if user provided just a time range (e.g., "20:00-23:00")
            time_only = self._parse_time_for_edit(message)
            if time_only:
                evt = context.selected_event
                context.new_event_data = {
                    "day": evt.day,
                    "month": evt.month,
                    "year": evt.year,
                    "start_hour": time_only[0],
                    "start_minute": time_only[1],
                    "end_hour": time_only[2],
                    "end_minute": time_only[3],
                }
                return await self._check_edit_conflict_and_apply(session_id, context)
            
            # Check if user provided just a date (e.g., "tomorrow", "10/4")
            date_only = self._parse_date_for_edit(message)
            if date_only:
                evt = context.selected_event
                context.new_event_data = {
                    "day": date_only[0],
                    "month": date_only[1],
                    "year": date_only[2],
                    "start_hour": evt.start_hour,
                    "start_minute": evt.start_minute,
                    "end_hour": evt.end_hour,
                    "end_minute": evt.end_minute,
                }
                return await self._check_edit_conflict_and_apply(session_id, context)
            
            # Try to detect intent from keywords
            if any(word in message_lower for word in ["date", "day", "when"]):
                context.edit_field = EditFieldType.DATE
                context.state = AgentState.ENTER_EDIT_VALUE
                return self._build_response(
                    session_id, context,
                    f"Current date: {context.selected_event.day}/{context.selected_event.month}/{context.selected_event.year}\n"
                    "What's the new date? (e.g., '25/4' or 'tomorrow')",
                    timeout=60
                )
            elif any(word in message_lower for word in ["time", "hour", "start", "end"]):
                context.edit_field = EditFieldType.TIME
                context.state = AgentState.ENTER_EDIT_VALUE
                evt = context.selected_event
                return self._build_response(
                    session_id, context,
                    f"Current time: {evt.start_hour:02d}:{evt.start_minute:02d} - {evt.end_hour:02d}:{evt.end_minute:02d}\n"
                    "What's the new time? (e.g., '10:00-11:00' or '14:00 to 15:30')",
                    timeout=60
                )
            elif any(word in message_lower for word in ["title", "name", "call"]):
                context.edit_field = EditFieldType.TITLE
                context.state = AgentState.ENTER_EDIT_VALUE
                return self._build_response(
                    session_id, context,
                    f"Current title: \"{context.selected_event.title}\"\n"
                    "What's the new title?",
                    timeout=60
                )
            
            # Use LLM as final fallback to parse complex input
            success, parsed_data, error = await self.llm.parse_edit_field(message)
            if success and parsed_data:
                field = parsed_data.get("field")
                evt = context.selected_event
                
                if field == "cancel":
                    context.reset()
                    return self._build_response(
                        session_id, context,
                        "Edit cancelled. How can I help you?",
                    )
                
                if field == "title":
                    new_title = parsed_data.get("new_title")
                    if new_title:
                        # Apply title change directly
                        updated = await self.repo.update_event(evt.event_id, title=new_title)
                        context.reset()
                        return self._build_response(
                            session_id, context,
                            f"✓ Title updated to \"{new_title}\"",
                            event_updated=updated
                        )
                    else:
                        context.edit_field = EditFieldType.TITLE
                        context.state = AgentState.ENTER_EDIT_VALUE
                        return self._build_response(
                            session_id, context,
                            f"Current title: \"{evt.title}\"\nWhat's the new title?",
                            timeout=60
                        )
                
                if field in ["date", "time", "both"]:
                    # Build new_event_data from parsed values
                    new_day = parsed_data.get("new_day") or evt.day
                    new_month = parsed_data.get("new_month") or evt.month
                    new_year = parsed_data.get("new_year") or evt.year
                    new_start_hour = parsed_data.get("new_start_hour")
                    new_start_minute = parsed_data.get("new_start_minute")
                    new_end_hour = parsed_data.get("new_end_hour")
                    new_end_minute = parsed_data.get("new_end_minute")
                    
                    # If time values were provided
                    if new_start_hour is not None:
                        context.new_event_data = {
                            "day": new_day,
                            "month": new_month,
                            "year": new_year,
                            "start_hour": new_start_hour,
                            "start_minute": new_start_minute or 0,
                            "end_hour": new_end_hour or (new_start_hour + 1),
                            "end_minute": new_end_minute or 0,
                        }
                        return await self._check_edit_conflict_and_apply(session_id, context)
                    
                    # If only date was provided
                    if field == "date" and parsed_data.get("new_day"):
                        context.new_event_data = {
                            "day": new_day,
                            "month": new_month,
                            "year": new_year,
                            "start_hour": evt.start_hour,
                            "start_minute": evt.start_minute,
                            "end_hour": evt.end_hour,
                            "end_minute": evt.end_minute,
                        }
                        return await self._check_edit_conflict_and_apply(session_id, context)
                    
                    # User said "date" or "time" but didn't provide values - ask for them
                    if field == "date":
                        context.edit_field = EditFieldType.DATE
                        context.state = AgentState.ENTER_EDIT_VALUE
                        return self._build_response(
                            session_id, context,
                            f"Current date: {evt.day}/{evt.month}/{evt.year}\nWhat's the new date?",
                            timeout=60
                        )
                    elif field == "time":
                        context.edit_field = EditFieldType.TIME
                        context.state = AgentState.ENTER_EDIT_VALUE
                        return self._build_response(
                            session_id, context,
                            f"Current time: {evt.start_hour:02d}:{evt.start_minute:02d} - {evt.end_hour:02d}:{evt.end_minute:02d}\nWhat's the new time?",
                            timeout=60
                        )
            
            # If LLM also failed, show options
            return self._build_response(
                session_id, context,
                "What would you like to change?",
                choices=[
                    ChoiceOption(id="date", label="📅 Change date", value="date"),
                    ChoiceOption(id="time", label="🕐 Change time", value="time"),
                    ChoiceOption(id="title", label="✏️ Change title", value="title"),
                    ChoiceOption(id="cancel", label="❌ Cancel", value="cancel"),
                ],
                timeout=60
            )
    
    def _parse_combined_edit_input(self, message: str) -> Optional[Tuple[Optional[Tuple[int, int, int]], Optional[Tuple[int, int, int, int]]]]:
        """
        Parse combined date and time from user input like:
        - "change it to 10 at 20:00-23:00" (day 10, time 20:00-23:00)
        - "move to tomorrow 14:00-16:00"
        - "10/4 at 9:00-10:00"
        Returns (date_tuple, time_tuple) or None if can't parse either.
        """
        import re
        
        # Try to extract time range first
        time_match = re.search(r'(\d{1,2}):(\d{2})\s*[-–to]+\s*(\d{1,2}):(\d{2})', message)
        time_tuple = None
        if time_match:
            time_tuple = (
                int(time_match.group(1)),
                int(time_match.group(2)),
                int(time_match.group(3)),
                int(time_match.group(4))
            )
        
        # Remove the time part for date parsing
        message_without_time = message
        if time_match:
            message_without_time = message[:time_match.start()] + message[time_match.end():]
        
        # Try to extract date
        date_tuple = None
        message_lower = message_without_time.lower()
        
        # Check for relative dates
        now = tz_now()
        if "tomorrow" in message_lower:
            tomorrow = now + timedelta(days=1)
            date_tuple = (tomorrow.day, tomorrow.month, tomorrow.year)
        elif "today" in message_lower:
            date_tuple = (now.day, now.month, now.year)
        else:
            # Check for day number patterns like "to 10", "day 10", "the 10th"
            day_match = re.search(r'(?:to|day|the)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s|$|[^/\d])', message_lower)
            if day_match:
                day = int(day_match.group(1))
                if 1 <= day <= 31:
                    date_tuple = (day, now.month, now.year)
            
            # Check for d/m format
            if not date_tuple:
                date_match = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', message_without_time)
                if date_match:
                    day = int(date_match.group(1))
                    month = int(date_match.group(2))
                    year = int(date_match.group(3)) if date_match.group(3) else now.year
                    if year < 100:
                        year += 2000
                    date_tuple = (day, month, year)
        
        # Return if we found at least one of date or time
        if date_tuple or time_tuple:
            return (date_tuple, time_tuple)
        
        return None
    
    async def _handle_enter_edit_value_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle ENTER_EDIT_VALUE state - user is entering the new value."""
        if not context.selected_event or not context.edit_field:
            context.reset()
            return self._build_response(
                session_id, context,
                "Session expired. Please start over.",
            )
        
        evt = context.selected_event
        
        if context.edit_field == EditFieldType.TITLE:
            # Update title directly - no conflict check needed
            updated = await self.repo.update_event(
                evt.event_id,
                title=message.strip()
            )
            context.reset()
            return self._build_response(
                session_id, context,
                f"✓ Title updated to \"{message.strip()}\"",
                event_updated=updated
            )
        
        elif context.edit_field == EditFieldType.DATE:
            # Parse the new date
            new_date = self._parse_date_for_edit(message)
            if not new_date:
                return self._build_response(
                    session_id, context,
                    "I couldn't understand that date. Please try again (e.g., '25/4', 'tomorrow', 'next monday'):",
                    timeout=60
                )
            
            new_day, new_month, new_year = new_date
            
            # Store new data for conflict check
            context.new_event_data = {
                "day": new_day,
                "month": new_month,
                "year": new_year,
                "start_hour": evt.start_hour,
                "start_minute": evt.start_minute,
                "end_hour": evt.end_hour,
                "end_minute": evt.end_minute,
            }
            
            return await self._check_edit_conflict_and_apply(session_id, context)
        
        elif context.edit_field == EditFieldType.TIME:
            # Parse the new time
            new_time = self._parse_time_for_edit(message)
            if not new_time:
                return self._build_response(
                    session_id, context,
                    "I couldn't understand that time. Please try again (e.g., '10:00-11:00', '14:00 to 15:30'):",
                    timeout=60
                )
            
            start_hour, start_minute, end_hour, end_minute = new_time
            
            # Store new data for conflict check
            context.new_event_data = {
                "day": evt.day,
                "month": evt.month,
                "year": evt.year,
                "start_hour": start_hour,
                "start_minute": start_minute,
                "end_hour": end_hour,
                "end_minute": end_minute,
            }
            
            return await self._check_edit_conflict_and_apply(session_id, context)
        
        context.reset()
        return self._build_response(
            session_id, context,
            "Something went wrong. Please start over.",
        )
    
    def _parse_date_for_edit(self, message: str) -> Optional[Tuple[int, int, int]]:
        """Parse a date from user input for editing."""
        import re
        now = tz_now()
        message_lower = message.strip().lower()
        
        # Handle relative dates
        if message_lower in ["today"]:
            return (now.day, now.month, now.year)
        elif message_lower in ["tomorrow"]:
            tomorrow = now + timedelta(days=1)
            return (tomorrow.day, tomorrow.month, tomorrow.year)
        
        # Handle day names
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day_name in enumerate(day_names):
            if day_name in message_lower:
                # Find the next occurrence of this day
                current_weekday = now.weekday()
                target_weekday = i
                days_ahead = target_weekday - current_weekday
                if "next" in message_lower:
                    days_ahead += 7
                elif days_ahead <= 0:
                    days_ahead += 7
                target_date = now + timedelta(days=days_ahead)
                return (target_date.day, target_date.month, target_date.year)
        
        # Try parsing explicit dates
        return self._parse_date_input(message)
    
    def _parse_time_for_edit(self, message: str) -> Optional[Tuple[int, int, int, int]]:
        """Parse a time range from user input for editing."""
        import re
        
        # Pattern: HH:MM-HH:MM or HH:MM to HH:MM
        pattern = r'(\d{1,2}):(\d{2})\s*[-–to]+\s*(\d{1,2}):(\d{2})'
        match = re.search(pattern, message)
        if match:
            return (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4))
            )
        
        # Pattern: HH-HH (assume :00 for minutes)
        pattern = r'^(\d{1,2})\s*[-–to]+\s*(\d{1,2})$'
        match = re.search(pattern, message.strip())
        if match:
            return (
                int(match.group(1)),
                0,
                int(match.group(2)),
                0
            )
        
        return None
    
    async def _check_edit_conflict_and_apply(
        self,
        session_id: str,
        context: SessionContext
    ) -> ChatAgentResponse:
        """
        Check for conflicts and apply the edit if none found.
        
        Uses the BLACK BOX KRR approach: Prolog autonomously validates
        the new time slot against existing events.
        """
        evt = context.selected_event
        new_data = context.new_event_data
        
        # Get existing events on the new date, excluding the event being edited
        existing_events = await self.repo.get_events_on_date(
            new_data["day"], new_data["month"], new_data["year"]
        )
        existing_events = [e for e in existing_events if e["id"] != evt.event_id]
        
        # BLACK BOX: Let Prolog decide if this edit is valid
        result = self.prolog.handle_add_event(
            new_data["start_hour"], new_data["start_minute"],
            new_data["end_hour"], new_data["end_minute"],
            existing_events
        )
        
        if result.status == 'invalid':
            context.reset()
            violations_str = ", ".join(result.violations)
            return self._build_response(
                session_id, context,
                f"Cannot apply edit: constraint violations ({violations_str}). Please check the time.",
                success=False
            )
        
        if result.status == 'conflict':
            conflict = result.conflicts[0]
            
            # Store conflict info and transition to conflict resolution
            context.conflict_info = ConflictInfo(
                event_id=conflict["id"],
                title=conflict["title"],
                day=new_data["day"],
                month=new_data["month"],
                year=new_data["year"],
                start_hour=conflict["start_hour"],
                start_minute=conflict["start_minute"],
                end_hour=conflict["end_hour"],
                end_minute=conflict["end_minute"],
            )
            
            # Set up for conflict resolution
            context.target_event_id = evt.event_id
            context.event_data = EventData(
                title=evt.title,
                day=new_data["day"],
                month=new_data["month"],
                year=new_data["year"],
                start_hour=new_data["start_hour"],
                start_minute=new_data["start_minute"],
                end_hour=new_data["end_hour"],
                end_minute=new_data["end_minute"],
            )
            context.state = AgentState.CONFIRM_CONFLICT
            
            return self._build_response(
                session_id, context,
                f"⚠️ The new time conflicts with \"{conflict['title']}\" "
                f"({conflict['start_hour']:02d}:{conflict['start_minute']:02d} - "
                f"{conflict['end_hour']:02d}:{conflict['end_minute']:02d}). "
                "Would you like help finding another time?",
                choices=[
                    ChoiceOption(id="yes", label="Yes, help me find another time", value="yes"),
                    ChoiceOption(id="no", label="No, cancel the change", value="no"),
                ],
                timeout=30
            )
        
        # No conflict - show confirmation before applying
        context.state = AgentState.CONFIRM_EDIT
        
        # Build a summary of what will change
        changes = []
        if new_data["day"] != evt.day or new_data["month"] != evt.month or new_data["year"] != evt.year:
            changes.append(f"📅 Date: {evt.day}/{evt.month}/{evt.year} → {new_data['day']}/{new_data['month']}/{new_data['year']}")
        if new_data["start_hour"] != evt.start_hour or new_data["start_minute"] != evt.start_minute or \
           new_data["end_hour"] != evt.end_hour or new_data["end_minute"] != evt.end_minute:
            changes.append(f"🕐 Time: {evt.start_hour:02d}:{evt.start_minute:02d}-{evt.end_hour:02d}:{evt.end_minute:02d} → "
                          f"{new_data['start_hour']:02d}:{new_data['start_minute']:02d}-{new_data['end_hour']:02d}:{new_data['end_minute']:02d}")
        
        changes_text = "\n".join(changes) if changes else "No changes detected"
        
        return self._build_response(
            session_id, context,
            f"**Changes to \"{evt.title}\":**\n{changes_text}\n\nConfirm these changes?",
            choices=[
                ChoiceOption(id="confirm", label="✓ Confirm", value="yes"),
                ChoiceOption(id="change_date", label="📅 Change date", value="change_date"),
                ChoiceOption(id="change_time", label="🕐 Change time", value="change_time"),
                ChoiceOption(id="cancel", label="✗ Cancel", value="cancel"),
            ],
            timeout=60
        )
    
    async def _handle_confirm_edit_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle CONFIRM_EDIT state - user confirming or modifying the edit."""
        if not context.selected_event or not context.new_event_data:
            context.reset()
            return self._build_response(
                session_id, context,
                "Session expired. Please start over.",
            )
        
        message_lower = message.strip().lower()
        evt = context.selected_event
        new_data = context.new_event_data
        
        # Check for confirmation
        if message_lower in ["yes", "confirm", "y", "✓ confirm", "ok", "okay"]:
            # Apply the update
            updated = await self.repo.update_event(
                evt.event_id,
                day=new_data["day"],
                month=new_data["month"],
                year=new_data["year"],
                start_hour=new_data["start_hour"],
                start_minute=new_data["start_minute"],
                end_hour=new_data["end_hour"],
                end_minute=new_data["end_minute"],
            )
            
            context.reset()
            return self._build_response(
                session_id, context,
                f"✓ Event \"{evt.title}\" updated to {new_data['day']}/{new_data['month']}/{new_data['year']} "
                f"{new_data['start_hour']:02d}:{new_data['start_minute']:02d} - "
                f"{new_data['end_hour']:02d}:{new_data['end_minute']:02d}",
                event_updated=updated
            )
        
        elif message_lower in ["cancel", "✗ cancel", "no", "n"]:
            context.reset()
            return self._build_response(
                session_id, context,
                "Edit cancelled. How can I help you?",
            )
        
        elif message_lower in ["change_date", "📅 change date", "date"]:
            context.edit_field = EditFieldType.DATE
            context.state = AgentState.ENTER_EDIT_VALUE
            return self._build_response(
                session_id, context,
                f"Current planned date: {new_data['day']}/{new_data['month']}/{new_data['year']}\n"
                "What's the new date? (e.g., '25/4' or 'tomorrow')",
                timeout=60
            )
        
        elif message_lower in ["change_time", "🕐 change time", "time"]:
            context.edit_field = EditFieldType.TIME
            context.state = AgentState.ENTER_EDIT_VALUE
            return self._build_response(
                session_id, context,
                f"Current planned time: {new_data['start_hour']:02d}:{new_data['start_minute']:02d} - {new_data['end_hour']:02d}:{new_data['end_minute']:02d}\n"
                "What's the new time? (e.g., '10:00-11:00' or '14:00 to 15:30')",
                timeout=60
            )
        
        else:
            # Try to parse as new date/time values directly
            combined_result = self._parse_combined_edit_input(message)
            if combined_result:
                new_date, new_time = combined_result
                if new_date:
                    new_data["day"], new_data["month"], new_data["year"] = new_date
                if new_time:
                    new_data["start_hour"], new_data["start_minute"] = new_time[0], new_time[1]
                    new_data["end_hour"], new_data["end_minute"] = new_time[2], new_time[3]
                context.new_event_data = new_data
                return await self._check_edit_conflict_and_apply(session_id, context)
            
            # Check for just time
            time_only = self._parse_time_for_edit(message)
            if time_only:
                new_data["start_hour"], new_data["start_minute"] = time_only[0], time_only[1]
                new_data["end_hour"], new_data["end_minute"] = time_only[2], time_only[3]
                context.new_event_data = new_data
                return await self._check_edit_conflict_and_apply(session_id, context)
            
            # Check for just date
            date_only = self._parse_date_for_edit(message)
            if date_only:
                new_data["day"], new_data["month"], new_data["year"] = date_only
                context.new_event_data = new_data
                return await self._check_edit_conflict_and_apply(session_id, context)
            
            # Didn't understand - show options again
            changes = []
            if new_data["day"] != evt.day or new_data["month"] != evt.month or new_data["year"] != evt.year:
                changes.append(f"📅 Date: {evt.day}/{evt.month}/{evt.year} → {new_data['day']}/{new_data['month']}/{new_data['year']}")
            if new_data["start_hour"] != evt.start_hour or new_data["start_minute"] != evt.start_minute or \
               new_data["end_hour"] != evt.end_hour or new_data["end_minute"] != evt.end_minute:
                changes.append(f"🕐 Time: {evt.start_hour:02d}:{evt.start_minute:02d}-{evt.end_hour:02d}:{evt.end_minute:02d} → "
                              f"{new_data['start_hour']:02d}:{new_data['start_minute']:02d}-{new_data['end_hour']:02d}:{new_data['end_minute']:02d}")
            
            changes_text = "\n".join(changes) if changes else "No changes detected"
            
            return self._build_response(
                session_id, context,
                f"**Changes to \"{evt.title}\":**\n{changes_text}\n\nConfirm or make more changes?",
                choices=[
                    ChoiceOption(id="confirm", label="✓ Confirm", value="yes"),
                    ChoiceOption(id="change_date", label="📅 Change date", value="change_date"),
                    ChoiceOption(id="change_time", label="🕐 Change time", value="change_time"),
                    ChoiceOption(id="cancel", label="✗ Cancel", value="cancel"),
                ],
                timeout=60
            )
    
    async def _handle_confirm_remove_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle CONFIRM_REMOVE state - user is confirming event removal."""
        if not context.selected_event:
            context.reset()
            return self._build_response(
                session_id, context,
                "Session expired. Please start over.",
            )
        
        message_lower = message.strip().lower()
        
        # Check for confirmation
        if message_lower in ["yes", "confirm", "y", "✓ yes, remove it", "remove", "delete"]:
            evt = context.selected_event
            await self.repo.delete_event(evt.event_id)
            context.reset()
            return self._build_response(
                session_id, context,
                f"✓ Event \"{evt.title}\" has been removed.",
                event_deleted=evt.event_id
            )
        elif message_lower in ["no", "cancel", "n", "✗ no, keep it", "keep"]:
            context.reset()
            return self._build_response(
                session_id, context,
                "Okay, I won't remove the event. How can I help you?",
            )
        else:
            evt = context.selected_event
            return self._build_response(
                session_id, context,
                f"Are you sure you want to remove \"{evt.title}\"?",
                choices=[
                    ChoiceOption(id="confirm", label="✓ Yes, remove it", value="yes"),
                    ChoiceOption(id="cancel", label="✗ No, keep it", value="no"),
                ],
                timeout=30
            )
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _build_response(
        self,
        session_id: str,
        context: SessionContext,
        text: str,
        choices: Optional[List[ChoiceOption]] = None,
        timeout: Optional[int] = None,
        success: bool = True,
        error: Optional[str] = None,
        event_created: Optional[Dict] = None,
        event_updated: Optional[Dict] = None,
        event_deleted: Optional[str] = None,
        events_list: Optional[List[Dict]] = None,
    ) -> ChatAgentResponse:
        """Build a standardized response."""
        return ChatAgentResponse(
            session_id=session_id,
            message=AgentMessage(
                text=text,
                choices=choices,
                requires_response=choices is not None,
                timeout_seconds=timeout,
            ),
            state=SessionState(
                state=context.state.value,
                intent=context.intent.value if context.intent else None,
                event_data=context.event_data.to_dict() if context.event_data else None,
                conflict_info=context.conflict_info.to_dict() if context.conflict_info else None,
            ),
            success=success,
            error=error,
            event_created=event_created,
            event_updated=event_updated,
            event_deleted=event_deleted,
            events_list=events_list,
        )
    
    def _get_field_prompt(self, field: str) -> str:
        """Get prompt for collecting a missing field."""
        prompts = {
            "title": "What would you like to call this event?",
            "start_time": "What time should it start? (e.g., '9am', '14:30')",
            "end_time": "What time should it end? (e.g., '10am', '15:00')",
            "day": "Which day? (e.g., 'tomorrow', 'Monday', '15/4')",
        }
        return prompts.get(field, f"Please provide the {field}.")
    
    def _format_events_list(self, events: List[Dict], query_type: str) -> str:
        """Format events list for display."""
        if not events:
            return "No events found."
        
        lines = ["Here are your events:"]
        
        # Group by date if week/month
        if query_type in ["week", "month"]:
            events_by_date: Dict[str, List[Dict]] = {}
            for e in events:
                key = f"{e['day']}/{e['month']}/{e['year']}"
                if key not in events_by_date:
                    events_by_date[key] = []
                events_by_date[key].append(e)
            
            for date_key in sorted(events_by_date.keys()):
                lines.append(f"\n📅 {date_key}:")
                for e in events_by_date[date_key]:
                    time_str = f"{e['start_hour']:02d}:{e['start_minute']:02d}-{e['end_hour']:02d}:{e['end_minute']:02d}"
                    lines.append(f"  • {time_str} - {e['title']}")
        else:
            for e in events:
                time_str = f"{e['start_hour']:02d}:{e['start_minute']:02d}-{e['end_hour']:02d}:{e['end_minute']:02d}"
                lines.append(f"• {time_str} - {e['title']}")
        
        return "\n".join(lines)
