# apps/backend/app/chat/states.py
"""
Agent State Machine - Defines all states and transitions for the chat agent.

States:
- INIT: Parse user intent (add/edit/remove/query events)
- COLLECT_INFO: Gather missing information from user
- CONFIRM_CONFLICT: Ask if user needs help with conflict
- CHOOSE_RESOLUTION: User chooses how to resolve conflict
- SELECT_PREFERENCE: User chooses preference for finding slots
- SELECT_SLOT: User picks from suggested time slots
- CONFIRM_ACTION: Final confirmation before executing
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class AgentState(str, Enum):
    """All possible states for the chat agent."""
    
    # Initial state - parse user intent
    INIT = "init"
    
    # Collecting missing information
    COLLECT_INFO = "collect_info"
    
    # Conflict detected - asking if user needs help
    CONFIRM_CONFLICT = "confirm_conflict"
    
    # User wants help - choose between find slot or move event
    CHOOSE_RESOLUTION = "choose_resolution"
    
    # User selecting preference (same time diff day, specific day, etc.)
    SELECT_PREFERENCE = "select_preference"
    
    # User selecting from available slots (legacy fixed-duration slots)
    SELECT_SLOT = "select_slot"
    
    # User viewing free time ranges and entering a specific time
    SELECT_TIME_IN_RANGE = "select_time_in_range"
    
    # Final confirmation before action
    CONFIRM_ACTION = "confirm_action"
    
    # Waiting for button click (with timeout)
    WAITING_CHOICE = "waiting_choice"
    
    # Edit/Remove flow: User selecting which day to look at events
    SELECT_EVENT_DAY = "select_event_day"
    
    # Edit/Remove flow: User selecting which event to edit/remove
    SELECT_EVENT = "select_event"
    
    # Edit flow: User selecting which field to edit
    SELECT_EDIT_FIELD = "select_edit_field"
    
    # Edit flow: User entering new value for the field
    ENTER_EDIT_VALUE = "enter_edit_value"
    
    # Edit flow: Confirm edit changes
    CONFIRM_EDIT = "confirm_edit"
    
    # Remove flow: Confirm removal
    CONFIRM_REMOVE = "confirm_remove"
    
    # Phase 3: User selecting reschedule strategy
    SELECT_STRATEGY = "select_strategy"
    
    # Phase 2: User viewing A*-generated reschedule options
    SELECT_RESCHEDULE_OPTION = "select_reschedule_option"
    
    # Phase 2: Confirm the selected reschedule plan
    CONFIRM_RESCHEDULE = "confirm_reschedule"


class IntentType(str, Enum):
    """Types of user intents."""
    
    ADD_EVENT = "add_event"
    EDIT_EVENT = "edit_event"
    REMOVE_EVENT = "remove_event"
    QUERY_EVENTS = "query_events"
    UNKNOWN = "unknown"


class PreferenceType(str, Enum):
    """User preferences for finding time slots."""
    
    SAME_TIME_DIFFERENT_DAY = "same_time_different_day"
    SPECIFIC_DAY = "specific_day"
    SPECIFIC_DAY_AND_TIME = "specific_day_and_time"
    ANY_FREE_TIME = "any_free_time"


class ResolutionType(str, Enum):
    """How to resolve a conflict."""
    
    FIND_SLOT_FOR_NEW = "find_slot_for_new"
    MOVE_CONFLICTING = "move_conflicting"
    SMART_RESCHEDULE = "smart_reschedule"


class RescheduleStrategy(str, Enum):
    """Strategy for A*-based rescheduling."""
    
    MINIMIZE_MOVES = "minimize_moves"
    MAXIMIZE_QUALITY = "maximize_quality"
    BALANCED = "balanced"


class EditFieldType(str, Enum):
    """Which field to edit in an event."""
    
    TITLE = "title"
    DATE = "date"
    TIME = "time"
    DATE_AND_TIME = "date_and_time"


@dataclass
class EventData:
    """Structured event data parsed from user input."""
    
    title: Optional[str] = None
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None
    start_hour: Optional[int] = None
    start_minute: Optional[int] = None
    end_hour: Optional[int] = None
    end_minute: Optional[int] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    
    def is_complete(self) -> bool:
        """Check if all required fields are present."""
        return all([
            self.title is not None,
            self.day is not None,
            self.month is not None,
            self.year is not None,
            self.start_hour is not None,
            self.start_minute is not None,
            self.end_hour is not None,
            self.end_minute is not None,
        ])
    
    def get_missing_fields(self) -> list[str]:
        """Get list of missing required fields."""
        missing = []
        if self.title is None:
            missing.append("title")
        if self.day is None:
            missing.append("day")
        if self.month is None:
            missing.append("month")
        if self.year is None:
            missing.append("year")
        if self.start_hour is None or self.start_minute is None:
            missing.append("start_time")
        if self.end_hour is None or self.end_minute is None:
            missing.append("end_time")
        return missing
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
            "location": self.location,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventData":
        """Create from dictionary."""
        return cls(
            title=data.get("title"),
            day=data.get("day"),
            month=data.get("month"),
            year=data.get("year"),
            start_hour=data.get("start_hour"),
            start_minute=data.get("start_minute"),
            end_hour=data.get("end_hour"),
            end_minute=data.get("end_minute"),
            location=data.get("location"),
            notes=data.get("notes"),
        )


@dataclass
class ConflictInfo:
    """Information about a conflicting event."""
    
    event_id: str
    title: str
    day: int
    month: int
    year: int
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "title": self.title,
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
        }


@dataclass
class ExistingEvent:
    """An existing event from the database for selection."""
    
    event_id: str
    title: str
    day: int
    month: int
    year: int
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "title": self.title,
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
        }
    
    def format_display(self) -> str:
        """Format for display to user."""
        return f"{self.title} ({self.start_hour:02d}:{self.start_minute:02d} - {self.end_hour:02d}:{self.end_minute:02d})"


@dataclass
class TimeSlot:
    """A suggested time slot."""
    
    day: int
    month: int
    year: int
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
        }
    
    def format_display(self) -> str:
        """Format for display to user."""
        return f"{self.day}/{self.month}/{self.year} {self.start_hour:02d}:{self.start_minute:02d} - {self.end_hour:02d}:{self.end_minute:02d}"


@dataclass
class FreeTimeRange:
    """A contiguous free time range where user can pick any start time."""
    
    day: int
    month: int
    year: int
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
        }
    
    def duration_minutes(self) -> int:
        """Get the duration of this range in minutes."""
        start = self.start_hour * 60 + self.start_minute
        end = self.end_hour * 60 + self.end_minute
        return end - start
    
    def format_time_range(self) -> str:
        """Format the range as a string like '09:00 - 17:00'."""
        return f"{self.start_hour:02d}:{self.start_minute:02d} - {self.end_hour:02d}:{self.end_minute:02d}"
    
    def format_display(self) -> str:
        """Format for display to user including date."""
        return f"{self.day}/{self.month}/{self.year} {self.format_time_range()}"
    
    def can_fit_duration(self, duration_minutes: int) -> bool:
        """Check if this range can fit an event of given duration."""
        return self.duration_minutes() >= duration_minutes


@dataclass
class SessionContext:
    """Session context holding all state data."""
    
    state: AgentState = AgentState.INIT
    intent: Optional[IntentType] = None
    event_data: Optional[EventData] = None
    conflict_info: Optional[ConflictInfo] = None
    resolution_type: Optional[ResolutionType] = None
    preference_type: Optional[PreferenceType] = None
    suggested_slots: list[TimeSlot] = field(default_factory=list)
    free_ranges: list[FreeTimeRange] = field(default_factory=list)
    selected_slot: Optional[TimeSlot] = None
    target_event_id: Optional[str] = None  # For edit/remove
    query_type: Optional[str] = None  # day, week, month
    query_date: Optional[Dict[str, int]] = None  # {day, month, year}
    slot_offset: int = 0  # For "show more" functionality
    missing_field: Optional[str] = None  # Current field being collected
    
    # Edit/Remove flow fields
    events_on_day: list[ExistingEvent] = field(default_factory=list)  # Events for selection
    selected_event: Optional[ExistingEvent] = None  # Event selected for edit/remove
    edit_field: Optional[EditFieldType] = None  # Field being edited
    new_event_data: Optional[Dict[str, Any]] = None  # New values for edited event (day, month, year, start_hour, etc.)
    
    # Phase 2: Constraint solver rescheduling fields
    reschedule_strategy: Optional[RescheduleStrategy] = None
    reschedule_options: list[Dict[str, Any]] = field(default_factory=list)  # Serialized RescheduleOption list
    selected_reschedule: Optional[Dict[str, Any]] = None  # The picked option
    
    def reset(self):
        """Reset to initial state."""
        self.state = AgentState.INIT
        self.intent = None
        self.event_data = None
        self.conflict_info = None
        self.resolution_type = None
        self.preference_type = None
        self.suggested_slots = []
        self.free_ranges = []
        self.selected_slot = None
        self.target_event_id = None
        self.query_type = None
        self.query_date = None
        self.slot_offset = 0
        self.missing_field = None
        self.events_on_day = []
        self.selected_event = None
        self.edit_field = None
        self.new_event_data = None
        self.reschedule_strategy = None
        self.reschedule_options = []
        self.selected_reschedule = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "state": self.state.value,
            "intent": self.intent.value if self.intent else None,
            "event_data": self.event_data.to_dict() if self.event_data else None,
            "conflict_info": self.conflict_info.to_dict() if self.conflict_info else None,
            "resolution_type": self.resolution_type.value if self.resolution_type else None,
            "preference_type": self.preference_type.value if self.preference_type else None,
            "suggested_slots": [s.to_dict() for s in self.suggested_slots],
            "free_ranges": [r.to_dict() for r in self.free_ranges],
            "selected_slot": self.selected_slot.to_dict() if self.selected_slot else None,
            "target_event_id": self.target_event_id,
            "query_type": self.query_type,
            "query_date": self.query_date,
            "slot_offset": self.slot_offset,
            "missing_field": self.missing_field,
            "events_on_day": [e.to_dict() for e in self.events_on_day],
            "selected_event": self.selected_event.to_dict() if self.selected_event else None,
            "edit_field": self.edit_field.value if self.edit_field else None,
            "new_event_data": self.new_event_data,  # Already a dict
            "reschedule_strategy": self.reschedule_strategy.value if self.reschedule_strategy else None,
            "reschedule_options": self.reschedule_options,  # Already list of dicts
            "selected_reschedule": self.selected_reschedule,  # Already a dict
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        """Deserialize from dictionary."""
        ctx = cls()
        ctx.state = AgentState(data.get("state", "init"))
        ctx.intent = IntentType(data["intent"]) if data.get("intent") else None
        ctx.event_data = EventData.from_dict(data["event_data"]) if data.get("event_data") else None
        ctx.conflict_info = ConflictInfo(**data["conflict_info"]) if data.get("conflict_info") else None
        ctx.resolution_type = ResolutionType(data["resolution_type"]) if data.get("resolution_type") else None
        ctx.preference_type = PreferenceType(data["preference_type"]) if data.get("preference_type") else None
        ctx.suggested_slots = [TimeSlot(**s) for s in data.get("suggested_slots", [])]
        ctx.free_ranges = [FreeTimeRange(**r) for r in data.get("free_ranges", [])]
        ctx.selected_slot = TimeSlot(**data["selected_slot"]) if data.get("selected_slot") else None
        ctx.target_event_id = data.get("target_event_id")
        ctx.query_type = data.get("query_type")
        ctx.query_date = data.get("query_date")
        ctx.slot_offset = data.get("slot_offset", 0)
        ctx.missing_field = data.get("missing_field")
        ctx.events_on_day = [ExistingEvent(**e) for e in data.get("events_on_day", [])]
        ctx.selected_event = ExistingEvent(**data["selected_event"]) if data.get("selected_event") else None
        ctx.edit_field = EditFieldType(data["edit_field"]) if data.get("edit_field") else None
        ctx.new_event_data = data.get("new_event_data")  # Already a dict
        ctx.reschedule_strategy = RescheduleStrategy(data["reschedule_strategy"]) if data.get("reschedule_strategy") else None
        ctx.reschedule_options = data.get("reschedule_options", [])
        ctx.selected_reschedule = data.get("selected_reschedule")
        return ctx


class StateTransition:
    """Helper class for state transitions."""
    
    @staticmethod
    def can_transition(from_state: AgentState, to_state: AgentState) -> bool:
        """Check if transition is valid."""
        valid_transitions = {
            AgentState.INIT: [
                AgentState.COLLECT_INFO,
                AgentState.CONFIRM_CONFLICT,
                AgentState.INIT,  # Success without conflict
            ],
            AgentState.COLLECT_INFO: [
                AgentState.COLLECT_INFO,  # Still missing fields
                AgentState.CONFIRM_CONFLICT,
                AgentState.INIT,  # Success without conflict
            ],
            AgentState.CONFIRM_CONFLICT: [
                AgentState.CHOOSE_RESOLUTION,  # User wants help
                AgentState.INIT,  # User doesn't want help
            ],
            AgentState.CHOOSE_RESOLUTION: [
                AgentState.SELECT_PREFERENCE,
                AgentState.SELECT_STRATEGY,  # Phase 3: Strategy selection before smart reschedule
                AgentState.SELECT_RESCHEDULE_OPTION,  # Phase 2: Smart reschedule
                AgentState.INIT,  # Timeout or cancel
            ],
            AgentState.SELECT_PREFERENCE: [
                AgentState.SELECT_SLOT,
                AgentState.CONFIRM_ACTION,  # Direct choice (specific day and time)
                AgentState.SELECT_PREFERENCE,  # No slots found, try again
                AgentState.INIT,  # Cancel
            ],
            AgentState.SELECT_SLOT: [
                AgentState.CONFIRM_ACTION,
                AgentState.SELECT_SLOT,  # Show more
                AgentState.SELECT_PREFERENCE,  # Go back
                AgentState.INIT,  # Cancel
            ],
            AgentState.CONFIRM_ACTION: [
                AgentState.INIT,  # Confirmed or cancelled
                AgentState.SELECT_PREFERENCE,  # Go back
            ],
            AgentState.WAITING_CHOICE: [
                AgentState.INIT,  # Timeout
                AgentState.CHOOSE_RESOLUTION,
                AgentState.SELECT_PREFERENCE,
                AgentState.SELECT_SLOT,
                AgentState.CONFIRM_ACTION,
                AgentState.SELECT_STRATEGY,
                AgentState.SELECT_RESCHEDULE_OPTION,
            ],
            # Phase 3: Strategy selection for smart reschedule
            AgentState.SELECT_STRATEGY: [
                AgentState.SELECT_RESCHEDULE_OPTION,  # Strategy chosen, run solver
                AgentState.CHOOSE_RESOLUTION,  # Go back
                AgentState.INIT,  # Cancel
            ],
            # Phase 2: Constraint solver rescheduling
            AgentState.SELECT_RESCHEDULE_OPTION: [
                AgentState.CONFIRM_RESCHEDULE,  # User picked an option
                AgentState.CHOOSE_RESOLUTION,  # Go back
                AgentState.INIT,  # Cancel
            ],
            AgentState.CONFIRM_RESCHEDULE: [
                AgentState.INIT,  # Confirmed or cancelled
                AgentState.SELECT_RESCHEDULE_OPTION,  # Go back
            ],
        }
        
        allowed = valid_transitions.get(from_state, [])
        return to_state in allowed
