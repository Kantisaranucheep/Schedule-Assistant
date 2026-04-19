# apps/backend/app/chat/prolog_service.py
"""
Prolog Service - Handles conflict detection and free slot finding using SWI-Prolog.

This service uses pyswip to interface with Prolog for:
- Checking time conflicts using First-Order Logic and Resolution
- Finding free time slots using Constraint Solving
- Logical inference for scheduling decisions
"""

import os
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.timezone import now as tz_now, get_system_timezone

# Try to import pyswip - it requires SWI-Prolog to be installed
try:
    from pyswip import Prolog
    PYSWIP_AVAILABLE = True
except ImportError:
    PYSWIP_AVAILABLE = False
    Prolog = None


@dataclass
class ConflictResult:
    """Result of a conflict check."""
    has_conflict: bool
    conflicts: List[Dict[str, Any]]


@dataclass 
class FreeSlot:
    """A free time slot."""
    day: int
    month: int
    year: int
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
        }


@dataclass
class FreeRange:
    """A contiguous free time range."""
    day: int
    month: int
    year: int
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    
    def to_dict(self) -> Dict[str, Any]:
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
    
    def can_fit_duration(self, duration_minutes: int) -> bool:
        """Check if this range can fit an event of given duration."""
        return self.duration_minutes() >= duration_minutes


@dataclass
class RescheduleOption:
    """A rescheduling suggestion from the constraint solver."""
    action: str  # 'move_new', 'move_existing', 'no_conflict'
    description: str
    cost: float
    moves: List[Dict[str, Any]]  # List of {event_id, title, new_start_hour, new_start_min, new_end_hour, new_end_min}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "description": self.description,
            "cost": self.cost,
            "moves": self.moves,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RescheduleOption":
        return cls(
            action=data["action"],
            description=data["description"],
            cost=data["cost"],
            moves=data.get("moves", []),
        )


@dataclass
class AddEventResult:
    """
    Result from the Prolog black-box add-event solver.
    
    This is the KRR "black box" response — Python doesn't know
    how Prolog reached this decision, only what the decision is.
    """
    status: str  # 'ok', 'conflict', 'invalid'
    conflicts: List[Dict[str, Any]]  # conflict details if status == 'conflict'
    violations: List[str]  # constraint violations if status == 'invalid'


@dataclass
class TimeSuggestion:
    """
    A single time suggestion from the Prolog black-box solver.
    
    Includes the slot, a quality score, and the REASON why
    this time was ranked this way — enabling Prolog to explain
    its reasoning to the user.
    """
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    score: float
    reason: str  # e.g., 'ideal_time', 'outside_preferred_hours', 'tight_buffer'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
            "score": self.score,
            "reason": self.reason,
        }


class PrologService:
    """Service for Prolog-based scheduling logic."""
    
    def __init__(self):
        self._prolog = None
        self._initialized = False
        self._constraint_solver_loaded = False
        self._prolog_file = os.path.join(
            os.path.dirname(__file__), 
            "prolog", 
            "scheduler.pl"
        )
        self._constraint_solver_file = os.path.join(
            os.path.dirname(__file__),
            "prolog",
            "constraint_solver.pl"
        )
    
    def _ensure_initialized(self) -> bool:
        """Initialize Prolog engine if needed."""
        if self._initialized:
            return True
            
        if not PYSWIP_AVAILABLE:
            return False
            
        try:
            self._prolog = Prolog()
            self._prolog.consult(self._prolog_file)
            self._initialized = True
            # Also try to load constraint solver
            try:
                self._prolog.consult(self._constraint_solver_file)
                self._constraint_solver_loaded = True
            except Exception as e:
                print(f"Constraint solver not loaded (will use Python fallback): {e}")
            return True
        except Exception as e:
            print(f"Failed to initialize Prolog: {e}")
            return False
    
    def check_conflict(
        self,
        new_start_hour: int,
        new_start_minute: int,
        new_end_hour: int,
        new_end_minute: int,
        existing_events: List[Dict[str, Any]]
    ) -> ConflictResult:
        """
        Check if a new event conflicts with existing events.
        
        Uses Prolog's Resolution-based conflict detection.
        
        Args:
            new_start_hour: Start hour of new event (0-23)
            new_start_minute: Start minute of new event (0-59)
            new_end_hour: End hour of new event (0-23)
            new_end_minute: End minute of new event (0-59)
            existing_events: List of existing events with keys:
                - id, title, start_hour, start_minute, end_hour, end_minute
        
        Returns:
            ConflictResult with has_conflict flag and list of conflicts
        """
        # If Prolog is not available, use Python fallback
        if not self._ensure_initialized():
            return self._check_conflict_python(
                new_start_hour, new_start_minute,
                new_end_hour, new_end_minute,
                existing_events
            )
        
        try:
            # Build Prolog event list
            events_str = self._build_events_list(existing_events)
            
            # Query Prolog
            query = f"check_conflict({new_start_hour}, {new_start_minute}, {new_end_hour}, {new_end_minute}, {events_str}, Conflicts)"
            
            results = list(self._prolog.query(query))
            
            if not results:
                return ConflictResult(has_conflict=False, conflicts=[])
            
            conflicts = results[0].get("Conflicts", [])
            
            # Parse Prolog conflict results
            parsed_conflicts = []
            for conflict in conflicts:
                if hasattr(conflict, 'args'):
                    # conflict(ID, Title, SH, SM, EH, EM)
                    args = conflict.args
                    parsed_conflicts.append({
                        "id": str(args[0]),
                        "title": str(args[1]),
                        "start_hour": int(args[2]),
                        "start_minute": int(args[3]),
                        "end_hour": int(args[4]),
                        "end_minute": int(args[5]),
                    })
            
            return ConflictResult(
                has_conflict=len(parsed_conflicts) > 0,
                conflicts=parsed_conflicts
            )
            
        except Exception as e:
            print(f"Prolog query failed: {e}")
            # Fallback to Python implementation
            return self._check_conflict_python(
                new_start_hour, new_start_minute,
                new_end_hour, new_end_minute,
                existing_events
            )
    
    def find_free_slots(
        self,
        duration_minutes: int,
        existing_events: List[Dict[str, Any]],
        min_start_hour: int = 0,
        min_start_minute: int = 0,
        max_end_hour: int = 23,
        max_end_minute: int = 59,
        max_results: int = 3
    ) -> List[FreeSlot]:
        """
        Find free time slots of given duration.
        
        Uses Prolog's Constraint Solving for slot finding.
        
        Args:
            duration_minutes: Required duration in minutes
            existing_events: List of existing events
            min_start_hour: Earliest possible start hour
            min_start_minute: Earliest possible start minute
            max_end_hour: Latest possible end hour
            max_end_minute: Latest possible end minute
            max_results: Maximum number of slots to return
        
        Returns:
            List of FreeSlot objects
        """
        # If Prolog is not available, use Python fallback
        if not self._ensure_initialized():
            return self._find_free_slots_python(
                duration_minutes, existing_events,
                min_start_hour, min_start_minute,
                max_end_hour, max_end_minute,
                max_results
            )
        
        try:
            # Build Prolog event list
            events_str = self._build_events_list(existing_events)
            
            # Query Prolog
            query = f"find_free_slots({duration_minutes}, {events_str}, {min_start_hour}, {min_start_minute}, {max_end_hour}, {max_end_minute}, FreeSlots)"
            
            results = list(self._prolog.query(query))
            
            if not results:
                return []
            
            slots = results[0].get("FreeSlots", [])
            
            # Parse Prolog slot results
            free_slots = []
            for slot in slots[:max_results]:
                if hasattr(slot, 'args'):
                    # slot(SH, SM, EH, EM)
                    args = slot.args
                    free_slots.append(FreeSlot(
                        day=0,  # Day will be set by caller
                        month=0,
                        year=0,
                        start_hour=int(args[0]),
                        start_minute=int(args[1]),
                        end_hour=int(args[2]),
                        end_minute=int(args[3]),
                    ))
            
            return free_slots
            
        except Exception as e:
            print(f"Prolog query failed: {e}")
            return self._find_free_slots_python(
                duration_minutes, existing_events,
                min_start_hour, min_start_minute,
                max_end_hour, max_end_minute,
                max_results
            )
    
    def find_free_slots_on_date(
        self,
        day: int,
        month: int,
        year: int,
        duration_minutes: int,
        existing_events: List[Dict[str, Any]],
        max_results: int = 3
    ) -> List[FreeSlot]:
        """
        Find free slots on a specific date.
        
        Args:
            day, month, year: The target date
            duration_minutes: Required duration
            existing_events: Events on that date
            max_results: Maximum slots to return
        
        Returns:
            List of FreeSlot objects with date filled in
        """
        slots = self.find_free_slots(
            duration_minutes=duration_minutes,
            existing_events=existing_events,
            max_results=max_results
        )
        
        # Fill in the date
        for slot in slots:
            slot.day = day
            slot.month = month
            slot.year = year
        
        return slots
    
    def find_free_ranges(
        self,
        existing_events: List[Dict[str, Any]],
        min_start_hour: int = 0,
        min_start_minute: int = 0,
        max_end_hour: int = 23,
        max_end_minute: int = 59,
    ) -> List[FreeRange]:
        """
        Find contiguous free time ranges (gaps between events).
        
        Unlike find_free_slots which returns fixed-duration slots,
        this returns the actual free periods where users can choose
        any start time within the range.
        
        Args:
            existing_events: List of existing events
            min_start_hour: Earliest possible start hour
            min_start_minute: Earliest possible start minute
            max_end_hour: Latest possible end hour
            max_end_minute: Latest possible end minute
        
        Returns:
            List of FreeRange objects representing contiguous free periods
        """
        # If Prolog is not available, use Python fallback
        if not self._ensure_initialized():
            return self._find_free_ranges_python(
                existing_events,
                min_start_hour, min_start_minute,
                max_end_hour, max_end_minute
            )
        
        try:
            # Build Prolog event list
            events_str = self._build_events_list(existing_events)
            
            # Query Prolog
            query = f"find_free_ranges({events_str}, {min_start_hour}, {min_start_minute}, {max_end_hour}, {max_end_minute}, FreeRanges)"
            
            results = list(self._prolog.query(query))
            
            if not results:
                return []
            
            ranges = results[0].get("FreeRanges", [])
            
            # Parse Prolog range results
            free_ranges = []
            for r in ranges:
                if hasattr(r, 'args'):
                    # range(SH, SM, EH, EM)
                    args = r.args
                    free_ranges.append(FreeRange(
                        day=0,  # Day will be set by caller
                        month=0,
                        year=0,
                        start_hour=int(args[0]),
                        start_minute=int(args[1]),
                        end_hour=int(args[2]),
                        end_minute=int(args[3]),
                    ))
            
            return free_ranges
            
        except Exception as e:
            print(f"Prolog query failed: {e}")
            return self._find_free_ranges_python(
                existing_events,
                min_start_hour, min_start_minute,
                max_end_hour, max_end_minute
            )
    
    def find_free_ranges_on_date(
        self,
        day: int,
        month: int,
        year: int,
        existing_events: List[Dict[str, Any]],
        duration_minutes: int = 0,
        filter_past_times: bool = True,
        timezone: str = "Asia/Bangkok"
    ) -> List[FreeRange]:
        """
        Find free time ranges on a specific date.
        
        Filters out past times when the date is today.
        Optionally filters ranges that can't fit the required duration.
        
        Args:
            day, month, year: The target date
            existing_events: Events on that date
            duration_minutes: If > 0, only return ranges that can fit this duration
            filter_past_times: If True and date is today, exclude past times
            timezone: Timezone string (e.g., "Asia/Bangkok") for current time
        
        Returns:
            List of FreeRange objects with date filled in
        """
        # Get current time in the specified timezone
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
        except Exception:
            # Fallback to system timezone if specified timezone is invalid
            now = tz_now()
        
        is_today = (day == now.day and month == now.month and year == now.year)
        
        # Determine start time
        if filter_past_times and is_today:
            # Start from current time (rounded up to next minute)
            min_start_hour = now.hour
            min_start_minute = now.minute + 1
            if min_start_minute >= 60:
                min_start_hour += 1
                min_start_minute = 0
            if min_start_hour >= 24:
                # Day is over, no free time
                return []
        else:
            min_start_hour = 0
            min_start_minute = 0
        
        ranges = self.find_free_ranges(
            existing_events=existing_events,
            min_start_hour=min_start_hour,
            min_start_minute=min_start_minute,
        )
        
        # Fill in the date
        for r in ranges:
            r.day = day
            r.month = month
            r.year = year
        
        # Filter by duration if specified
        if duration_minutes > 0:
            ranges = [r for r in ranges if r.can_fit_duration(duration_minutes)]
        
        return ranges
    
    def validate_time_in_ranges(
        self,
        start_hour: int,
        start_minute: int,
        duration_minutes: int,
        free_ranges: List[FreeRange]
    ) -> bool:
        """
        Check if a given start time fits within any of the free ranges.
        
        Args:
            start_hour: Proposed start hour
            start_minute: Proposed start minute
            duration_minutes: Required duration in minutes
            free_ranges: List of available free ranges
        
        Returns:
            True if the proposed time slot fits within a free range
        """
        proposed_start = start_hour * 60 + start_minute
        proposed_end = proposed_start + duration_minutes
        
        for r in free_ranges:
            range_start = r.start_hour * 60 + r.start_minute
            range_end = r.end_hour * 60 + r.end_minute
            
            # Check if proposed slot fits entirely within this range
            if proposed_start >= range_start and proposed_end <= range_end:
                return True
        
        return False
    
    def find_free_days(
        self,
        duration_minutes: int,
        events_by_day: Dict[Tuple[int, int, int], List[Dict[str, Any]]],
        preferred_start_hour: int,
        preferred_start_minute: int,
        max_results: int = 3
    ) -> List[FreeSlot]:
        """
        Find days where a slot of given duration can fit at the same time.
        
        Args:
            duration_minutes: Required duration
            events_by_day: Dict mapping (day, month, year) to events on that day
            preferred_start_hour: Preferred start hour
            preferred_start_minute: Preferred start minute
            max_results: Maximum days to return
        
        Returns:
            List of FreeSlot objects representing available days
        """
        free_days = []
        
        preferred_end_hour = preferred_start_hour + (duration_minutes // 60)
        preferred_end_minute = preferred_start_minute + (duration_minutes % 60)
        if preferred_end_minute >= 60:
            preferred_end_hour += 1
            preferred_end_minute -= 60
        
        for (day, month, year), events in events_by_day.items():
            # Check if the preferred time slot is free
            conflict = self.check_conflict(
                preferred_start_hour, preferred_start_minute,
                preferred_end_hour, preferred_end_minute,
                events
            )
            
            if not conflict.has_conflict:
                free_days.append(FreeSlot(
                    day=day,
                    month=month,
                    year=year,
                    start_hour=preferred_start_hour,
                    start_minute=preferred_start_minute,
                    end_hour=preferred_end_hour,
                    end_minute=preferred_end_minute,
                ))
                
                if len(free_days) >= max_results:
                    break
        
        return free_days
    
    # =========================================================================
    # Black Box KRR API — High-Level Reasoning Requests
    # =========================================================================
    # These methods treat Prolog as an autonomous reasoning agent.
    # Python sends all data and a high-level goal; Prolog handles
    # ALL reasoning internally and returns a complete decision.
    #
    # Python does NOT know which predicates Prolog uses internally —
    # it only understands the result type.
    
    def handle_add_event(
        self,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
        existing_events: List[Dict[str, Any]]
    ) -> AddEventResult:
        """
        Black-box KRR solver: "Can I add this event?"
        
        Sends all data to Prolog and lets it autonomously reason about:
        - Constraint validation (duration, bounds)
        - Conflict detection with existing events
        - Result classification
        
        Python doesn't call check_conflict or valid_placement —
        Prolog handles everything and returns a complete decision.
        
        Returns:
            AddEventResult with status ('ok', 'conflict', 'invalid')
            and relevant details.
        """
        if not self._ensure_initialized():
            print("[handle_add_event] Prolog not initialized, using Python fallback")
            return self._handle_add_event_python(
                start_hour, start_minute, end_hour, end_minute,
                existing_events
            )
        
        try:
            events_str = self._build_events_list(existing_events)
            
            # Use separate output variables (Status, Conflicts, Violations)
            # instead of a single compound term — pyswip handles atoms and
            # lists reliably, but compound terms like result(...) may not
            # expose .args correctly across all pyswip versions.
            query = (
                f"handle_add_event({start_hour}, {start_minute}, "
                f"{end_hour}, {end_minute}, {events_str}, "
                f"Status, Conflicts, Violations)"
            )
            
            print(f"[handle_add_event] Query: {query[:200]}...")
            
            results = list(self._prolog.query(query))
            
            if not results:
                print("[handle_add_event] No Prolog results, using Python fallback")
                return self._handle_add_event_python(
                    start_hour, start_minute, end_hour, end_minute,
                    existing_events
                )
            
            result = results[0]
            status_raw = result.get("Status")
            conflicts_raw = result.get("Conflicts", [])
            violations_raw = result.get("Violations", [])
            
            print(f"[handle_add_event] Raw: status={status_raw} (type={type(status_raw).__name__}), "
                  f"conflicts={conflicts_raw} (type={type(conflicts_raw).__name__}), "
                  f"violations={violations_raw}")
            
            # Parse status atom — pyswip returns atoms as str or Atom objects
            status = str(status_raw) if status_raw is not None else "ok"
            
            if status == "invalid":
                violations = []
                if isinstance(violations_raw, list):
                    violations = [str(v) for v in violations_raw]
                return AddEventResult(status='invalid', conflicts=[], violations=violations)
            
            if status == "conflict":
                conflicts = self._parse_conflict_list(conflicts_raw)
                if conflicts:
                    return AddEventResult(status='conflict', conflicts=conflicts, violations=[])
                # If we got status=conflict but couldn't parse conflicts, fall through
                print("[handle_add_event] WARNING: Got conflict status but no parseable conflicts")
            
            if status == "ok":
                return AddEventResult(status='ok', conflicts=[], violations=[])
            
            # Unrecognized status — fall back to Python for safety
            print(f"[handle_add_event] Unrecognized status '{status}', using Python fallback")
            return self._handle_add_event_python(
                start_hour, start_minute, end_hour, end_minute,
                existing_events
            )
            
        except Exception as e:
            print(f"Prolog handle_add_event failed: {e}")
            import traceback
            traceback.print_exc()
            return self._handle_add_event_python(
                start_hour, start_minute, end_hour, end_minute,
                existing_events
            )
    
    def handle_suggest_times(
        self,
        duration_minutes: int,
        existing_events: List[Dict[str, Any]],
        min_start_hour: int = 6,
        min_start_minute: int = 0,
        max_end_hour: int = 23,
        max_end_minute: int = 0,
        max_results: int = 5
    ) -> List[TimeSuggestion]:
        """
        Black-box KRR solver: "What are the best times for this event?"
        
        Sends duration + existing events + bounds to Prolog.
        Prolog autonomously:
        - Generates candidate slots
        - Validates against all constraints
        - Scores using soft constraint reasoning
        - Ranks and returns top suggestions with explanations
        
        Returns:
            List of TimeSuggestion with score and reason for ranking.
        """
        if not self._ensure_initialized():
            return self._handle_suggest_times_python(
                duration_minutes, existing_events,
                min_start_hour, min_start_minute,
                max_end_hour, max_end_minute,
                max_results
            )
        
        try:
            events_str = self._build_events_list(existing_events)
            
            query = (
                f"handle_suggest_times({duration_minutes}, {events_str}, "
                f"{min_start_hour}, {min_start_minute}, "
                f"{max_end_hour}, {max_end_minute}, Suggestions)"
            )
            
            results = list(self._prolog.query(query))
            
            if not results:
                return self._handle_suggest_times_python(
                    duration_minutes, existing_events,
                    min_start_hour, min_start_minute,
                    max_end_hour, max_end_minute,
                    max_results
                )
            
            suggestions = results[0].get("Suggestions", [])
            return self._parse_suggestions(suggestions, max_results)
            
        except Exception as e:
            print(f"Prolog handle_suggest_times failed: {e}")
            return self._handle_suggest_times_python(
                duration_minutes, existing_events,
                min_start_hour, min_start_minute,
                max_end_hour, max_end_minute,
                max_results
            )
    
    # =========================================================================
    # Black Box Result Parsers
    # =========================================================================
    
    def _parse_conflict_list(self, conflicts_raw) -> List[Dict[str, Any]]:
        """
        Parse a list of conflict(ID, Title, SH, SM, EH, EM) terms from Prolog.
        
        Uses the same parsing approach as the proven check_conflict method.
        """
        conflicts = []
        if not isinstance(conflicts_raw, list):
            return conflicts
        
        for c in conflicts_raw:
            if hasattr(c, 'args'):
                args = c.args
                conflicts.append({
                    "id": str(args[0]),
                    "title": str(args[1]),
                    "start_hour": int(args[2]),
                    "start_minute": int(args[3]),
                    "end_hour": int(args[4]),
                    "end_minute": int(args[5]),
                })
            elif hasattr(c, 'value'):
                # Some pyswip versions use .value
                print(f"[_parse_conflict_list] Got .value type: {c}")
            else:
                print(f"[_parse_conflict_list] Unknown conflict format: {c} (type={type(c).__name__})")
        
        return conflicts
    
    def _parse_suggestions(self, suggestions, max_results: int) -> List[TimeSuggestion]:
        """Parse the Prolog suggestion(Score, SH, SM, EH, EM, Reason) terms."""
        parsed = []
        if not isinstance(suggestions, list):
            return parsed
        
        for s in suggestions[:max_results]:
            if hasattr(s, 'args'):
                args = s.args
                parsed.append(TimeSuggestion(
                    start_hour=int(args[1]),
                    start_minute=int(args[2]),
                    end_hour=int(args[3]),
                    end_minute=int(args[4]),
                    score=float(args[0]),
                    reason=str(args[5]),
                ))
        
        return parsed
    
    # =========================================================================
    # Python Fallbacks for Black Box API
    # =========================================================================
    
    def _handle_add_event_python(
        self,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
        existing_events: List[Dict[str, Any]]
    ) -> AddEventResult:
        """Python fallback for the add-event solver."""
        start = start_hour * 60 + start_minute
        end = end_hour * 60 + end_minute
        
        # Check basic validity
        violations = []
        if end <= start:
            violations.append("positive_duration")
        if start < 360 or end > 1380:
            violations.append("within_bounds")
        if violations:
            return AddEventResult(status='invalid', conflicts=[], violations=violations)
        
        # Check conflicts
        conflicts = []
        for event in existing_events:
            ex_start = event["start_hour"] * 60 + event["start_minute"]
            ex_end = event["end_hour"] * 60 + event["end_minute"]
            if start < ex_end and ex_start < end:
                conflicts.append({
                    "id": event.get("id", "unknown"),
                    "title": event.get("title", ""),
                    "start_hour": event["start_hour"],
                    "start_minute": event["start_minute"],
                    "end_hour": event["end_hour"],
                    "end_minute": event["end_minute"],
                })
        
        if conflicts:
            return AddEventResult(status='conflict', conflicts=conflicts, violations=[])
        
        return AddEventResult(status='ok', conflicts=[], violations=[])
    
    def _handle_suggest_times_python(
        self,
        duration_minutes: int,
        existing_events: List[Dict[str, Any]],
        min_start_hour: int,
        min_start_minute: int,
        max_end_hour: int,
        max_end_minute: int,
        max_results: int
    ) -> List[TimeSuggestion]:
        """Python fallback for the suggest-times solver."""
        min_start = min_start_hour * 60 + min_start_minute
        max_end = max_end_hour * 60 + max_end_minute
        step = 30
        
        busy = []
        for e in existing_events:
            s = e["start_hour"] * 60 + e["start_minute"]
            end = e["end_hour"] * 60 + e["end_minute"]
            busy.append((s, end))
        busy.sort()
        
        suggestions = []
        current = min_start
        while current + duration_minutes <= max_end and len(suggestions) < max_results * 3:
            slot_end = current + duration_minutes
            is_free = not any(current < be and slot_end > bs for bs, be in busy)
            
            if is_free:
                # Score the slot
                buf_cost = sum(
                    3 for bs, be in busy
                    if (0 < current - be < 15) or (0 < bs - slot_end < 15)
                )
                pref_cost = 0 if 540 <= current <= 1020 else min(abs(current - 780) // 30, 10)
                load_cost = max(0, (len(busy) - 6) * 2) if len(busy) > 6 else 0
                score = buf_cost + pref_cost + load_cost
                
                if score == 0:
                    reason = "ideal_time"
                elif pref_cost > 0 and buf_cost > 0:
                    reason = "suboptimal_time_and_tight_buffer"
                elif pref_cost > 0:
                    reason = "outside_preferred_hours"
                elif buf_cost > 0:
                    reason = "tight_buffer"
                elif load_cost > 0:
                    reason = "heavy_day"
                else:
                    reason = "acceptable"
                
                sh, sm = divmod(current, 60)
                eh, em = divmod(slot_end, 60)
                suggestions.append(TimeSuggestion(
                    start_hour=sh, start_minute=sm,
                    end_hour=eh, end_minute=em,
                    score=score, reason=reason,
                ))
            
            current += step
        
        suggestions.sort(key=lambda s: s.score)
        return suggestions[:max_results]
    
    def _build_events_list(self, events: List[Dict[str, Any]]) -> str:
        """Build a Prolog list of events."""
        if not events:
            return "[]"
        
        event_strs = []
        for e in events:
            # event(ID, Title, StartH, StartM, EndH, EndM)
            event_id = str(e.get("id", "unknown")).replace('"', '\\"')
            title = str(e.get("title", "")).replace('"', '\\"')
            event_str = f'event("{event_id}", "{title}", {e["start_hour"]}, {e["start_minute"]}, {e["end_hour"]}, {e["end_minute"]})'
            event_strs.append(event_str)
        
        return "[" + ", ".join(event_strs) + "]"
    
    # =========================================================================
    # Python Fallback Implementations
    # =========================================================================
    # These are used when Prolog is not available
    
    def _check_conflict_python(
        self,
        new_start_hour: int,
        new_start_minute: int,
        new_end_hour: int,
        new_end_minute: int,
        existing_events: List[Dict[str, Any]]
    ) -> ConflictResult:
        """Python fallback for conflict checking."""
        new_start = new_start_hour * 60 + new_start_minute
        new_end = new_end_hour * 60 + new_end_minute
        
        conflicts = []
        for event in existing_events:
            ex_start = event["start_hour"] * 60 + event["start_minute"]
            ex_end = event["end_hour"] * 60 + event["end_minute"]
            
            # Overlap check: S1 < E2 and S2 < E1
            if new_start < ex_end and ex_start < new_end:
                conflicts.append({
                    "id": event.get("id", "unknown"),
                    "title": event.get("title", ""),
                    "start_hour": event["start_hour"],
                    "start_minute": event["start_minute"],
                    "end_hour": event["end_hour"],
                    "end_minute": event["end_minute"],
                })
        
        return ConflictResult(
            has_conflict=len(conflicts) > 0,
            conflicts=conflicts
        )
    
    def _find_free_slots_python(
        self,
        duration_minutes: int,
        existing_events: List[Dict[str, Any]],
        min_start_hour: int,
        min_start_minute: int,
        max_end_hour: int,
        max_end_minute: int,
        max_results: int
    ) -> List[FreeSlot]:
        """Python fallback for finding free slots."""
        min_start = min_start_hour * 60 + min_start_minute
        max_end = max_end_hour * 60 + max_end_minute
        
        # Convert events to intervals
        busy_intervals = []
        for event in existing_events:
            start = event["start_hour"] * 60 + event["start_minute"]
            end = event["end_hour"] * 60 + event["end_minute"]
            busy_intervals.append((start, end))
        
        # Sort by start time
        busy_intervals.sort(key=lambda x: x[0])
        
        # Find free slots with 30-minute granularity
        free_slots = []
        step = 30
        
        current = min_start
        while current + duration_minutes <= max_end and len(free_slots) < max_results:
            slot_end = current + duration_minutes
            
            # Check if slot conflicts with any busy interval
            is_free = True
            for busy_start, busy_end in busy_intervals:
                if current < busy_end and busy_start < slot_end:
                    is_free = False
                    break
            
            if is_free:
                start_h, start_m = divmod(current, 60)
                end_h, end_m = divmod(slot_end, 60)
                free_slots.append(FreeSlot(
                    day=0, month=0, year=0,
                    start_hour=start_h,
                    start_minute=start_m,
                    end_hour=end_h,
                    end_minute=end_m,
                ))
            
            current += step
        
        return free_slots
    
    def _find_free_ranges_python(
        self,
        existing_events: List[Dict[str, Any]],
        min_start_hour: int,
        min_start_minute: int,
        max_end_hour: int,
        max_end_minute: int
    ) -> List[FreeRange]:
        """Python fallback for finding free time ranges."""
        min_start = min_start_hour * 60 + min_start_minute
        max_end = max_end_hour * 60 + max_end_minute
        
        if min_start >= max_end:
            return []
        
        # Convert events to intervals and sort by start time
        busy_intervals = []
        for event in existing_events:
            start = event["start_hour"] * 60 + event["start_minute"]
            end = event["end_hour"] * 60 + event["end_minute"]
            busy_intervals.append((start, end))
        
        busy_intervals.sort(key=lambda x: x[0])
        
        # Find gaps between busy intervals
        free_ranges = []
        current_start = min_start
        
        for busy_start, busy_end in busy_intervals:
            # Clip busy interval to our range
            busy_start = max(busy_start, min_start)
            busy_end = min(busy_end, max_end)
            
            # Gap before this busy interval?
            if current_start < busy_start:
                gap_end = min(busy_start, max_end)
                if current_start < gap_end:
                    start_h, start_m = divmod(current_start, 60)
                    end_h, end_m = divmod(gap_end, 60)
                    free_ranges.append(FreeRange(
                        day=0, month=0, year=0,
                        start_hour=start_h,
                        start_minute=start_m,
                        end_hour=end_h,
                        end_minute=end_m,
                    ))
            
            # Move current_start to end of this busy interval
            current_start = max(current_start, busy_end)
        
        # Gap after last busy interval?
        if current_start < max_end:
            start_h, start_m = divmod(current_start, 60)
            end_h, end_m = divmod(max_end, 60)
            free_ranges.append(FreeRange(
                day=0, month=0, year=0,
                start_hour=start_h,
                start_minute=start_m,
                end_hour=end_h,
                end_minute=end_m,
            ))
        
        return free_ranges
    
    # =========================================================================
    # Phase 2: Constraint Solver — Reschedule Suggestions
    # =========================================================================
    
    def suggest_reschedule_options(
        self,
        new_event: Dict[str, Any],
        existing_events: List[Dict[str, Any]],
        strategy: str = "balanced",
        min_hour: int = 6,
        min_minute: int = 0,
        max_hour: int = 23,
        max_minute: int = 0,
        priority_map: Optional[Dict[str, int]] = None,
    ) -> List[RescheduleOption]:
        """
        Use the Phase 2 constraint solver to suggest up to 3 reschedule options.
        
        Args:
            new_event: Dict with id, title, start_hour, start_minute, end_hour, end_minute
            existing_events: List of existing event dicts on the same day
            strategy: 'minimize_moves', 'maximize_quality', or 'balanced'
            min_hour/min_minute: Earliest allowed time
            max_hour/max_minute: Latest allowed time
            priority_map: Event-type -> weight mapping from user persona (1-10 scale)
            
        Returns:
            List of RescheduleOption sorted by cost (best first)
        """
        return self._suggest_reschedule_python(
            new_event, existing_events, strategy,
            min_hour, min_minute, max_hour, max_minute,
            priority_map=priority_map,
        )
    
    def _suggest_reschedule_python(
        self,
        new_event: Dict[str, Any],
        existing_events: List[Dict[str, Any]],
        strategy: str,
        min_hour: int,
        min_minute: int,
        max_hour: int,
        max_minute: int,
        priority_map: Optional[Dict[str, int]] = None,
    ) -> List[RescheduleOption]:
        """
        Python implementation of suggest_reschedule_options.
        Mirrors the A*-based logic from constraint_solver.pl.
        
        Phase 3: Uses priority_map from user persona to assign event priorities.
        """
        new_start = new_event["start_hour"] * 60 + new_event.get("start_minute", 0)
        new_end = new_event["end_hour"] * 60 + new_event.get("end_minute", 0)
        new_duration = new_end - new_start
        new_title = new_event.get("title", "New event")
        new_priority = self._resolve_priority(new_title, new_event.get("priority"), priority_map)
        
        min_start = min_hour * 60 + min_minute
        max_end = max_hour * 60 + max_minute
        
        # Find conflicting events
        conflicts = []
        for evt in existing_events:
            e_start = evt["start_hour"] * 60 + evt.get("start_minute", 0)
            e_end = evt["end_hour"] * 60 + evt.get("end_minute", 0)
            if new_start < e_end and new_end > e_start:
                conflicts.append(evt)
        
        if not conflicts:
            return [RescheduleOption(
                action="no_conflict",
                description="No conflicts detected",
                cost=0,
                moves=[],
            )]
        
        options: List[RescheduleOption] = []
        
        # --- Option A: Move the NEW event to a nearby free slot ---
        all_busy = []
        for evt in existing_events:
            e_start = evt["start_hour"] * 60 + evt.get("start_minute", 0)
            e_end = evt["end_hour"] * 60 + evt.get("end_minute", 0)
            all_busy.append((e_start, e_end))
        all_busy.sort()
        
        # Generate candidate slots (30-min granularity) sorted by proximity
        candidates = []
        step = 30
        slot_start = min_start
        while slot_start + new_duration <= max_end:
            slot_end = slot_start + new_duration
            # Check no overlap with any existing event
            has_overlap = any(
                slot_start < be and slot_end > bs for bs, be in all_busy
            )
            if not has_overlap:
                displacement = abs(slot_start - new_start)
                disp_cost = displacement / 60.0 * 2
                # Soft cost: preferred time bonus
                soft_cost = self._calc_soft_cost(slot_start, slot_end, all_busy)
                score = disp_cost + soft_cost
                candidates.append((score, slot_start, slot_end))
            slot_start += step
        
        candidates.sort()
        
        # Add top 2 "move new event" options
        for i, (score, s_start, s_end) in enumerate(candidates[:2]):
            s_sh, s_sm = divmod(s_start, 60)
            s_eh, s_em = divmod(s_end, 60)
            # Apply strategy weighting
            adj_score = self._apply_strategy_weight(score, new_priority, strategy, is_new_event=True)
            options.append(RescheduleOption(
                action="move_new",
                description=f'Move "{new_title}" to {s_sh:02d}:{s_sm:02d}-{s_eh:02d}:{s_em:02d}',
                cost=adj_score,
                moves=[{
                    "event_id": new_event.get("id", "new"),
                    "title": new_title,
                    "new_start_hour": s_sh,
                    "new_start_minute": s_sm,
                    "new_end_hour": s_eh,
                    "new_end_minute": s_em,
                }],
            ))
        
        # --- Option B: Move each conflicting event to make room ---
        # Build busy list that includes the new event (as if placed)
        busy_with_new = all_busy + [(new_start, new_end)]
        busy_with_new.sort()
        
        for conflict_evt in conflicts:
            c_id = conflict_evt.get("id", "unknown")
            c_title = conflict_evt.get("title", "Event")
            c_start = conflict_evt["start_hour"] * 60 + conflict_evt.get("start_minute", 0)
            c_end = conflict_evt["end_hour"] * 60 + conflict_evt.get("end_minute", 0)
            c_duration = c_end - c_start
            c_priority = self._resolve_priority(c_title, conflict_evt.get("priority"), priority_map)
            
            # Build busy list excluding this conflict but including new event
            other_busy = [(bs, be) for bs, be in all_busy 
                          if not (bs == c_start and be == c_end)]
            other_busy.append((new_start, new_end))
            other_busy.sort()
            
            # Find best slot for this conflicting event
            best = None
            slot_start = min_start
            while slot_start + c_duration <= max_end:
                slot_end = slot_start + c_duration
                has_overlap = any(
                    slot_start < be and slot_end > bs for bs, be in other_busy
                )
                if not has_overlap:
                    displacement = abs(slot_start - c_start)
                    disp_cost = displacement / 60.0 * 2
                    soft_cost = self._calc_soft_cost(slot_start, slot_end, other_busy)
                    score = disp_cost + soft_cost + c_priority * 0.3
                    if best is None or score < best[0]:
                        best = (score, slot_start, slot_end)
                slot_start += step
            
            if best:
                score, s_start, s_end = best
                s_sh, s_sm = divmod(s_start, 60)
                s_eh, s_em = divmod(s_end, 60)
                adj_score = self._apply_strategy_weight(score, c_priority, strategy, is_new_event=False)
                options.append(RescheduleOption(
                    action="move_existing",
                    description=f'Move "{c_title}" to {s_sh:02d}:{s_sm:02d}-{s_eh:02d}:{s_em:02d}, keep "{new_title}" at original time',
                    cost=adj_score,
                    moves=[{
                        "event_id": c_id,
                        "title": c_title,
                        "new_start_hour": s_sh,
                        "new_start_minute": s_sm,
                        "new_end_hour": s_eh,
                        "new_end_minute": s_em,
                    }],
                ))
        
        # Sort by cost and return top 3
        options.sort(key=lambda o: o.cost)
        return options[:3]
    
    def _calc_soft_cost(self, start_min: int, end_min: int, busy_intervals: List[tuple]) -> float:
        """Calculate soft constraint cost (buffer proximity + overload)."""
        cost = 0.0
        # Buffer proximity: penalty if < 15 min gap to neighboring events
        for bs, be in busy_intervals:
            if 0 < start_min - be < 15:
                cost += 3.0
            if 0 < bs - end_min < 15:
                cost += 3.0
        # Daily overload: penalize if >6 events
        num_events = len(busy_intervals)
        if num_events > 8:
            cost += (num_events - 8) * 5
        elif num_events > 6:
            cost += (num_events - 6) * 2
        return cost
    
    def _apply_strategy_weight(
        self, base_cost: float, priority: int, strategy: str, is_new_event: bool
    ) -> float:
        """Apply strategy weighting as per constraint_solver.pl pick_best_option.
        
        Phase 3 - Strategy behavior:
        - minimize_moves: Favor moving the fewest events (prefer moving new event only)
        - maximize_quality: Protect high-priority events — move low-priority events first.
          Uses persona-derived priority (1-10). Higher priority = much more expensive to move.
        - balanced: Weighted compromise of moves + quality
        """
        if strategy == "minimize_moves":
            if is_new_event:
                return base_cost * 0.7  # Favor moving just the new event
            return base_cost * 1.3
        elif strategy == "maximize_quality":
            # Use a single continuous priority scale regardless of new/existing.
            # This guarantees a lower-priority event is always cheaper to move than
            # a higher-priority one — the is_new_event distinction caused lower-priority
            # existing events to be scored as more expensive than higher-priority new events.
            priority_factor = priority / 10.0  # 0.1 – 1.0
            return base_cost * (0.3 + priority_factor * 1.7)  # 0.47 (p=1) to 2.0 (p=10)
        elif strategy == "balanced":
            # Mild priority bias + mild move-count bias
            priority_factor = priority / 10.0
            if is_new_event:
                return base_cost * (0.7 + priority_factor * 0.5)  # 0.7 – 1.2
            else:
                return base_cost * (0.8 + priority_factor * 0.7)  # 0.8 – 1.5
        return base_cost
    
    # Keywords used to infer event type from title (Thai + English).
    # Must match the keyword list in SchedulingService._infer_event_type.
    _TYPE_KEYWORDS: Dict[str, List[str]] = {
        "exam":        ["exam", "test", "quiz", "midterm", "final", "สอบ"],
        "meeting":     ["meeting", "meet", "standup", "sync", "ประชุม", "daily scrum"],
        "study":       ["study", "homework", "assignment", "research", "review", "อ่านหนังสือ"],
        "class":       ["class", "lecture", "lab", "tutorial", "เรียน"],
        "deadline":    ["deadline", "due", "submit", "ส่งงาน"],
        "exercise":    ["exercise", "gym", "run", "sport", "yoga", "workout", "ออกกำลังกาย",
                        "football", "basketball", "swim", "cycling", "hiking", "volleyball",
                        "tennis", "badminton", "boxing", "martial arts", "dance"],
        "party":       ["party", "celebration", "ปาร์ตี้"],
        "social":      ["lunch", "dinner", "hangout", "coffee", "social", "เจอเพื่อน"],
        "work":        ["work", "shift", "office", "ทำงาน"],
        "appointment": ["doctor", "dentist", "appointment", "นัดหมาย"],
        "travel":      ["travel", "trip", "flight", "เดินทาง"],
        "personal":    ["personal", "errands", "ธุระ"],
    }

    def _infer_event_type(self, title: str) -> str:
        """Infer event type from title using the shared keyword map."""
        text = title.lower()
        for event_type, keywords in self._TYPE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return event_type
        return "other"

    def _resolve_priority(
        self,
        title: str,
        explicit_priority: Optional[int],
        priority_map: Optional[Dict[str, int]],
    ) -> int:
        """Resolve event priority using persona's priority_map.

        1. Infer the event type from the title using the full keyword map
           (handles Thai keywords, compound names, etc.).
        2. Look up that type in the user's priority_map.
        3. Fall back to explicit_priority (from the event dict), then 5.
        """
        if priority_map:
            event_type = self._infer_event_type(title)
            if event_type in priority_map:
                return priority_map[event_type]

        if explicit_priority is not None:
            return explicit_priority
        return 5
    
    def is_available(self) -> bool:
        """Check if Prolog service is available."""
        return self._ensure_initialized()


# Global instance
_prolog_service: Optional[PrologService] = None

def get_prolog_service() -> PrologService:
    """Get or create the Prolog service singleton."""
    global _prolog_service
    if _prolog_service is None:
        _prolog_service = PrologService()
    return _prolog_service
