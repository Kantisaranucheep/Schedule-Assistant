"""Chat-specific intent parser with state-aware parsing and dynamic system prompts."""

import json
from typing import Optional, Dict, Any
from enum import Enum

from app.agent.llm_clients import get_llm_client
from app.agent.chat_state_manager import ConversationStateEnum
from app.agent.schemas import Intent, IntentType


class ChatIntentType(str, Enum):
    """Extended intent types for chat-specific operations."""
    # Core chat operations
    ADD_EVENT_CHAT = "add_event_chat"
    EDIT_EVENT_CHAT = "edit_event_chat"
    REMOVE_EVENT_CHAT = "remove_event_chat"
    UPDATE_DAILY_CHAT = "update_daily_chat"

    # Conversation flow responses
    RESPOND_AFFIRMATIVE = "respond_affirmative"
    RESPOND_NEGATIVE = "respond_negative"
    SELECT_PREFERENCE = "select_preference"
    SELECT_OPTION = "select_option"
    CONFIRM_CHANGES = "confirm_changes"

    # Unknown
    UNKNOWN = "unknown"


class ChatIntentParser:
    """Parse user input with context awareness based on conversation state."""

    def __init__(self):
        self.llm_client = get_llm_client()

    def get_system_prompt(self, state: ConversationStateEnum) -> str:
        """Get system prompt for conversation state."""
        prompts = {
            ConversationStateEnum.INITIAL: """You are a helpful calendar assistant. Help the user add, edit, remove, or check events.
Parse their request into structured JSON intent.

Return ONLY valid JSON with this structure:
{
  "intent_type": "add_event_chat" | "edit_event_chat" | "remove_event_chat" | "update_daily_chat" | "unknown",
  "confidence": 0.0 to 1.0,
  "data": { /* intent-specific fields */ },
  "clarification_question": "optional question if ambiguous"
}

**Detection rules:**
- If user asks to LIST, SHOW, or CHECK events (e.g., "what's on today", "list my schedule", "show events"), → update_daily_chat with date_range
- If user asks to ADD an event (e.g., "add meeting", "schedule", "book time"), → add_event_chat
- If user asks to EDIT/UPDATE (e.g., "move meeting", "change time"), → edit_event_chat
- If user asks to REMOVE/DELETE (e.g., "cancel event", "delete"), → remove_event_chat

For add_event_chat, extract: title, date (flexible format: "tomorrow", "2024-12-25", "next Monday", etc.), start_time (HH:MM), end_time (HH:MM), location (optional)
For edit_event_chat, extract: event_name, new_start_time, new_end_time, new_date (optional)
For remove_event_chat, extract: event_name, date (optional)
For update_daily_chat, extract: date_range ("today" | "this week" | "this month" | specific date)

**Date handling:** Accept any date format the user provides - don't force YYYY-MM-DD. The system will parse it.
""",

            ConversationStateEnum.CHECK_CONFLICT: """You are detecting if the user wants help resolving a scheduling conflict.
Listen for affirmative words (yes, help, sure, please, pls, ok, yep, yeah, absolutely, of course)
or negative words (no, nope, cancel, skip, never, don't).

Return ONLY valid JSON:
{
  "intent_type": "respond_affirmative" | "respond_negative" | "unknown",
  "confidence": 0.8 to 1.0,
  "data": {"response": user's text},
  "clarification_question": null
}

Be lenient with interpretation. "help" or any positive word = affirmative.
""",

            ConversationStateEnum.STRATEGY_CHOICE: """You are detecting if the user wants to:
1) Find a free time slot for the new event
2) Move the conflicting event to a different time

User will respond with a number (1 or 2) or descriptive text.

Return ONLY valid JSON:
{
  "intent_type": "select_option",
  "confidence": 0.85 to 1.0,
  "data": {"selected_option": 1 or 2, "strategy": "find_slot" or "move_event"},
  "clarification_question": null
}
""",

            ConversationStateEnum.PREFERENCE_SELECT: """You are detecting which preference the user selected:
1) Same time, different day
2) Specific day (I'll choose the day)
3) Specific date and time (I'll be precise)
4) Any available time

User responds with 1, 2, 3, or 4.

Return ONLY valid JSON:
{
  "intent_type": "select_preference",
  "confidence": 0.9 to 1.0,
  "data": {"selected_preference": 1 or 2 or 3 or 4},
  "clarification_question": null
}
""",

            ConversationStateEnum.SELECTING_OPTION: """You are detecting which option the user selected from a numbered list (1, 2, 3, 4).
Option 4 usually means "show more options".

Return ONLY valid JSON:
{
  "intent_type": "select_option",
  "confidence": 0.9 to 1.0,
  "data": {"selected_option": 1 or 2 or 3 or 4},
  "clarification_question": null
}
""",

            ConversationStateEnum.CONFIRMING: """You are detecting if the user confirms or cancels the proposed changes.
Listen for confirm words (yes, confirm, ok, agree, proceed, do it, go ahead)
or cancel words (no, cancel, back, change my mind, undo).

Return ONLY valid JSON:
{
  "intent_type": "confirm_changes" | "respond_negative",
  "confidence": 0.9 to 1.0,
  "data": {"confirmed": true or false},
  "clarification_question": null
}
""",
        }

        return prompts.get(state, prompts[ConversationStateEnum.INITIAL])

    async def parse_with_state(
        self,
        text: str,
        current_state: ConversationStateEnum,
        current_date: Optional[str] = None,
        timezone: str = "Asia/Bangkok",
    ) -> Dict[str, Any]:
        """Parse user input with state-aware context."""
        system_prompt = self.get_system_prompt(current_state)

        # Format current date info for context
        date_context = f"Today's date: {current_date}" if current_date else "Date context: unknown"

        user_prompt = f"""{date_context}
User timezone: {timezone}

User message: {text}

Parse this according to the current conversation state. Return ONLY valid JSON, no explanations."""

        try:
            response_text = await self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            # Extract JSON from response
            response_text = response_text.strip()

            # Try to find JSON in response (in case there's extra text)
            if response_text.startswith('{'):
                json_str = response_text
            elif '{' in response_text:
                json_str = response_text[response_text.index('{'):]
                if '}' in json_str:
                    json_str = json_str[:json_str.rindex('}') + 1]
            else:
                return {
                    "success": False,
                    "error": "No JSON in response",
                    "intent": None,
                }

            # Parse JSON
            parsed = json.loads(json_str)

            return {
                "success": True,
                "intent": parsed,
                "error": None,
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}",
                "intent": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM parsing failed: {str(e)}",
                "intent": None,
            }

    async def parse_affirmative(self, text: str) -> bool:
        """Quick check: is response affirmative? (called in CHECK_CONFLICT state)."""
        affirmative_words = [
            'yes', 'yep', 'yeah', 'ok', 'okay', 'sure', 'help', 'please',
            'pls', 'definitely', 'absolutely', 'of course', 'go ahead',
            'dae', 'udi', 'hai', 'ok na',  # Common Thai abbreviations
        ]
        text_lower = text.lower().strip()
        return any(word in text_lower for word in affirmative_words)

    async def parse_negative(self, text: str) -> bool:
        """Quick check: is response negative? (called in CHECK_CONFLICT state)."""
        negative_words = [
            'no', 'nope', 'no thanks', 'cancel', 'skip', 'never',
            'don\'t', 'dont', 'not needed', 'later',
            'mai', 'imi', 'mai sai',  # Common Thai words
        ]
        text_lower = text.lower().strip()
        return any(word in text_lower for word in negative_words)

    async def parse_numbered_option(self, text: str, max_option: int = 4) -> Optional[int]:
        """Extract numbered option (1-N) from text."""
        text_clean = text.strip()

        # Try direct number
        if text_clean.isdigit():
            num = int(text_clean)
            if 1 <= num <= max_option:
                return num

        # Try to extract number from text (e.g., "option 2" or "pick 3")
        for i in range(1, max_option + 1):
            if str(i) in text_clean:
                return i

        return None


# Singleton instance
_chat_parser: Optional[ChatIntentParser] = None


def get_chat_intent_parser() -> ChatIntentParser:
    """Get or create chat intent parser instance."""
    global _chat_parser
    if _chat_parser is None:
        _chat_parser = ChatIntentParser()
    return _chat_parser
