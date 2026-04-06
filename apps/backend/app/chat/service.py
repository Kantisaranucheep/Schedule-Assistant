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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.states import (
    AgentState, IntentType, PreferenceType, ResolutionType,
    EventData, ConflictInfo, TimeSlot, SessionContext
)
from app.chat.schemas import (
    ChatAgentResponse, AgentMessage, ChoiceOption, SessionState,
    ChatMessageRequest, ChatChoiceRequest
)
from app.chat.llm_service import LLMService
from app.chat.prolog_service import get_prolog_service, PrologService
from app.chat.event_repository import EventRepository
from app.chat.date_parser import parse_date_reference, parse_date_reference_safe


# In-memory session storage (for simplicity - not persistent)
_sessions: Dict[str, SessionContext] = {}


class ChatAgentService:
    """
    Main chat agent service implementing the state machine.
    
    State Flow:
    INIT -> [COLLECT_INFO] -> CONFIRM_CONFLICT -> CHOOSE_RESOLUTION 
         -> SELECT_PREFERENCE -> SELECT_SLOT -> CONFIRM_ACTION -> INIT
    """
    
    def __init__(self, db: AsyncSession, timezone: str = "Asia/Bangkok"):
        self.db = db
        self.timezone = timezone
        self.llm = LLMService()
        self.prolog = get_prolog_service()
        self.repo = EventRepository(db, timezone)
    
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
            elif context.state == AgentState.CONFIRM_ACTION:
                response = await self._handle_confirm_action_state(session_id, context, request.message)
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
        
        # Parse date reference using Python instead of relying on LLM
        date_ref = event_data.get("date_ref")
        if date_ref:
            parsed_date = parse_date_reference_safe(date_ref)
            if parsed_date:
                event_data["day"], event_data["month"], event_data["year"] = parsed_date
            else:
                # Invalid date reference
                return self._build_response(
                    session_id, context,
                    f"I couldn't understand the date '{date_ref}'. Please try again with something like 'tomorrow', 'next Monday', or '15/4'.",
                )
        
        # Fill in defaults for missing month/year (if not from date_ref)
        now = datetime.now()
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
        """Check for conflicts and handle appropriately."""
        event = context.event_data
        
        # Get existing events on that date
        existing_events = await self.repo.get_events_on_date(
            event.day, event.month, event.year
        )
        
        # Check for conflicts using Prolog
        result = self.prolog.check_conflict(
            event.start_hour, event.start_minute,
            event.end_hour, event.end_minute,
            existing_events
        )
        
        if result.has_conflict:
            # Store conflict info
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
            
            # Transition to CONFIRM_CONFLICT
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
        else:
            # No conflict - create the event
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
            
            # Reset to INIT
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
        """Handle edit event intent."""
        target = data.get("target_event", {})
        event_data = data.get("event", {})
        
        if not target or not target.get("title"):
            return self._build_response(
                session_id, context,
                "Which event would you like to edit? Please include the event title and date.",
            )
        
        # Find the event
        now = datetime.now()
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
        """Handle remove event intent."""
        target = data.get("target_event", {})
        
        if not target or not target.get("title"):
            return self._build_response(
                session_id, context,
                "Which event would you like to remove? Please include the event title and date.",
            )
        
        now = datetime.now()
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
        
        # Delete the event
        await self.repo.delete_event(found_event["id"])
        context.reset()
        
        return self._build_response(
            session_id, context,
            f"✓ Event \"{found_event['title']}\" has been removed.",
            event_deleted=found_event["id"]
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
        
        # Parse date reference using Python
        date_ref = query.get("date_ref")
        if date_ref:
            parsed_date = parse_date_reference_safe(date_ref)
            if parsed_date:
                day, month, year = parsed_date
            else:
                return self._build_response(
                    session_id, context,
                    f"I couldn't understand the date '{date_ref}'. Please try again.",
                )
        else:
            # Default to today
            now = datetime.now()
            day, month, year = now.day, now.month, now.year
        
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
            # Parse date reference using Python
            date_ref = data.get("date_ref")
            if date_ref:
                parsed_date = parse_date_reference_safe(date_ref)
                if parsed_date:
                    context.event_data.day, context.event_data.month, context.event_data.year = parsed_date
                else:
                    return self._build_response(
                        session_id, context,
                        f"I couldn't understand the date '{date_ref}'. Please try something like 'tomorrow', 'next Monday', or '15/4'.",
                    )
            elif "day" in data:
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
            f"I can help you in two ways:\n1. Find a time slot that fits \"{event_title}\"\n2. Move \"{conflict_title}\" to make room",
            choices=[
                ChoiceOption(id="find", label=f"Find slot for \"{event_title}\"", value="1"),
                ChoiceOption(id="move", label=f"Move \"{conflict_title}\"", value="2"),
            ],
            timeout=30
        )
    
    async def _handle_choose_resolution_state(
        self,
        session_id: str,
        context: SessionContext,
        message: str
    ) -> ChatAgentResponse:
        """Handle CHOOSE_RESOLUTION state - find slot or move event."""
        # Parse choice (1 or 2)
        choice = message.strip()
        
        if choice in ["1", "find", "first"]:
            context.resolution_type = ResolutionType.FIND_SLOT_FOR_NEW
        elif choice in ["2", "move", "second"]:
            context.resolution_type = ResolutionType.MOVE_CONFLICTING
        else:
            return self._build_response(
                session_id, context,
                "Please select option 1 or 2.",
                choices=[
                    ChoiceOption(id="find", label="1. Find slot for new event", value="1"),
                    ChoiceOption(id="move", label="2. Move conflicting event", value="2"),
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
            # Check if day was provided (as date_ref)
            date_ref = pref_data.get("date_ref")
            if date_ref:
                parsed_date = parse_date_reference_safe(date_ref)
                if parsed_date:
                    day, month, year = parsed_date
                    return await self._find_slots_on_day(
                        session_id, context, day, month, year
                    )
            # Also check for direct day/month/year (from LLM fallback)
            elif pref_data.get("day"):
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
            # Parse date reference if provided
            date_ref = pref_data.get("date_ref")
            if date_ref:
                parsed_date = parse_date_reference_safe(date_ref)
                if parsed_date and pref_data.get("start_hour") is not None:
                    pref_data["day"], pref_data["month"], pref_data["year"] = parsed_date
                    return await self._check_specific_time(
                        session_id, context, pref_data
                    )
            # Fallback to direct fields
            elif pref_data.get("day") and pref_data.get("start_hour") is not None:
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
        now = datetime.now()
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
        """Find free time slots on a specific day."""
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        
        event = context.event_data
        duration = (event.end_hour * 60 + event.end_minute) - (event.start_hour * 60 + event.start_minute)
        
        existing_events = await self.repo.get_events_on_date(day, month, year)
        
        free_slots = self.prolog.find_free_slots_on_date(
            day, month, year, duration, existing_events,
            max_results=3 + context.slot_offset
        )
        
        if len(free_slots) <= context.slot_offset:
            context.slot_offset = 0
            context.state = AgentState.SELECT_PREFERENCE
            return self._build_response(
                session_id, context,
                f"No free slots found on {day}/{month}/{year}. Please try a different day.",
                choices=[
                    ChoiceOption(id="same_time", label="1. Same time on different day", value="1"),
                    ChoiceOption(id="specific_day", label="2. Try another day", value="2"),
                    ChoiceOption(id="any_free", label="4. Any time I'm free", value="4"),
                ],
                timeout=30
            )
        
        display_slots = free_slots[context.slot_offset:context.slot_offset + 3]
        context.suggested_slots = [TimeSlot(
            day=s.day, month=s.month, year=s.year,
            start_hour=s.start_hour, start_minute=s.start_minute,
            end_hour=s.end_hour, end_minute=s.end_minute
        ) for s in display_slots]
        
        context.state = AgentState.SELECT_SLOT
        
        choices = []
        for i, slot in enumerate(display_slots):
            label = f"{i+1}. {slot.start_hour:02d}:{slot.start_minute:02d} - {slot.end_hour:02d}:{slot.end_minute:02d}"
            choices.append(ChoiceOption(id=f"slot_{i}", label=label, value=str(i+1)))
        choices.append(ChoiceOption(id="more", label="4. Show more options", value="4"))
        
        return self._build_response(
            session_id, context,
            f"Available time slots on {day}/{month}/{year}:",
            choices=choices,
            timeout=30
        )
    
    async def _check_specific_time(
        self,
        session_id: str,
        context: SessionContext,
        time_data: Dict[str, Any]
    ) -> ChatAgentResponse:
        """Check if a specific time slot is available."""
        day = time_data["day"]
        month = time_data.get("month") or datetime.now().month
        year = time_data.get("year") or datetime.now().year
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
        """Find any free slots in the next 7 days."""
        event = context.event_data
        duration = (event.end_hour * 60 + event.end_minute) - (event.start_hour * 60 + event.start_minute)
        
        now = datetime.now()
        all_slots = []
        
        # Search through next 7 days
        for i in range(7):
            check_date = now + timedelta(days=i)
            events = await self.repo.get_events_on_date(
                check_date.day, check_date.month, check_date.year
            )
            
            day_slots = self.prolog.find_free_slots_on_date(
                check_date.day, check_date.month, check_date.year,
                duration, events, max_results=5
            )
            all_slots.extend(day_slots)
            
            if len(all_slots) >= 3 + context.slot_offset:
                break
        
        if len(all_slots) <= context.slot_offset:
            context.slot_offset = 0
            return self._build_response(
                session_id, context,
                "No free slots found in the next 7 days. Your schedule is quite full!",
            )
        
        display_slots = all_slots[context.slot_offset:context.slot_offset + 3]
        context.suggested_slots = [TimeSlot(
            day=s.day, month=s.month, year=s.year,
            start_hour=s.start_hour, start_minute=s.start_minute,
            end_hour=s.end_hour, end_minute=s.end_minute
        ) for s in display_slots]
        
        context.state = AgentState.SELECT_SLOT
        
        choices = []
        for i, slot in enumerate(display_slots):
            label = f"{i+1}. {slot.day}/{slot.month} {slot.start_hour:02d}:{slot.start_minute:02d}-{slot.end_hour:02d}:{slot.end_minute:02d}"
            choices.append(ChoiceOption(id=f"slot_{i}", label=label, value=str(i+1)))
        choices.append(ChoiceOption(id="more", label="4. Show more options", value="4"))
        
        return self._build_response(
            session_id, context,
            "Here are available time slots:",
            choices=choices,
            timeout=30
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
