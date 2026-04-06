# apps/backend/app/chat/llm_service.py
"""
LLM Service - Handles communication with Ollama LLM.

This service sends prompts to Ollama and parses JSON responses.
It does NOT generate natural language responses - only converts user input to structured data.
"""

import json
import re
from typing import Optional, Dict, Any, Tuple

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.chat.prompts import (
    build_intent_prompt,
    build_yes_no_prompt,
    build_preference_prompt,
    build_slot_selection_prompt,
    build_field_collection_prompt,
    build_confirmation_prompt,
    build_edit_field_prompt,
)


class LLMService:
    """Service for interacting with Ollama LLM."""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = 60.0  # seconds
    
    async def _call_ollama(self, prompt: str) -> Tuple[bool, str]:
        """
        Call Ollama API with a prompt.
        
        Returns:
            Tuple of (success, response_text)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temperature for consistent JSON
                            "num_predict": 500,  # Limit response length
                        }
                    }
                )
                
                if response.status_code != 200:
                    return False, f"Ollama API error: {response.status_code}"
                
                data = response.json()
                return True, data.get("response", "")
                
        except httpx.TimeoutException:
            return False, "LLM request timed out"
        except httpx.RequestError as e:
            return False, f"LLM request failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response text.
        
        The LLM might include extra text before/after the JSON.
        """
        # Try to find JSON in the response
        text = text.strip()
        
        # If the entire response is JSON
        if text.startswith("{") and text.endswith("}"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        
        # Try to extract JSON from code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in the text
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    async def parse_intent(self, user_message: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Parse user intent from natural language.
        
        Returns:
            Tuple of (success, parsed_data, error_message)
        """
        prompt = build_intent_prompt(user_message)
        success, response = await self._call_ollama(prompt)
        
        if not success:
            return False, None, response
        
        data = self._extract_json(response)
        if data is None:
            return False, None, "Failed to parse LLM response as JSON"
        
        return True, data, ""
    
    async def parse_yes_no(self, user_message: str) -> Tuple[bool, Optional[bool], str]:
        """
        Parse yes/no response from user.
        
        Returns:
            Tuple of (success, answer (True/False), error_message)
        """
        prompt = build_yes_no_prompt(user_message)
        success, response = await self._call_ollama(prompt)
        
        if not success:
            return False, None, response
        
        data = self._extract_json(response)
        if data is None:
            return False, None, "Failed to parse LLM response as JSON"
        
        answer = data.get("answer")
        if answer is None:
            return False, None, "Response missing 'answer' field"
        
        return True, bool(answer), ""
    
    async def parse_preference(self, user_message: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Parse user preference for time slot finding.
        
        Returns:
            Tuple of (success, preference_data, error_message)
        """
        prompt = build_preference_prompt(user_message)
        success, response = await self._call_ollama(prompt)
        
        if not success:
            return False, None, response
        
        data = self._extract_json(response)
        if data is None:
            return False, None, "Failed to parse LLM response as JSON"
        
        if "choice" not in data:
            return False, None, "Response missing 'choice' field"
        
        return True, data, ""
    
    async def parse_slot_selection(self, user_message: str) -> Tuple[bool, Optional[int], str]:
        """
        Parse slot selection from user.
        
        Returns:
            Tuple of (success, choice_number (1-4), error_message)
        """
        prompt = build_slot_selection_prompt(user_message)
        success, response = await self._call_ollama(prompt)
        
        if not success:
            return False, None, response
        
        data = self._extract_json(response)
        if data is None:
            return False, None, "Failed to parse LLM response as JSON"
        
        choice = data.get("choice")
        if choice is None:
            return False, None, "Response missing 'choice' field"
        
        return True, int(choice), ""
    
    async def parse_field(self, field_name: str, user_message: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Parse a specific field value from user input.
        
        Returns:
            Tuple of (success, field_data, error_message)
        """
        prompt = build_field_collection_prompt(field_name, user_message)
        success, response = await self._call_ollama(prompt)
        
        if not success:
            return False, None, response
        
        data = self._extract_json(response)
        if data is None:
            return False, None, "Failed to parse LLM response as JSON"
        
        return True, data, ""
    
    async def parse_confirmation(self, user_message: str) -> Tuple[bool, Optional[bool], str]:
        """
        Parse confirmation response from user.
        
        Returns:
            Tuple of (success, confirmed (True/False), error_message)
        """
        prompt = build_confirmation_prompt(user_message)
        success, response = await self._call_ollama(prompt)
        
        if not success:
            return False, None, response
        
        data = self._extract_json(response)
        if data is None:
            return False, None, "Failed to parse LLM response as JSON"
        
        confirmed = data.get("confirmed")
        if confirmed is None:
            return False, None, "Response missing 'confirmed' field"
        
        return True, bool(confirmed), ""
    
    async def parse_edit_field(self, user_message: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Parse what field the user wants to edit and any values provided.
        
        Returns:
            Tuple of (success, parsed_data, error_message)
            parsed_data contains: field, new_day, new_month, new_year, new_start_hour, etc.
        """
        prompt = build_edit_field_prompt(user_message)
        success, response = await self._call_ollama(prompt)
        
        if not success:
            return False, None, response
        
        data = self._extract_json(response)
        if data is None:
            return False, None, "Failed to parse LLM response as JSON"
        
        field = data.get("field")
        if field not in ["date", "time", "title", "cancel", "both"]:
            return False, None, f"Invalid field type: {field}"
        
        return True, data, ""
    
    async def check_available(self) -> bool:
        """Check if LLM is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
