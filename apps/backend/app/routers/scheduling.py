"""Scheduling API — Priority-aware rescheduling with A* optimization.

Endpoints:
  POST /scheduling/reschedule   — Analyze conflicts & suggest rescheduling
  POST /scheduling/priority     — Check inferred priority for an event title
  GET  /scheduling/constraints  — Get hard/soft constraint definitions
"""

import logging
from datetime import datetime, timezone as dt_timezone
from typing import Optional
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
)
from app.services.scheduling_service import SchedulingService, MoveAction

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
