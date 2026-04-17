"""
Scheduling Service — Priority-aware constraint solver with A* rescheduling.

Bridges user priorities (from Phase 1 LLM extraction) with Prolog constraint
logic (or Python fallback) for intelligent event scheduling.

Key concepts:
  - Hard constraints: MUST be satisfied (no time overlap, within bounds)
  - Soft constraints: SHOULD be satisfied (priority weights, time preferences)
  - g(n): Displacement cost — how far events moved from original times
  - h(n): Priority loss — impact of conflicts on high-priority events
  - f(n) = g(n) + h(n): Total cost, strategy-weighted
  - A* search: Explores schedule states sorted by f(n)
"""

import heapq
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ScheduleEvent:
    """An event in the scheduling domain."""
    id: str
    title: str
    start_minutes: int  # Minutes from midnight
    end_minutes: int
    priority: int  # 1-10 scale
    event_type: str  # meeting, study, party, etc.
    is_fixed: bool = False  # Hard constraint: cannot be moved

    @property
    def duration(self) -> int:
        return self.end_minutes - self.start_minutes

    def overlaps(self, other: "ScheduleEvent") -> bool:
        return self.start_minutes < other.end_minutes and other.start_minutes < self.end_minutes

    def copy_to(self, new_start: int) -> "ScheduleEvent":
        """Create a copy moved to a new start time."""
        duration = self.duration
        return ScheduleEvent(
            id=self.id, title=self.title,
            start_minutes=new_start, end_minutes=new_start + duration,
            priority=self.priority, event_type=self.event_type,
            is_fixed=self.is_fixed,
        )


@dataclass
class MoveAction:
    """Records a single event move."""
    event_id: str
    event_title: str
    original_start: int
    original_end: int
    new_start: int
    new_end: int
    priority: int
    cost: float
    reason: str = ""


@dataclass
class RescheduleOption:
    """One possible rescheduling solution."""
    action: str  # "no_conflict", "move_new", "move_existing", "no_solution"
    moves: List[MoveAction]
    total_cost: float
    explanation: str
    strategy: str


@dataclass
class RescheduleResult:
    """Complete result of rescheduling analysis."""
    has_conflict: bool
    conflicting_events: List[Dict]
    options: List[RescheduleOption]
    recommended_option: Optional[RescheduleOption] = None


# ============================================================================
# State for A* Search
# ============================================================================

@dataclass(order=True)
class ScheduleState:
    """A state in the A* search space."""
    f_score: float
    events: List[ScheduleEvent] = field(compare=False)
    moves: List[MoveAction] = field(compare=False)
    g_cost: float = field(compare=False, default=0.0)
    h_cost: float = field(compare=False, default=0.0)

    def state_key(self) -> tuple:
        """Hashable key for deduplication."""
        return tuple(sorted((e.id, e.start_minutes) for e in self.events))


# ============================================================================
# Constraint Checking
# ============================================================================

def check_hard_constraints(event: ScheduleEvent, all_events: List[ScheduleEvent],
                           min_time: int = 360, max_time: int = 1380) -> List[str]:
    """Check hard constraints. Returns list of violation descriptions."""
    violations = []

    # 1. Time overlap
    for other in all_events:
        if other.id != event.id and event.overlaps(other):
            violations.append(f"Overlaps with '{other.title}'")

    # 2. Working hours bounds
    if event.start_minutes < min_time:
        violations.append(f"Starts before {min_time // 60}:00")
    if event.end_minutes > max_time:
        violations.append(f"Ends after {max_time // 60}:00")

    # 3. Valid duration
    if event.duration <= 0:
        violations.append("Invalid duration")

    return violations


def find_all_conflicts(events: List[ScheduleEvent]) -> List[Tuple[str, str]]:
    """Find all pairs of overlapping events. Returns list of (id1, id2) tuples."""
    conflicts = []
    for i, e1 in enumerate(events):
        for e2 in events[i + 1:]:
            if e1.overlaps(e2):
                conflicts.append((e1.id, e2.id))
    return conflicts


# ============================================================================
# Soft Constraint Costs
# ============================================================================

PREFERRED_TIMES = {
    "meeting": (540, 1020),    # 9am - 5pm
    "study": (480, 720),       # 8am - 12pm  
    "exercise": (360, 480),    # 6am - 8am
    "class": (480, 1020),      # 8am - 5pm
    "exam": (480, 1020),       # 8am - 5pm
    "work": (540, 1080),       # 9am - 6pm
}


def calculate_soft_cost(event: ScheduleEvent, all_events: List[ScheduleEvent]) -> float:
    """Calculate total soft constraint violation cost for an event."""
    cost = 0.0

    # 1. Preferred time penalty
    pref = PREFERRED_TIMES.get(event.event_type)
    if pref:
        pref_start, pref_end = pref
        if event.start_minutes < pref_start:
            cost += min((pref_start - event.start_minutes) / 30, 10)
        elif event.start_minutes > pref_end:
            cost += min((event.start_minutes - pref_end) / 30, 10)

    # 2. Buffer proximity (events too close together, < 15 min gap)
    for other in all_events:
        if other.id == event.id:
            continue
        gap_before = event.start_minutes - other.end_minutes
        gap_after = other.start_minutes - event.end_minutes
        if 0 < gap_before < 15 or 0 < gap_after < 15:
            cost += 3

    # 3. High-priority events at suboptimal times
    if event.priority >= 8 and not (540 <= event.start_minutes <= 1020):
        cost += (event.priority - 7) * 3

    return cost


# ============================================================================
# g(n): Displacement Cost
# ============================================================================

def calculate_displacement_cost(moves: List[MoveAction]) -> float:
    """
    g(n) = Σ for each moved event:
      base_penalty(3) + hours_shifted × shift_weight(2) + priority × 0.5
    """
    total = 0.0
    for move in moves:
        shift_minutes = abs(move.new_start - move.original_start)
        shift_hours = shift_minutes / 60.0
        base_penalty = 3.0
        shift_cost = shift_hours * 2.0
        priority_penalty = move.priority * 0.5
        total += base_penalty + shift_cost + priority_penalty
    return total


# ============================================================================
# h(n): Priority Loss Heuristic
# ============================================================================

def calculate_priority_loss(conflicts: List[Tuple[str, str]],
                            events_map: Dict[str, ScheduleEvent],
                            strategy: str) -> float:
    """
    h(n) = Σ for each remaining conflict:
      priority_weight² × strategy_multiplier
    
    Quadratic penalty means high-priority conflicts are much more expensive.
    """
    weight = {"minimize_moves": 0.5, "maximize_quality": 2.0, "balanced": 1.0}.get(strategy, 1.0)

    total = 0.0
    for id1, id2 in conflicts:
        e1 = events_map.get(id1)
        e2 = events_map.get(id2)
        if e1 and e2:
            max_pri = max(e1.priority, e2.priority)
            total += (max_pri ** 2) * weight
    return total


# ============================================================================
# Find Free Slots
# ============================================================================

def find_free_slots(events: List[ScheduleEvent], duration: int,
                    min_time: int = 360, max_time: int = 1380,
                    step: int = 30) -> List[int]:
    """Find all free slot start times that can fit the given duration."""
    free = []
    t = min_time
    while t + duration <= max_time:
        slot_end = t + duration
        conflict = False
        for e in events:
            if t < e.end_minutes and e.start_minutes < slot_end:
                conflict = True
                break
        if not conflict:
            free.append(t)
        t += step
    return free


def find_best_slot_for_event(event: ScheduleEvent, other_events: List[ScheduleEvent],
                             min_time: int = 360, max_time: int = 1380) -> Optional[Tuple[int, float]]:
    """
    Find the best available slot for an event, minimizing displacement + soft cost.
    Returns (start_time, cost) or None.
    """
    others = [e for e in other_events if e.id != event.id]
    slots = find_free_slots(others, event.duration, min_time, max_time)

    if not slots:
        return None

    best_start = None
    best_cost = float("inf")

    for slot_start in slots:
        moved_event = event.copy_to(slot_start)
        displacement = abs(slot_start - event.start_minutes) / 60.0 * 2.0
        soft = calculate_soft_cost(moved_event, others)
        cost = displacement + soft
        if cost < best_cost:
            best_cost = cost
            best_start = slot_start

    return (best_start, best_cost) if best_start is not None else None


def find_top_n_slots_for_event(event: ScheduleEvent, other_events: List[ScheduleEvent],
                                n: int = 3,
                                min_time: int = 360, max_time: int = 1380) -> List[Tuple[int, float]]:
    """
    Find the N closest available slots to the event's original time.
    Ranked purely by absolute time distance so suggestions stay near the original hour.
    Returns list of (start_time_minutes, distance_minutes) sorted by distance ascending.
    """
    others = [e for e in other_events if e.id != event.id]
    slots = find_free_slots(others, event.duration, min_time, max_time, step=30)

    if not slots:
        return []

    scored = []
    for slot_start in slots:
        distance = abs(slot_start - event.start_minutes)
        scored.append((slot_start, float(distance)))

    scored.sort(key=lambda x: x[1])
    return scored[:n]


# ============================================================================
# A* Schedule Optimizer
# ============================================================================

class ScheduleOptimizer:
    """A* search-based schedule optimizer."""

    def __init__(self, strategy: str = "balanced",
                 min_time: int = 360, max_time: int = 1380,
                 max_depth: int = 5):
        self.strategy = strategy
        self.min_time = min_time
        self.max_time = max_time
        self.max_depth = max_depth

    def optimize(self, existing_events: List[ScheduleEvent],
                 new_event: ScheduleEvent) -> RescheduleResult:
        """Run full rescheduling analysis for a new event."""

        # Check if there are conflicts
        all_events = existing_events + [new_event]
        conflicts_with_new = [
            e for e in existing_events
            if new_event.overlaps(e)
        ]

        if not conflicts_with_new:
            return RescheduleResult(
                has_conflict=False,
                conflicting_events=[],
                options=[RescheduleOption(
                    action="no_conflict", moves=[], total_cost=0,
                    explanation="No conflicts. Event can be placed as-is.",
                    strategy=self.strategy,
                )],
                recommended_option=RescheduleOption(
                    action="no_conflict", moves=[], total_cost=0,
                    explanation="No conflicts. Event can be placed as-is.",
                    strategy=self.strategy,
                ),
            )

        conflict_info = [
            {"id": e.id, "title": e.title, "priority": e.priority,
             "start_minutes": e.start_minutes, "end_minutes": e.end_minutes}
            for e in conflicts_with_new
        ]

        options = []

        # Option A: Move the NEW event to a free slot
        opt_a = self._option_move_new(new_event, existing_events)
        if opt_a:
            options.append(opt_a)

        # Option B: Keep new event, move conflicting events
        opt_b = self._option_move_existing(new_event, existing_events, conflicts_with_new)
        if opt_b:
            options.append(opt_b)

        # Option C: A* search for optimal multi-move solution
        opt_c = self._option_astar(new_event, existing_events)
        if opt_c and opt_c.action != "no_solution":
            # Only add if it's different from A or B
            if not any(opt_c.total_cost == o.total_cost for o in options):
                options.append(opt_c)

        if not options:
            options.append(RescheduleOption(
                action="no_solution", moves=[], total_cost=9999,
                explanation="No feasible rescheduling found within constraints.",
                strategy=self.strategy,
            ))

        # Sort by cost, pick recommended
        options.sort(key=lambda o: o.total_cost)
        recommended = options[0] if options[0].action != "no_solution" else None

        return RescheduleResult(
            has_conflict=True,
            conflicting_events=conflict_info,
            options=options[:3],  # Return top 3
            recommended_option=recommended,
        )

    def _option_move_new(self, new_event: ScheduleEvent,
                         existing: List[ScheduleEvent]) -> Optional[RescheduleOption]:
        """Option A: Move the new event to a free slot."""
        result = find_best_slot_for_event(new_event, existing, self.min_time, self.max_time)
        if not result:
            return None

        new_start, slot_cost = result
        new_end = new_start + new_event.duration

        # Priority penalty: higher priority events cost more to move (quadratic scaling)
        priority_penalty = (new_event.priority ** 2) * 0.15

        # Strategy adjustment
        strategy_factor = {
            "minimize_moves": 0.7,   # Favor this (fewer total moves)
            "maximize_quality": 1.8 if new_event.priority >= 8 else 0.5,
            "balanced": 1.0,
        }.get(self.strategy, 1.0)

        total_cost = (slot_cost + priority_penalty) * strategy_factor

        move = MoveAction(
            event_id=new_event.id, event_title=new_event.title,
            original_start=new_event.start_minutes, original_end=new_event.end_minutes,
            new_start=new_start, new_end=new_end,
            priority=new_event.priority, cost=total_cost,
            reason=f"Move new event '{new_event.title}' to avoid conflict",
        )

        return RescheduleOption(
            action="move_new", moves=[move], total_cost=total_cost,
            explanation=self._explain_move(move),
            strategy=self.strategy,
        )

    def _option_move_existing(self, new_event: ScheduleEvent,
                              existing: List[ScheduleEvent],
                              conflicts: List[ScheduleEvent]) -> Optional[RescheduleOption]:
        """Option B: Keep new event in place, move conflicting events."""
        # Only move events that are lower priority than the new one (or all if maximize_quality)
        movable = [e for e in conflicts if not e.is_fixed]
        if not movable:
            return None

        all_with_new = [e for e in existing if e.id not in {c.id for c in movable}] + [new_event]
        moves = []
        total_cost = 0.0
        failed = False

        # Sort: move lowest priority first
        movable.sort(key=lambda e: e.priority)

        for event in movable:
            result = find_best_slot_for_event(event, all_with_new, self.min_time, self.max_time)
            if not result:
                failed = True
                break

            new_start, slot_cost = result
            new_end = new_start + event.duration

            move = MoveAction(
                event_id=event.id, event_title=event.title,
                original_start=event.start_minutes, original_end=event.end_minutes,
                new_start=new_start, new_end=new_end,
                priority=event.priority, cost=slot_cost,
                reason=f"Move '{event.title}' (priority {event.priority}) to make room for "
                       f"'{new_event.title}' (priority {new_event.priority})",
            )
            moves.append(move)
            # Priority penalty: higher priority events cost more to move (quadratic scaling)
            priority_penalty = (event.priority ** 2) * 0.15
            total_cost += slot_cost + priority_penalty

            # Update the "all_with_new" list with the moved event
            moved_event = event.copy_to(new_start)
            all_with_new.append(moved_event)

        if failed:
            return None

        # Strategy adjustment — consider priorities of events being moved
        max_moved_priority = max((m.priority for m in moves), default=0)
        strategy_factor = {
            "minimize_moves": 1.3,   # Penalize multiple moves
            "maximize_quality": 0.4 if max_moved_priority <= 5 else 1.8,  # Penalize moving high-priority events
            "balanced": 1.0,
        }.get(self.strategy, 1.0)

        total_cost *= strategy_factor

        explanation_parts = [self._explain_move(m) for m in moves]
        explanation = "Keep new event in place. " + " ".join(explanation_parts)

        return RescheduleOption(
            action="move_existing", moves=moves, total_cost=total_cost,
            explanation=explanation,
            strategy=self.strategy,
        )

    def _option_astar(self, new_event: ScheduleEvent,
                      existing: List[ScheduleEvent]) -> Optional[RescheduleOption]:
        """Option C: A* search for optimal schedule."""
        all_events = existing + [new_event]
        events_map = {e.id: e for e in all_events}

        initial_conflicts = find_all_conflicts(all_events)
        if not initial_conflicts:
            return None

        h0 = calculate_priority_loss(initial_conflicts, events_map, self.strategy)
        initial_state = ScheduleState(
            f_score=h0, events=list(all_events),
            moves=[], g_cost=0.0, h_cost=h0,
        )

        open_list: List[ScheduleState] = [initial_state]
        closed_keys = set()
        iterations = 0
        max_iterations = 200  # Prevent runaway search

        best_solution = None

        while open_list and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_list)

            key = current.state_key()
            if key in closed_keys:
                continue
            closed_keys.add(key)

            # Check if goal (no conflicts)
            current_conflicts = find_all_conflicts(current.events)
            if not current_conflicts:
                best_solution = current
                break

            # Limit search depth
            if len(current.moves) >= self.max_depth:
                if best_solution is None or current.f_score < best_solution.f_score:
                    best_solution = current
                continue

            # Expand: try moving each event involved in a conflict
            tried_events = set()
            for id1, id2 in current_conflicts:
                for eid in (id1, id2):
                    if eid in tried_events:
                        continue
                    tried_events.add(eid)

                    event = events_map.get(eid)
                    if not event or event.is_fixed:
                        continue

                    # Find current position of this event in state
                    current_event = next((e for e in current.events if e.id == eid), None)
                    if not current_event:
                        continue

                    others = [e for e in current.events if e.id != eid]
                    result = find_best_slot_for_event(current_event, others, self.min_time, self.max_time)
                    if not result:
                        continue

                    new_start, slot_cost = result
                    moved = current_event.copy_to(new_start)
                    new_events = others + [moved]

                    # Calculate original displacement
                    orig_event = events_map[eid]
                    move = MoveAction(
                        event_id=eid, event_title=event.title,
                        original_start=orig_event.start_minutes, original_end=orig_event.end_minutes,
                        new_start=new_start, new_end=new_start + event.duration,
                        priority=event.priority, cost=slot_cost,
                        reason=f"A* move '{event.title}' to resolve conflict",
                    )

                    new_moves = current.moves + [move]
                    g = calculate_displacement_cost(new_moves)
                    new_map = {e.id: e for e in new_events}
                    new_conflicts = find_all_conflicts(new_events)
                    h = calculate_priority_loss(new_conflicts, new_map, self.strategy)
                    f = g + h

                    new_state = ScheduleState(
                        f_score=f, events=new_events,
                        moves=new_moves, g_cost=g, h_cost=h,
                    )

                    if new_state.state_key() not in closed_keys:
                        heapq.heappush(open_list, new_state)

        if best_solution and best_solution.moves:
            return RescheduleOption(
                action="optimal_astar",
                moves=best_solution.moves,
                total_cost=best_solution.f_score,
                explanation=f"A* found optimal solution in {iterations} iterations. "
                           + " ".join(self._explain_move(m) for m in best_solution.moves),
                strategy=self.strategy,
            )

        return None

    @staticmethod
    def _explain_move(move: MoveAction) -> str:
        """Generate human-readable explanation for a move."""
        orig_h, orig_m = divmod(move.original_start, 60)
        new_h, new_m = divmod(move.new_start, 60)
        new_end_h, new_end_m = divmod(move.new_end, 60)
        return (
            f"Move '{move.event_title}' from {orig_h:02d}:{orig_m:02d} "
            f"to {new_h:02d}:{new_m:02d}-{new_end_h:02d}:{new_end_m:02d} "
            f"(priority: {move.priority}, cost: {move.cost:.1f})."
        )


# ============================================================================
# High-Level Service Interface
# ============================================================================

class SchedulingService:
    """
    Main service that connects the scheduling optimizer with the database layer.
    Converts DB events + user priorities into ScheduleEvents, runs the optimizer,
    and returns structured results.
    """

    def __init__(self):
        self.default_priorities = {
            "meeting": 7, "exam": 10, "study": 8, "deadline": 10,
            "appointment": 7, "class": 8, "work": 8, "exercise": 5,
            "social": 4, "party": 3, "personal": 5, "travel": 6, "other": 5,
        }

    def convert_db_event(self, event_dict: Dict, priority_config: Optional[Dict] = None) -> ScheduleEvent:
        """Convert a database event dict to a ScheduleEvent."""
        priorities = {**self.default_priorities, **(priority_config or {})}

        event_type = self._infer_event_type(
            event_dict.get("title", ""),
            event_dict.get("category_name", ""),
        )
        priority = priorities.get(event_type, 5)

        # Handle both datetime objects and hour/minute dicts
        if isinstance(event_dict.get("start_time"), datetime):
            start_dt = event_dict["start_time"]
            end_dt = event_dict["end_time"]
            start_min = start_dt.hour * 60 + start_dt.minute
            end_min = end_dt.hour * 60 + end_dt.minute
        else:
            start_min = event_dict.get("start_hour", 0) * 60 + event_dict.get("start_minute", 0)
            end_min = event_dict.get("end_hour", 0) * 60 + event_dict.get("end_minute", 0)

        is_fixed = event_dict.get("is_fixed", False) or event_type in ("exam", "deadline")

        return ScheduleEvent(
            id=str(event_dict.get("id", "")),
            title=event_dict.get("title", ""),
            start_minutes=start_min,
            end_minutes=end_min,
            priority=priority,
            event_type=event_type,
            is_fixed=is_fixed,
        )

    def reschedule(
        self,
        new_event_dict: Dict,
        existing_events_dicts: List[Dict],
        priority_config: Optional[Dict] = None,
        strategy: str = "balanced",
        min_hour: int = 6,
        max_hour: int = 23,
    ) -> RescheduleResult:
        """
        Main rescheduling entry point.

        Args:
            new_event_dict: The new event to add
            existing_events_dicts: Current events on the same day
            priority_config: User's priority weights from Phase 1
            strategy: "minimize_moves", "maximize_quality", or "balanced"
            min_hour: Earliest scheduling hour
            max_hour: Latest scheduling hour
        """
        new_event = self.convert_db_event(new_event_dict, priority_config)
        existing = [self.convert_db_event(e, priority_config) for e in existing_events_dicts]

        optimizer = ScheduleOptimizer(
            strategy=strategy,
            min_time=min_hour * 60,
            max_time=max_hour * 60,
        )

        return optimizer.optimize(existing, new_event)

    def _infer_event_type(self, title: str, category_name: str = "") -> str:
        """Infer event type from title and category using keyword matching."""
        text = (title + " " + category_name).lower()

        type_keywords = {
            "exam": ["exam", "test", "quiz", "midterm", "final", "สอบ"],
            "meeting": ["meeting", "meet", "standup", "sync", "ประชุม", "daily scrum"],
            "study": ["study", "homework", "assignment", "research", "review", "อ่านหนังสือ"],
            "class": ["class", "lecture", "lab", "tutorial", "เรียน"],
            "deadline": ["deadline", "due", "submit", "ส่งงาน"],
            "exercise": ["exercise", "gym", "run", "sport", "yoga", "workout", "ออกกำลังกาย", "football", "basketball", "swim","cycling", "hiking", "volleyball", "tennis","badminton","boxing", "martial arts", "dance"],
            "party": ["party", "celebration", "ปาร์ตี้"],
            "social": ["lunch", "dinner", "hangout", "coffee", "social", "เจอเพื่อน","hangout"],
            "work": ["work", "shift", "office", "ทำงาน"],
            "appointment": ["doctor", "dentist", "appointment", "นัดหมาย"],
            "travel": ["travel", "trip", "flight", "เดินทาง"],
            "personal": ["personal", "errands", "ธุระ"],
        }

        for event_type, keywords in type_keywords.items():
            if any(kw in text for kw in keywords):
                return event_type

        return "other"

    def get_event_priority(self, title: str, category_name: str = "",
                           priority_config: Optional[Dict] = None) -> Dict:
        """Get priority info for an event based on its title/category."""
        priorities = {**self.default_priorities, **(priority_config or {})}
        event_type = self._infer_event_type(title, category_name)
        priority = priorities.get(event_type, 5)

        return {
            "event_type": event_type,
            "priority": priority,
            "is_critical": priority >= 8,
            "is_movable": event_type not in ("exam", "deadline"),
        }
