"""Scheduling API — Priority-aware rescheduling with A* optimization.

Endpoints:
  POST /scheduling/reschedule                  — Analyze conflicts & suggest rescheduling
  POST /scheduling/suggest-conflict-resolution — AI-suggest best times for conflicting events
  POST /scheduling/priority                    — Check inferred priority for an event title
  GET  /scheduling/constraints                 — Get hard/soft constraint definitions
"""

import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Event, Calendar, UserProfile, Category
from app.schemas.scheduling import (
    RescheduleRequest,
    RescheduleResponse,
    RescheduleOptionResponse,
    MoveActionResponse,
    EventPriorityCheckRequest,
    EventPriorityCheckResponse,
    ConflictSuggestionRequest,
    ConflictSuggestionResponse,
    EventSuggestions,
    TimeSuggestion,
)
from app.services.scheduling_service import (
    SchedulingService, MoveAction,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduling", tags=["scheduling"])

def _minutes_to_time_str(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def _move_to_response(move: MoveAction) -> MoveActionResponse:
    return MoveActionResponse(
        event_id=move.event_id,
        event_title=move.event_title,
        original_start_time=_minutes_to_time_str(move.original_start),
        original_end_time=_minutes_to_time_str(move.original_end),
        new_start_time=_minutes_to_time_str(move.new_start),
        new_end_time=_minutes_to_time_str(move.new_end),
        priority=move.priority,
        cost=round(move.cost, 2),
        reason=move.reason,
    )


async def _get_user_priority_config(db: AsyncSession, user_id: str) -> dict:
    """Load user's priority config from the database."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        return profile.merge_priorities()
    return {}


async def _get_day_events(
    db: AsyncSession, calendar_id: UUID,
    target_date: datetime, exclude_event_id: Optional[UUID] = None
) -> list[dict]:
    """Fetch all events on the same day as target_date."""
    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    query = select(Event).where(
        and_(
            Event.calendar_id == calendar_id,
            Event.start_time >= day_start,
            Event.start_time <= day_end,
            Event.status != "cancelled",
        )
    )
    if exclude_event_id:
        query = query.where(Event.id != exclude_event_id)

    result = await db.execute(query)
    events = result.scalars().all()

    event_dicts = []
    for e in events:
        # Get category name
        cat_name = ""
        if e.category_id:
            cat_result = await db.execute(
                select(Category).where(Category.id == e.category_id)
            )
            cat = cat_result.scalar_one_or_none()
            if cat:
                cat_name = cat.name

        event_dicts.append({
            "id": str(e.id),
            "title": e.title,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "category_name": cat_name,
            "is_fixed": False,
        })

    return event_dicts


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/reschedule", response_model=RescheduleResponse)
async def reschedule_event(
    data: RescheduleRequest,
    user_id: str = Query(..., description="User ID for priority config"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze conflicts for a new event and suggest rescheduling options.

    Uses A* search with priority-weighted heuristic to find optimal solutions.
    Three strategies available:
      - minimize_moves: Fewest events rescheduled
      - maximize_quality: Protect high-priority events
      - balanced: Weighted combination
    """
    # Load user priorities
    priority_config = await _get_user_priority_config(db, user_id)

    # Fetch existing events on the same day
    existing = await _get_day_events(db, data.calendar_id, data.start_time)

    # Build new event dict
    new_event = {
        "id": "new-event",
        "title": data.title,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "category_name": data.category_name or "",
        "is_fixed": False,
    }

    # Run the scheduler
    service = SchedulingService()
    result = service.reschedule(
        new_event_dict=new_event,
        existing_events_dicts=existing,
        priority_config=priority_config,
        strategy=data.strategy,
        min_hour=data.min_hour,
        max_hour=data.max_hour,
    )

    # Convert to response
    options = []
    for opt in result.options:
        options.append(RescheduleOptionResponse(
            action=opt.action,
            moves=[_move_to_response(m) for m in opt.moves],
            total_cost=round(opt.total_cost, 2),
            explanation=opt.explanation,
            strategy=opt.strategy,
        ))

    recommended = None
    if result.recommended_option:
        recommended = RescheduleOptionResponse(
            action=result.recommended_option.action,
            moves=[_move_to_response(m) for m in result.recommended_option.moves],
            total_cost=round(result.recommended_option.total_cost, 2),
            explanation=result.recommended_option.explanation,
            strategy=result.recommended_option.strategy,
        )

    return RescheduleResponse(
        has_conflict=result.has_conflict,
        conflicting_events=result.conflicting_events,
        options=options,
        recommended=recommended,
    )


@router.post("/priority", response_model=EventPriorityCheckResponse)
async def check_event_priority(
    data: EventPriorityCheckRequest,
    user_id: str = Query(..., description="User ID for priority config"),
    db: AsyncSession = Depends(get_db),
):
    """
    Check the inferred priority of an event based on its title.

    Returns event type classification, priority weight, and whether
    the event would be considered critical or movable.
    """
    priority_config = await _get_user_priority_config(db, user_id)

    service = SchedulingService()
    info = service.get_event_priority(
        title=data.title,
        category_name=data.category_name or "",
        priority_config=priority_config,
    )

    merged = {**service.default_priorities, **(priority_config or {})}

    return EventPriorityCheckResponse(
        event_type=info["event_type"],
        priority=info["priority"],
        is_critical=info["is_critical"],
        is_movable=info["is_movable"],
        priority_config=merged,
    )


@router.get("/constraints")
async def get_constraints():
    """
    Get the constraint definitions used by the scheduler.

    Returns both hard constraints (must satisfy) and soft constraints
    (preferences with penalty costs).
    """
    return {
        "hard_constraints": [
            {
                "name": "no_time_overlap",
                "description": "Events cannot overlap in time",
                "type": "hard",
            },
            {
                "name": "within_bounds",
                "description": "Events must be within scheduling bounds (default 6:00-23:00)",
                "type": "hard",
            },
            {
                "name": "positive_duration",
                "description": "Event end time must be after start time",
                "type": "hard",
            },
            {
                "name": "fixed_events",
                "description": "Exams and deadlines cannot be moved",
                "type": "hard",
            },
        ],
        "soft_constraints": [
            {
                "name": "preferred_time",
                "description": "Events should be scheduled during their preferred time window",
                "type": "soft",
                "penalty": "0-10 based on distance from preferred window",
            },
            {
                "name": "buffer_time",
                "description": "Events should have at least 15 minutes buffer between them",
                "type": "soft",
                "penalty": "3 per close event",
            },
            {
                "name": "priority_scheduling",
                "description": "High-priority events should be in peak hours (9am-5pm)",
                "type": "soft",
                "penalty": "(priority - 7) × 3 for off-peak scheduling",
            },
            {
                "name": "daily_overload",
                "description": "Day should not have too many events (>6 warning, >8 penalty)",
                "type": "soft",
                "penalty": "2 per event over 6, 5 per event over 8",
            },
        ],
        "strategies": {
            "minimize_moves": "Fewest events rescheduled. Good for stable schedules.",
            "maximize_quality": "Protect high-priority events. Good for important work.",
            "balanced": "Weighted combination. General purpose (default).",
        },
        "cost_function": {
            "f(n)": "g(n) + h(n)",
            "g(n)": "Displacement cost: base_penalty(3) + hours_shifted × 2 + priority × 0.5",
            "h(n)": "Priority loss: priority² × strategy_weight for each remaining conflict",
        },
    }


def _find_closest_free_slots(
    occupied: List[tuple],
    target_start: datetime,
    duration: timedelta,
    day_start: datetime,
    day_end: datetime,
    n: int = 3,
    step_minutes: int = 30,
) -> List[tuple]:
    """
    Find the N free time slots closest to target_start.

    Works directly with UTC datetimes — no minute-from-midnight conversion.
    Scans the window [day_start, day_end) in step_minutes increments,
    skips occupied periods, and ranks by absolute distance to target_start.

    Args:
        occupied: list of (start_dt, end_dt) tuples for busy periods
        target_start: the original event start time (to minimize distance from)
        duration: how long the event needs
        day_start: earliest possible start for a slot
        day_end: latest possible end for a slot
        n: how many results to return
        step_minutes: scan granularity

    Returns: list of (new_start_dt, new_end_dt, distance_minutes) sorted by distance
    """
    step = timedelta(minutes=step_minutes)
    slots = []
    current = day_start
    while current + duration <= day_end:
        slot_end = current + duration
        conflict = any(current < occ_end and occ_start < slot_end
                       for occ_start, occ_end in occupied)
        if not conflict:
            dist = abs((current - target_start).total_seconds()) / 60.0
            slots.append((current, slot_end, dist))
        current += step

    slots.sort(key=lambda x: x[2])
    return slots[:n]


@router.post("/suggest-conflict-resolution", response_model=ConflictSuggestionResponse)
async def suggest_conflict_resolution(
    data: ConflictSuggestionRequest,
    user_id: str = Query(..., description="User ID for priority config"),
    db: AsyncSession = Depends(get_db),
):
    """
    Suggest the 3 closest available time slots for each conflicting event.

    Works directly with UTC datetimes to avoid timezone conversion issues.
    Scans the full 24h window of the event's day in 30-min steps, treating
    all other events + the collab event as occupied blocks, then ranks
    free slots by absolute time distance from the original event start.
    If the same day has fewer than 3 slots, checks ±1 and ±2 adjacent days.
    """
    event_suggestions_list: List[EventSuggestions] = []

    for event_id in data.event_ids:
        event_q = await db.execute(select(Event).where(Event.id == event_id))
        ev = event_q.scalar_one_or_none()
        if not ev:
            continue

        duration = ev.end_time - ev.start_time
        base_date = ev.start_time.date()
        collab_start = data.collab_event_start
        collab_end = data.collab_event_end
        collab_date = collab_start.date()

        all_candidates: list[dict] = []

        for day_offset in [0, 1, -1, 2, -2]:
            check_date = base_date + timedelta(days=day_offset)
            day_start_dt = datetime(check_date.year, check_date.month, check_date.day,
                                    tzinfo=dt_timezone.utc)
            day_end_dt = day_start_dt + timedelta(hours=24)

            # Fetch occupied events on this day
            day_events = await _get_day_events(
                db, ev.calendar_id, day_start_dt, exclude_event_id=ev.id,
            )

            occupied: List[tuple] = []
            for de in day_events:
                s = de["start_time"]
                e = de["end_time"]
                # Ensure timezone-aware
                if s.tzinfo is None:
                    s = s.replace(tzinfo=dt_timezone.utc)
                if e.tzinfo is None:
                    e = e.replace(tzinfo=dt_timezone.utc)
                occupied.append((s, e))

            # Add collab event as occupied on its day
            if check_date == collab_date:
                cs = collab_start if collab_start.tzinfo else collab_start.replace(tzinfo=dt_timezone.utc)
                ce = collab_end if collab_end.tzinfo else collab_end.replace(tzinfo=dt_timezone.utc)
                occupied.append((cs, ce))

            # The target start: same wall-clock time projected onto check_date
            target_start = datetime(
                check_date.year, check_date.month, check_date.day,
                ev.start_time.hour, ev.start_time.minute,
                tzinfo=dt_timezone.utc,
            )

            slots = _find_closest_free_slots(
                occupied, target_start, duration, day_start_dt, day_end_dt, n=3,
            )

            for new_start, new_end, dist in slots:
                day_penalty = abs(day_offset) * 1440.0
                total_dist = dist + day_penalty

                all_candidates.append({
                    "new_start": new_start.isoformat(),
                    "new_end": new_end.isoformat(),
                    "cost": round(total_dist, 2),
                    "explanation": "Same day" if day_offset == 0 else f"on {check_date.strftime('%b %d')}",
                })

            if day_offset == 0 and len(all_candidates) >= 3:
                break

        all_candidates.sort(key=lambda c: c["cost"])
        top = all_candidates[:3]

        event_suggestions_list.append(EventSuggestions(
            event_id=str(ev.id),
            event_title=ev.title,
            original_start=ev.start_time.isoformat(),
            original_end=ev.end_time.isoformat(),
            suggestions=[TimeSuggestion(**s) for s in top],
        ))

    return ConflictSuggestionResponse(event_suggestions=event_suggestions_list)
