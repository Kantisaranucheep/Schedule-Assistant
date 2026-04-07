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


class PrologService:
    """Service for Prolog-based scheduling logic."""
    
    def __init__(self):
        self._prolog = None
        self._initialized = False
        self._prolog_file = os.path.join(
            os.path.dirname(__file__), 
            "prolog", 
            "scheduler.pl"
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
