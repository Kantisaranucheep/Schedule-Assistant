"""Chat executor - handles intent execution in chat conversations."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.chat_state_manager import (
    ChatStateManager,
    ConversationStateEnum,
    get_chat_state_manager,
)
from app.agent.chat_intent_parser import get_chat_intent_parser
from app.agent.schemas import IntentType
from app.services.event_service import EventService
from app.services.availability_service import AvailabilityService
from app.integrations.prolog_client import get_prolog_client
from app.schemas.event import EventCreate, EventUpdate


class ChatExecutor:
    """Execute chat-specific intents with state transitions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.state_manager = get_chat_state_manager()
        self.intent_parser = get_chat_intent_parser()
        self.event_service = EventService(db)
        self.availability_service = AvailabilityService(db)
        self.prolog_client = get_prolog_client()

    async def execute(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        current_state: ConversationStateEnum,
        user_message: str,
        current_date: Optional[str] = None,
        timezone: str = "Asia/Bangkok",
    ) -> Dict[str, Any]:
        """
        Execute user message in chat context.

        Returns response with:
        - text: Agent response text
        - state: New conversation state
        - buttons: Optional interactive buttons
        - error: Optional error message
        """
        try:
            # Get current date if not provided
            if not current_date:
                from zoneinfo import ZoneInfo
                tz = ZoneInfo(timezone)
                current_date = datetime.now(tz).strftime("%Y-%m-%d")

            # Parse user message with state context
            parse_result = await self.intent_parser.parse_with_state(
                text=user_message,
                current_state=current_state,
                current_date=current_date,
                timezone=timezone,
            )

            if not parse_result["success"]:
                return {
                    "text": "I didn't understand that. Could you please rephrase?",
                    "state": current_state,
                    "buttons": None,
                    "error": parse_result["error"],
                }

            intent_data = parse_result.get("intent", {})
            intent_type = intent_data.get("intent_type")
            confidence = intent_data.get("confidence", 0.0)

            # Low confidence - ask for clarification
            if confidence < 0.7:
                clarification = intent_data.get("clarification_question")
                return {
                    "text": clarification or "Could you provide more details?",
                    "state": current_state,
                    "buttons": None,
                }

            # Route to handler based on current state
            if current_state == ConversationStateEnum.INITIAL:
                return await self._handle_initial_state(
                    session_id, user_id, calendar_id, intent_type, intent_data
                )
            elif current_state == ConversationStateEnum.CHECK_CONFLICT:
                return await self._handle_conflict_response(
                    session_id, user_id, calendar_id, user_message
                )
            elif current_state == ConversationStateEnum.STRATEGY_CHOICE:
                return await self._handle_strategy_choice(
                    session_id, user_id, calendar_id, user_message
                )
            elif current_state == ConversationStateEnum.PREFERENCE_SELECT:
                return await self._handle_preference_select(
                    session_id, user_id, calendar_id, user_message
                )
            elif current_state == ConversationStateEnum.SELECTING_OPTION:
                return await self._handle_option_select(
                    session_id, user_id, calendar_id, user_message
                )
            elif current_state == ConversationStateEnum.CONFIRMING:
                return await self._handle_confirmation(
                    session_id, user_id, calendar_id, user_message
                )
            else:
                return {
                    "text": "Invalid state. Restarting conversation.",
                    "state": ConversationStateEnum.INITIAL,
                    "buttons": None,
                }

        except Exception as e:
            return {
                "text": f"An error occurred: {str(e)}",
                "state": current_state,
                "buttons": None,
                "error": str(e),
            }

    # ========================================================================
    # State Handlers
    # ========================================================================

    async def _handle_initial_state(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        intent_type: str,
        intent_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle user input in INITIAL state."""

        if intent_type == IntentType.ADD_EVENT_CHAT.value:
            return await self._execute_add_event_chat(
                session_id, user_id, calendar_id, intent_data
            )
        elif intent_type == IntentType.EDIT_EVENT_CHAT.value:
            return await self._execute_edit_event_chat(
                session_id, user_id, calendar_id, intent_data
            )
        elif intent_type == IntentType.REMOVE_EVENT_CHAT.value:
            return await self._execute_remove_event_chat(
                session_id, user_id, calendar_id, intent_data
            )
        elif intent_type == IntentType.UPDATE_DAILY_CHAT.value:
            return await self._execute_update_daily(
                session_id, user_id, calendar_id, intent_data
            )
        else:
            return {
                "text": "I'm not sure what you'd like me to do. Try asking to add, edit, remove, or list events.",
                "state": ConversationStateEnum.INITIAL,
                "buttons": None,
            }

    async def _handle_conflict_response(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        user_message: str,
    ) -> Dict[str, Any]:
        """Handle yes/no response in CHECK_CONFLICT state."""
        session = self.state_manager.get_session(session_id)
        if not session:
            return {"text": "Session expired.", "state": ConversationStateEnum.INITIAL}

        is_affirmative = await self.intent_parser.parse_affirmative(user_message)
        is_negative = await self.intent_parser.parse_negative(user_message)

        if is_affirmative:
            # User wants help - show strategy options
            self.state_manager.update_state(session_id, ConversationStateEnum.STRATEGY_CHOICE)
            return {
                "text": "I can help! Would you like me to:\n1) Find a different time for your new event\n2) Move the conflicting event",
                "state": ConversationStateEnum.STRATEGY_CHOICE,
                "buttons": [
                    {"label": "Find a slot for new event", "value": "1"},
                    {"label": "Move the existing event", "value": "2"},
                ],
            }
        elif is_negative:
            # User doesn't want help - cancel
            self.state_manager.update_state(session_id, ConversationStateEnum.CANCELLED)
            return {
                "text": "Understood. Your new event was not created. Let me know if you need anything else.",
                "state": ConversationStateEnum.CANCELLED,
                "buttons": None,
            }
        else:
            # Unclear - ask again
            return {
                "text": "I didn't catch that. Would you like me to help reschedule? (Yes/No)",
                "state": ConversationStateEnum.CHECK_CONFLICT,
                "buttons": [
                    {"label": "Yes, help me", "value": "yes"},
                    {"label": "No, cancel", "value": "no"},
                ],
            }

    async def _handle_strategy_choice(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        user_message: str,
    ) -> Dict[str, Any]:
        """Handle strategy choice (1 or 2) in STRATEGY_CHOICE state."""
        session = self.state_manager.get_session(session_id)
        if not session:
            return {"text": "Session expired.", "state": ConversationStateEnum.INITIAL}

        strategy = await self.intent_parser.parse_numbered_option(user_message, max_option=2)

        if strategy == 1:
            # Find slot for new event
            session.intent_data["strategy"] = "find_slot"
            self.state_manager.update_state(session_id, ConversationStateEnum.PREFERENCE_SELECT)
            return {
                "text": "What's your preference?\n1) Same time on different day\n2) Specific day\n3) Specific date & time\n4) Any available time",
                "state": ConversationStateEnum.PREFERENCE_SELECT,
                "buttons": [
                    {"label": "Same time, different day", "value": "1"},
                    {"label": "Specific day", "value": "2"},
                    {"label": "Specific date & time", "value": "3"},
                    {"label": "Any available time", "value": "4"},
                ],
            }
        elif strategy == 2:
            # Move existing event
            session.intent_data["strategy"] = "move_event"
            self.state_manager.update_state(session_id, ConversationStateEnum.PREFERENCE_SELECT)
            return {
                "text": "Where should I move the conflicting event?\n1) Same time on different day\n2) Specific day\n3) Specific date & time\n4) Any available time",
                "state": ConversationStateEnum.PREFERENCE_SELECT,
                "buttons": [
                    {"label": "Same time, different day", "value": "1"},
                    {"label": "Specific day", "value": "2"},
                    {"label": "Specific date & time", "value": "3"},
                    {"label": "Any available time", "value": "4"},
                ],
            }
        else:
            return {
                "text": "Please choose option 1 or 2.",
                "state": ConversationStateEnum.STRATEGY_CHOICE,
                "buttons": [
                    {"label": "Find slot for new event", "value": "1"},
                    {"label": "Move existing event", "value": "2"},
                ],
            }

    async def _handle_preference_select(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        user_message: str,
    ) -> Dict[str, Any]:
        """Handle preference selection (1-4) in PREFERENCE_SELECT state."""
        session = self.state_manager.get_session(session_id)
        if not session:
            return {"text": "Session expired.", "state": ConversationStateEnum.INITIAL}

        preference = await self.intent_parser.parse_numbered_option(user_message, max_option=4)

        if preference not in [1, 2, 3, 4]:
            return {
                "text": "Please choose option 1, 2, 3, or 4.",
                "state": ConversationStateEnum.PREFERENCE_SELECT,
            }

        session.intent_data["preference"] = preference

        if preference == 1:
            # Same time, different day - query Prolog for 3 available days
            alternatives = await self._query_prolog_alternatives(
                session.conflict_info,
                calendar_id,
                preference,
                count=3,
            )
            session.set_options(alternatives or [])
            self.state_manager.update_state(session_id, ConversationStateEnum.SELECTING_OPTION)

            if not alternatives:
                return {
                    "text": "I couldn't find any available days at that time. Let's try another approach.",
                    "state": ConversationStateEnum.PREFERENCE_SELECT,
                }

            buttons = []
            for i, alt in enumerate(alternatives[:3], 1):
                buttons.append({"label": f"{i}. {alt.get('label', '')}", "value": str(i)})
            buttons.append({"label": "More options", "value": "4"})

            return {
                "text": f"Here are available days:\n" + "\n".join(
                    [f"{i}. {alt.get('label', '')}" for i, alt in enumerate(alternatives[:3], 1)]
                ),
                "state": ConversationStateEnum.SELECTING_OPTION,
                "buttons": buttons,
            }

        elif preference == 2:
            # Specific day - ask user for day
            return {
                "text": "Which day would you prefer? (Please provide date YYYY-MM-DD or describe like 'tomorrow', 'next Monday')",
                "state": ConversationStateEnum.SELECTING_OPTION,
                "buttons": None,  # Free-form input
            }

        elif preference == 3:
            # Specific date and time - ask user
            return {
                "text": "What specific date and time? (Please provide like '2024-01-20 14:00-15:00')",
                "state": ConversationStateEnum.SELECTING_OPTION,
                "buttons": None,  # Free-form input
            }

        elif preference == 4:
            # Any available time - query Prolog for 3 earliest available
            alternatives = await self._query_prolog_alternatives(
                session.conflict_info,
                calendar_id,
                preference,
                count=3,
            )
            session.set_options(alternatives or [])
            self.state_manager.update_state(session_id, ConversationStateEnum.SELECTING_OPTION)

            if not alternatives:
                return {
                    "text": "I couldn't find any available time slots. Please try another approach.",
                    "state": ConversationStateEnum.PREFERENCE_SELECT,
                }

            buttons = []
            for i, alt in enumerate(alternatives[:3], 1):
                buttons.append({"label": f"{i}. {alt.get('label', '')}", "value": str(i)})
            buttons.append({"label": "More options", "value": "4"})

            return {
                "text": f"Here are available time slots:\n" + "\n".join(
                    [f"{i}. {alt.get('label', '')}" for i, alt in enumerate(alternatives[:3], 1)]
                ),
                "state": ConversationStateEnum.SELECTING_OPTION,
                "buttons": buttons,
            }

    async def _handle_option_select(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        user_message: str,
    ) -> Dict[str, Any]:
        """Handle option selection in SELECTING_OPTION state."""
        session = self.state_manager.get_session(session_id)
        if not session:
            return {"text": "Session expired.", "state": ConversationStateEnum.INITIAL}

        # Try to parse numbered option
        selection = await self.intent_parser.parse_numbered_option(user_message, max_option=4)

        if selection == 4:
            # Show more options - query Prolog again with offset
            alternatives = await self._query_prolog_alternatives(
                session.conflict_info,
                calendar_id,
                session.intent_data.get("preference", 1),
                count=3,
                offset=3,  # Skip first 3
            )
            session.set_options(alternatives or [])

            buttons = []
            for i, alt in enumerate(alternatives[:3], 1):
                buttons.append({"label": f"{i}. {alt.get('label', '')}", "value": str(i)})
            buttons.append({"label": "More options", "value": "4"})

            return {
                "text": f"Here are more options:\n" + "\n".join(
                    [f"{i}. {alt.get('label', '')}" for i, alt in enumerate(alternatives[:3], 1)]
                ),
                "state": ConversationStateEnum.SELECTING_OPTION,
                "buttons": buttons,
            }

        elif selection in [1, 2, 3]:
            # User selected option - store and move to confirmation
            if selection <= len(session.options):
                session.intent_data["selected_option"] = session.options[selection - 1]
                self.state_manager.update_state(session_id, ConversationStateEnum.CONFIRMING)

                # Build confirmation message
                new_event = session.intent_data.get("new_event", {})
                old_event = session.conflict_info
                selected = session.intent_data.get("selected_option", {})

                confirm_text = f"Confirm these changes:\n"
                if session.intent_data.get("strategy") == "find_slot":
                    confirm_text += f"❌ Cancel: '{old_event.get('title')}' ({old_event.get('start_time')} - {old_event.get('end_time')})\n"
                    confirm_text += f"✅ Create: '{new_event.get('title')}' {selected.get('label', '')}"
                else:  # move_event
                    confirm_text += f"🔄 Move: '{old_event.get('title')}'\nFrom: {old_event.get('start_time')} - {old_event.get('end_time')}\nTo: {selected.get('label', '')}"

                return {
                    "text": confirm_text,
                    "state": ConversationStateEnum.CONFIRMING,
                    "buttons": [
                        {"label": "Confirm", "value": "confirm"},
                        {"label": "Cancel", "value": "cancel"},
                    ],
                }
            else:
                return {"text": "Invalid option.", "state": ConversationStateEnum.SELECTING_OPTION}
        else:
            # Free-form input for specific day/time
            if session.intent_data.get("preference") == 2:
                # Handle specific day input
                session.intent_data["user_provided_day"] = user_message
                # Query Prolog for time slots on that day
                alternatives = await self._query_prolog_alternatives_for_day(
                    calculator_id=calendar_id,
                    provided_day=user_message,
                    event_duration=session.intent_data.get("event_duration", 60),
                    count=3,
                )
                session.set_options(alternatives or [])

                buttons = []
                for i, alt in enumerate(alternatives[:3], 1):
                    buttons.append({"label": f"{i}. {alt.get('label', '')}", "value": str(i)})

                return {
                    "text": f"Available time slots on {user_message}:\n" + "\n".join(
                        [f"{i}. {alt.get('label', '')}" for i, alt in enumerate(alternatives[:3], 1)]
                    ),
                    "state": ConversationStateEnum.SELECTING_OPTION,
                    "buttons": buttons,
                }

    async def _handle_confirmation(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        user_message: str,
    ) -> Dict[str, Any]:
        """Handle confirmation in CONFIRMING state."""
        session = self.state_manager.get_session(session_id)
        if not session:
            return {"text": "Session expired.", "state": ConversationStateEnum.INITIAL}

        is_confirmed = await self.intent_parser.parse_affirmative(user_message)
        is_cancelled = await self.intent_parser.parse_negative(user_message)

        if is_confirmed:
            # Execute the changes
            strategy = session.intent_data.get("strategy")
            new_event = session.intent_data.get("new_event", {})
            old_event = session.conflict_info

            try:
                if strategy == "find_slot":
                    # Remove old event
                    if old_event.get("event_id"):
                        await self.event_service.delete(uuid.UUID(old_event["event_id"]))
                    # Create new event
                    selected = session.intent_data.get("selected_option", {})
                    # Update new_event with selected time
                    new_event.update(selected)
                    await self.event_service.create(EventCreate(**new_event))
                else:  # move_event
                    # Move old event to new time
                    selected = session.intent_data.get("selected_option", {})
                    if old_event.get("event_id"):
                        await self.event_service.update(
                            uuid.UUID(old_event["event_id"]),
                            EventUpdate(
                                start_time=selected.get("start_time"),
                                end_time=selected.get("end_time"),
                            ),
                        )
                    # Create new event
                    await self.event_service.create(EventCreate(**new_event))

                self.state_manager.update_state(session_id, ConversationStateEnum.COMPLETED)
                return {
                    "text": "✅ Done! Your events have been updated.",
                    "state": ConversationStateEnum.COMPLETED,
                    "buttons": None,
                }
            except Exception as e:
                return {
                    "text": f"Error updating events: {str(e)}",
                    "state": ConversationStateEnum.CONFIRMING,
                    "error": str(e),
                }

        elif is_cancelled:
            self.state_manager.update_state(session_id, ConversationStateEnum.CANCELLED)
            return {
                "text": "Changes cancelled. Let me know if you need anything else.",
                "state": ConversationStateEnum.CANCELLED,
                "buttons": None,
            }
        else:
            return {
                "text": "Please confirm (yes/no).",
                "state": ConversationStateEnum.CONFIRMING,
                "buttons": [
                    {"label": "Confirm", "value": "confirm"},
                    {"label": "Cancel", "value": "cancel"},
                ],
            }

    # ========================================================================
    # Core Execution Methods (Initial State Intents)
    # ========================================================================

    async def _execute_add_event_chat(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        intent_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute ADD_EVENT_CHAT - check for conflicts."""
        try:
            data = intent_data.get("data", {})

            # Parse datetime
            date_str = data.get("date")
            start_time = data.get("start_time", "09:00")
            end_time = data.get("end_time", "10:00")

            # Resolve relative dates (e.g., "tomorrow" -> actual date)
            # In real implementation, use proper date parsing library
            if date_str == "tomorrow":
                date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

            # Check for conflicts
            from zoneinfo import ZoneInfo
            tz = ZoneInfo("Asia/Bangkok")
            naive_start = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
            naive_end = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")
            start_dt = naive_start.replace(tzinfo=tz)
            end_dt = naive_end.replace(tzinfo=tz)

            conflicts = await self.event_service.check_conflicts(calendar_id, start_dt, end_dt)

            session = self.state_manager.get_or_create_session(session_id, user_id, calendar_id)
            session.intent_data["new_event"] = {
                "calendar_id": str(calendar_id),
                "title": data.get("title"),
                "start_time": start_dt,
                "end_time": end_dt,
                "location": data.get("location"),
            }
            session.intent_data["event_duration"] = int((end_dt - start_dt).total_seconds() / 60)

            if conflicts:
                # Store conflict info and move to CHECK_CONFLICT state
                conflict_event = conflicts[0]
                session.set_conflict_info(
                    event_id=str(conflict_event.id),
                    title=conflict_event.title,
                    start=conflict_event.start_time.strftime("%H:%M"),
                    end=conflict_event.end_time.strftime("%H:%M"),
                )
                self.state_manager.update_state(session_id, ConversationStateEnum.CHECK_CONFLICT)

                return {
                    "text": f"I found a conflict with '{conflict_event.title}' ({conflict_event.start_time.strftime('%H:%M')}-{conflict_event.end_time.strftime('%H:%M')}). Would you like me to help reschedule?",
                    "state": ConversationStateEnum.CHECK_CONFLICT,
                    "buttons": [
                        {"label": "Yes, help me", "value": "yes"},
                        {"label": "No, thanks", "value": "no"},
                    ],
                }
            else:
                # No conflicts - create event immediately
                await self.event_service.create(EventCreate(**session.intent_data["new_event"]))
                self.state_manager.update_state(session_id, ConversationStateEnum.COMPLETED)

                return {
                    "text": f"✅ Created '{data.get('title')}' on {date_str} from {start_time} to {end_time}.",
                    "state": ConversationStateEnum.COMPLETED,
                    "buttons": None,
                }

        except Exception as e:
            return {
                "text": f"Error creating event: {str(e)}",
                "state": ConversationStateEnum.INITIAL,
                "error": str(e),
            }

    async def _execute_edit_event_chat(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        intent_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute EDIT_EVENT_CHAT."""
        return {
            "text": "Edit event feature coming soon.",
            "state": ConversationStateEnum.INITIAL,
            "buttons": None,
        }

    async def _execute_remove_event_chat(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        intent_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute REMOVE_EVENT_CHAT."""
        return {
            "text": "Remove event feature coming soon.",
            "state": ConversationStateEnum.INITIAL,
            "buttons": None,
        }

    async def _execute_update_daily(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        calendar_id: uuid.UUID,
        intent_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute UPDATE_DAILY_CHAT - list events for day/week/month."""
        try:
            data = intent_data.get("data", {})
            date_range = data.get("date_range", "today").lower()

            today = datetime.now()

            if date_range == "today":
                start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                end = today.replace(hour=23, minute=59, second=59, microsecond=0)
            elif date_range == "this week":
                start = today - timedelta(days=today.weekday())
                end = start + timedelta(days=7)
            elif date_range == "this month":
                start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if today.month == 12:
                    end = today.replace(year=today.year + 1, month=1, day=1)
                else:
                    end = today.replace(month=today.month + 1, day=1)
            else:
                start = today
                end = today + timedelta(days=1)

            # Get events in range
            events = await self.event_service.get_by_calendar(calendar_id, start, end)

            # Format as table: Name | Start Time | End Time
            if not events:
                return {
                    "text": f"No events found for {date_range}.",
                    "state": ConversationStateEnum.INITIAL,
                    "buttons": None,
                }

            # Build table
            events_sorted = sorted(events, key=lambda e: e.start_time)
            table_lines = ["**Events for " + date_range + ":**\n"]
            table_lines.append("| Name | Start | End |")
            table_lines.append("|------|-------|-----|")

            for event in events_sorted:
                table_lines.append(
                    f"| {event.title} | {event.start_time.strftime('%H:%M')} | {event.end_time.strftime('%H:%M')} |"
                )

            self.state_manager.update_state(session_id, ConversationStateEnum.INITIAL)

            return {
                "text": "\n".join(table_lines),
                "state": ConversationStateEnum.INITIAL,
                "table": {
                    "headers": ["Name", "Start", "End"],
                    "rows": [
                        [
                            e.title,
                            e.start_time.strftime("%H:%M"),
                            e.end_time.strftime("%H:%M"),
                        ]
                        for e in events_sorted
                    ],
                },
                "buttons": None,
            }

        except Exception as e:
            return {
                "text": f"Error fetching events: {str(e)}",
                "state": ConversationStateEnum.INITIAL,
                "error": str(e),
            }

    # ========================================================================
    # Helper Methods - Prolog Queries
    # ========================================================================

    async def _query_prolog_alternatives(
        self,
        conflict_info: Dict[str, Any],
        calendar_id: uuid.UUID,
        preference: int,
        count: int = 3,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query Prolog for alternative time slots."""
        # Stub implementation - would call actual Prolog
        # For now, return mock data
        if preference == 1:  # Same time, different day
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            return [
                {"label": f"{day} 9:00-10:00", "day": day, "start_time": "09:00", "end_time": "10:00"}
                for day in days[offset : offset + count]
            ]
        elif preference == 4:  # Any time
            slots = [
                {"label": "Tomorrow 10:00-11:00", "day": "tomorrow", "start_time": "10:00", "end_time": "11:00"},
                {"label": "Tomorrow 14:00-15:00", "day": "tomorrow", "start_time": "14:00", "end_time": "15:00"},
                {"label": "Next Monday 9:00-10:00", "day": "next_monday", "start_time": "09:00", "end_time": "10:00"},
            ]
            return slots[offset : offset + count]

        return []

    async def _query_prolog_alternatives_for_day(
        self,
        calendar_id: uuid.UUID,
        provided_day: str,
        event_duration: int,
        count: int = 3,
    ) -> List[Dict[str, Any]]:
        """Query Prolog for time slots on specific day."""
        # Stub implementation
        return [
            {"label": "9:00-10:00", "start_time": "09:00", "end_time": "10:00"},
            {"label": "14:00-15:00", "start_time": "14:00", "end_time": "15:00"},
            {"label": "16:00-17:00", "start_time": "16:00", "end_time": "17:00"},
        ]
