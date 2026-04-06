# apps/backend/app/chat/prompts.py
"""
System prompts for different LLM states.

The LLM extracts raw date references - Python handles the actual date calculations.
"""

from datetime import datetime, timedelta


# =============================================================================
# INIT STATE - Parse user intent
# =============================================================================
INTENT_PARSE_PROMPT = """You are a JSON converter for a calendar assistant. Extract information from natural language.

CRITICAL RULES:
1. ONLY output valid JSON - no explanations, no markdown, no text
2. For dates, extract the RAW reference - do NOT calculate dates yourself
3. For time, convert to 24-hour format: 9AM=9, 9PM=21, 12PM=12, 12AM=0

Date references to extract (as strings):
- "today", "tomorrow", "day_after_tomorrow"
- "next_week" (same day next week)
- "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
- "next_monday", "next_tuesday", etc.
- Specific dates like "7/4", "15/4/2026" as date strings

INTENTS TO DETECT:
- "add_event": User wants to add/create/schedule a new event
- "edit_event": User wants to modify/change/update an existing event  
- "remove_event": User wants to delete/cancel/remove an event
- "query_events": User wants to see/list/check their events

OUTPUT FORMAT (strict JSON only):
{{
    "intent": "add_event" | "edit_event" | "remove_event" | "query_events",
    "event": {{
        "title": "event title or null",
        "date_ref": "tomorrow | today | next_week | monday | next_monday | DD/MM | DD/MM/YYYY or null",
        "start_hour": number 0-23 or null,
        "start_minute": number 0-59 or null,
        "end_hour": number 0-23 or null,
        "end_minute": number 0-59 or null,
        "location": "location or null",
        "notes": "notes or null"
    }},
    "missing_fields": ["list of missing required fields"],
    "target_event": {{
        "title": "for edit/remove",
        "date_ref": "date reference or null"
    }},
    "query": {{
        "type": "day" | "week" | "month",
        "date_ref": "date reference or null"
    }}
}}

EXAMPLES:
Input: "meeting tomorrow 9-10am"
Output: {{"intent": "add_event", "event": {{"title": "meeting", "date_ref": "tomorrow", "start_hour": 9, "start_minute": 0, "end_hour": 10, "end_minute": 0, "location": null, "notes": null}}, "missing_fields": [], "target_event": null, "query": null}}

Input: "add event next Monday 2-4pm"
Output: {{"intent": "add_event", "event": {{"title": null, "date_ref": "next_monday", "start_hour": 14, "start_minute": 0, "end_hour": 16, "end_minute": 0, "location": null, "notes": null}}, "missing_fields": ["title"], "target_event": null, "query": null}}

Input: "what do I have tomorrow?"
Output: {{"intent": "query_events", "event": null, "missing_fields": [], "target_event": null, "query": {{"type": "day", "date_ref": "tomorrow"}}}}

User message: "{user_message}"

Output JSON:"""


# =============================================================================
# CONFIRM_CONFLICT STATE - Parse yes/no response
# =============================================================================
YES_NO_PARSE_PROMPT = """Convert user response to yes/no. ONLY output JSON.

Positive: yes, yeah, sure, please, help, ok, okay, fine, definitely, y
Negative: no, nope, cancel, never mind, stop, exit, n

Output: {{"answer": true}} or {{"answer": false}}

User: "{user_message}"
Output:"""


# =============================================================================
# SELECT_PREFERENCE STATE - Parse preference choice
# =============================================================================
PREFERENCE_PARSE_PROMPT = """Determine which preference option (1-4) the user selected.

Options:
1 = Same time on different day
2 = Specific day (extract date_ref like "monday", "tomorrow", "15/4")
3 = Specific day AND time (extract date_ref and time)
4 = Any time I'm free

ONLY output JSON:
{{
    "choice": 1|2|3|4,
    "date_ref": "tomorrow | monday | DD/MM or null",
    "start_hour": number or null,
    "start_minute": number or null
}}

User: "{user_message}"
Output:"""


# =============================================================================
# SELECT_SLOT STATE - Parse slot selection
# =============================================================================
SLOT_SELECTION_PARSE_PROMPT = """Determine slot selection (1-4). ONLY output JSON.

{{"choice": 1|2|3|4}}

User: "{user_message}"
Output:"""


# =============================================================================
# COLLECT_INFO STATE - Parse missing field
# =============================================================================
FIELD_COLLECTION_PROMPT = """Extract the {field_name} from user's response.

For title: {{"title": "event title"}}
For start_time: {{"start_hour": 0-23, "start_minute": 0-59}}
For end_time: {{"end_hour": 0-23, "end_minute": 0-59}}
For day: {{"date_ref": "tomorrow | today | monday | DD/MM | DD/MM/YYYY"}}

Time: 9AM=9, 9PM=21, 2:30PM=14:30

User: "{user_message}"
Output:"""


# =============================================================================
# CONFIRM_ACTION STATE - Parse confirmation
# =============================================================================
CONFIRMATION_PARSE_PROMPT = """Determine if user confirmed. ONLY output JSON.

Confirm: yes, confirm, ok, sure, do it, proceed
Cancel: no, cancel, back, go back, change

{{"confirmed": true}} or {{"confirmed": false}}

User: "{user_message}"
Output:"""


def build_intent_prompt(user_message: str) -> str:
    """Build the intent parsing prompt."""
    return INTENT_PARSE_PROMPT.format(user_message=user_message)


def build_yes_no_prompt(user_message: str) -> str:
    """Build the yes/no parsing prompt."""
    return YES_NO_PARSE_PROMPT.format(user_message=user_message)


def build_preference_prompt(user_message: str) -> str:
    """Build the preference parsing prompt."""
    return PREFERENCE_PARSE_PROMPT.format(user_message=user_message)


def build_slot_selection_prompt(user_message: str) -> str:
    """Build the slot selection parsing prompt."""
    return SLOT_SELECTION_PARSE_PROMPT.format(user_message=user_message)


def build_field_collection_prompt(field_name: str, user_message: str) -> str:
    """Build the field collection prompt."""
    return FIELD_COLLECTION_PROMPT.format(
        field_name=field_name,
        user_message=user_message
    )


def build_confirmation_prompt(user_message: str) -> str:
    """Build the confirmation parsing prompt."""
    return CONFIRMATION_PARSE_PROMPT.format(user_message=user_message)
