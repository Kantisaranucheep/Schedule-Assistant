"""User profile/persona API endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user_profile import UserProfile
from app.services.priority_extractor import PriorityExtractorService
from app.schemas.user_profile import (
    UserStoryRequest,
    PriorityUpdateRequest,
    StrategyUpdateRequest,
    PriorityExtractionResponse,
    UserProfileResponse,
    UserProfileWithExtractionResponse,
    EventPriorityRequest,
    EventPriorityResponse,
)

router = APIRouter(prefix="/user-profile", tags=["user-profile"])


def _profile_to_response(profile: UserProfile) -> UserProfileResponse:
    """Convert UserProfile model to response schema."""
    return UserProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        user_story=profile.user_story,
        priority_config=profile.priority_config,
        default_priorities=profile.default_priorities,
        scheduling_strategy=profile.scheduling_strategy,
        priorities_extracted_at=profile.priorities_extracted_at,
        merged_priorities=profile.merge_priorities(),
    )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get user profile with priorities.
    
    Returns the user's profile including their story, extracted priorities,
    and merged priority configuration.
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    service = PriorityExtractorService(db)
    profile = await service.get_or_create_profile(user_uuid)
    
    return _profile_to_response(profile)


@router.post("/{user_id}/story", response_model=UserProfileWithExtractionResponse)
async def save_user_story(
    user_id: str,
    request: UserStoryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save user story and extract priorities.
    
    Accepts a natural language description of who the user is (their persona),
    uses LLM to analyze it and extract event type priority weights.
    
    Example story:
    "I'm a third year software engineering student. My priorities are 
    graduating on time and getting a good internship. I value my study time
    and team meetings, but I also try to maintain work-life balance."
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    service = PriorityExtractorService(db)
    profile, extraction_result = await service.save_user_story(
        user_uuid, 
        request.user_story,
        extract_priorities=request.extract_priorities
    )
    
    extraction_response = None
    if extraction_result:
        extraction_response = PriorityExtractionResponse(
            success=extraction_result.success,
            priorities=extraction_result.priorities,
            persona_summary=extraction_result.persona_summary,
            reasoning=extraction_result.reasoning,
            recommended_strategy=extraction_result.recommended_strategy,
            error=extraction_result.error,
        )
    
    return UserProfileWithExtractionResponse(
        profile=_profile_to_response(profile),
        extraction=extraction_response,
    )


@router.post("/{user_id}/extract", response_model=PriorityExtractionResponse)
async def extract_priorities(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Re-extract priorities from existing user story.
    
    Useful when you want to re-analyze the user's story with potentially
    updated LLM capabilities.
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    service = PriorityExtractorService(db)
    profile = await service.get_or_create_profile(user_uuid)
    
    if not profile.user_story:
        raise HTTPException(
            status_code=400, 
            detail="No user story saved. Please save a story first."
        )
    
    profile, extraction_result = await service.save_user_story(
        user_uuid,
        profile.user_story,
        extract_priorities=True
    )
    
    if extraction_result:
        return PriorityExtractionResponse(
            success=extraction_result.success,
            priorities=extraction_result.priorities,
            persona_summary=extraction_result.persona_summary,
            reasoning=extraction_result.reasoning,
            recommended_strategy=extraction_result.recommended_strategy,
            error=extraction_result.error,
        )
    
    raise HTTPException(status_code=500, detail="Extraction failed")


@router.put("/{user_id}/priorities", response_model=UserProfileResponse)
async def update_priorities(
    user_id: str,
    request: PriorityUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually update priority weights.
    
    Allows users to override or fine-tune the LLM-extracted priorities.
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    service = PriorityExtractorService(db)
    profile = await service.update_priorities_manually(
        user_uuid,
        request.priorities,
        request.strategy
    )
    
    return _profile_to_response(profile)


@router.put("/{user_id}/strategy", response_model=UserProfileResponse)
async def update_strategy(
    user_id: str,
    request: StrategyUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update scheduling strategy.
    
    Strategies:
    - minimize_moves: Prefer solutions that move the fewest events
    - maximize_quality: Protect high-priority events at all costs
    - balanced: Weighted balance between moves and quality
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    service = PriorityExtractorService(db)
    profile = await service.get_or_create_profile(user_uuid)
    profile.scheduling_strategy = request.strategy
    
    await db.commit()
    await db.refresh(profile)
    
    return _profile_to_response(profile)


@router.get("/{user_id}/priorities", response_model=dict)
async def get_priorities(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get merged priorities for user.
    
    Returns combined priority weights from defaults and extracted priorities.
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    service = PriorityExtractorService(db)
    priorities = await service.get_user_priorities(user_uuid)
    
    return {"priorities": priorities}


@router.get("/{user_id}/priority/{event_type}", response_model=EventPriorityResponse)
async def get_event_priority(
    user_id: str,
    event_type: str,
    db: AsyncSession = Depends(get_db),
):
    """Get priority weight for a specific event type.
    
    Useful when scheduling a single event to know its relative importance.
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    service = PriorityExtractorService(db)
    profile = await service.get_or_create_profile(user_uuid)
    
    event_type_lower = event_type.lower()
    
    # Determine source
    if profile.priority_config and event_type_lower in profile.priority_config:
        source = "extracted"
        priority = profile.priority_config[event_type_lower]
    elif profile.default_priorities and event_type_lower in profile.default_priorities:
        source = "default"
        priority = profile.default_priorities[event_type_lower]
    else:
        source = "fallback"
        priority = 5
    
    return EventPriorityResponse(
        event_type=event_type,
        priority=priority,
        source=source,
    )


@router.delete("/{user_id}", status_code=204)
async def delete_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete user profile and all priority data."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_uuid)
    )
    profile = result.scalar_one_or_none()
    
    if profile:
        await db.delete(profile)
        await db.commit()
