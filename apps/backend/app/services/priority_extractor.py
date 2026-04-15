"""Service for extracting user priorities from persona using LLM."""

import json
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user_profile import UserProfile
from app.agent.llm_clients import BaseLLMClient, get_llm_client
from app.agent.prompts.priority_extraction import (
    PRIORITY_EXTRACTION_SYSTEM_PROMPT,
    PRIORITY_EXTRACTION_USER_TEMPLATE,
    PRIORITY_UPDATE_PROMPT,
)

logger = logging.getLogger(__name__)


class PriorityExtractionResult:
    """Result of priority extraction from LLM."""
    
    def __init__(
        self,
        success: bool,
        priorities: Optional[dict] = None,
        persona_summary: Optional[str] = None,
        reasoning: Optional[str] = None,
        recommended_strategy: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.priorities = priorities or {}
        self.persona_summary = persona_summary
        self.reasoning = reasoning
        self.recommended_strategy = recommended_strategy
        self.error = error
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "priorities": self.priorities,
            "persona_summary": self.persona_summary,
            "reasoning": self.reasoning,
            "recommended_strategy": self.recommended_strategy,
            "error": self.error,
        }


class PriorityExtractorService:
    """Service for extracting and managing user priorities."""
    
    def __init__(self, db: AsyncSession, llm_client: Optional[BaseLLMClient] = None):
        self.db = db
        self.llm_client = llm_client or get_llm_client()
    
    async def extract_priorities_from_story(
        self, 
        user_story: str
    ) -> PriorityExtractionResult:
        """Extract priority weights from user's story using LLM.
        
        Args:
            user_story: Natural language description of user's persona
            
        Returns:
            PriorityExtractionResult with extracted priorities
        """
        if not user_story or not user_story.strip():
            return PriorityExtractionResult(
                success=False,
                error="User story is empty"
            )
        
        try:
            # Build the prompt
            user_prompt = PRIORITY_EXTRACTION_USER_TEMPLATE.format(
                user_story=user_story
            )
            
            # Call LLM
            response = await self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=PRIORITY_EXTRACTION_SYSTEM_PROMPT,
            )
            
            if not response or not response.strip():
                return PriorityExtractionResult(
                    success=False,
                    error="LLM returned empty response"
                )
            
            # Parse JSON response
            # Clean up response (remove markdown code blocks if present)
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            try:
                data = json.loads(cleaned_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Response was: {response}")
                return PriorityExtractionResult(
                    success=False,
                    error=f"Failed to parse LLM response: {str(e)}"
                )
            
            # Validate and normalize priorities
            priorities = data.get("priorities", {})
            normalized_priorities = {}
            
            for event_type, weight in priorities.items():
                # Ensure weight is within bounds
                try:
                    weight_int = int(weight)
                    normalized_priorities[event_type.lower()] = max(1, min(10, weight_int))
                except (ValueError, TypeError):
                    normalized_priorities[event_type.lower()] = 5  # Default
            
            return PriorityExtractionResult(
                success=True,
                priorities=normalized_priorities,
                persona_summary=data.get("persona_summary"),
                reasoning=data.get("reasoning"),
                recommended_strategy=data.get("recommended_strategy", "balanced"),
            )
            
        except Exception as e:
            logger.exception(f"Error extracting priorities: {e}")
            return PriorityExtractionResult(
                success=False,
                error=str(e)
            )
    
    async def get_or_create_profile(self, user_id) -> UserProfile:
        """Get existing profile or create a new one."""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        
        return profile
    
    async def save_user_story(
        self, 
        user_id, 
        user_story: str,
        extract_priorities: bool = True
    ) -> tuple[UserProfile, Optional[PriorityExtractionResult]]:
        """Save user story and optionally extract priorities.
        
        Args:
            user_id: UUID of the user
            user_story: Natural language persona description
            extract_priorities: Whether to extract priorities from story
            
        Returns:
            Tuple of (UserProfile, PriorityExtractionResult or None)
        """
        profile = await self.get_or_create_profile(user_id)
        profile.user_story = user_story
        
        extraction_result = None
        
        if extract_priorities:
            extraction_result = await self.extract_priorities_from_story(user_story)
            
            if extraction_result.success:
                profile.priority_config = extraction_result.priorities
                profile.priorities_extracted_at = datetime.utcnow().isoformat()
                
                if extraction_result.recommended_strategy:
                    profile.scheduling_strategy = extraction_result.recommended_strategy
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile, extraction_result
    
    async def update_priorities_manually(
        self,
        user_id,
        priorities: dict,
        strategy: Optional[str] = None
    ) -> UserProfile:
        """Manually update user's priorities.
        
        Args:
            user_id: UUID of the user
            priorities: Dict of event_type -> weight
            strategy: Optional scheduling strategy
            
        Returns:
            Updated UserProfile
        """
        profile = await self.get_or_create_profile(user_id)
        
        # Normalize and validate priorities
        normalized = {}
        for event_type, weight in priorities.items():
            try:
                weight_int = int(weight)
                normalized[event_type.lower()] = max(1, min(10, weight_int))
            except (ValueError, TypeError):
                normalized[event_type.lower()] = 5
        
        profile.priority_config = normalized
        profile.priorities_extracted_at = datetime.utcnow().isoformat()
        
        if strategy and strategy in ["minimize_moves", "maximize_quality", "balanced"]:
            profile.scheduling_strategy = strategy
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile
    
    async def get_user_priorities(self, user_id) -> dict:
        """Get merged priorities for a user (defaults + extracted).
        
        Returns priorities dict with all event types and their weights.
        """
        profile = await self.get_or_create_profile(user_id)
        return profile.merge_priorities()
    
    async def get_priority_for_event_type(
        self, 
        user_id, 
        event_type: str
    ) -> int:
        """Get priority weight for a specific event type.
        
        Args:
            user_id: UUID of the user
            event_type: Type of event (e.g., "meeting", "exam")
            
        Returns:
            Priority weight (1-10)
        """
        profile = await self.get_or_create_profile(user_id)
        return profile.get_priority(event_type)
