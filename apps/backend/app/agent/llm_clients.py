# apps/backend/app/agent/llm_clients.py
"""LLM client wrappers for Ollama and Gemini."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx

from app.agent.config import get_agent_settings
from app.agent.exceptions import LLMConnectionError


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM service is available."""
        pass


class OllamaClient(BaseLLMClient):
    """Client for Ollama local LLM service."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_agent_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response using Ollama API."""
        url = f"{self.base_url}/api/generate"

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent JSON output
                "num_predict": 1024,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except httpx.ConnectError as e:
            raise LLMConnectionError("Ollama", f"Connection failed: {str(e)}")
        except httpx.TimeoutException as e:
            raise LLMConnectionError("Ollama", f"Request timeout: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise LLMConnectionError("Ollama", f"HTTP error {e.response.status_code}: {e.response.text}")

    async def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return False

                # Check if model is available
                tags = response.json()
                models = [m.get("name", "").split(":")[0] for m in tags.get("models", [])]
                return self.model.split(":")[0] in models
        except Exception:
            return False


class GeminiClient(BaseLLMClient):
    """Client for Google Gemini API (placeholder implementation)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_agent_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response using Gemini API.

        Note: This is a placeholder implementation. Full implementation would require
        the google-generativeai package or direct API calls.
        """
        if not self.api_key:
            raise LLMConnectionError("Gemini", "API key not configured")

        url = f"{self.base_url}/models/{self.model}:generateContent"

        # Build content parts
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": system_prompt}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "I understand. I will follow these instructions."}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload,
                    params={"key": self.api_key},
                )
                response.raise_for_status()
                result = response.json()

                # Extract text from response
                candidates = result.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return ""
        except httpx.ConnectError as e:
            raise LLMConnectionError("Gemini", f"Connection failed: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise LLMConnectionError("Gemini", f"HTTP error {e.response.status_code}: {e.response.text}")

    async def is_available(self) -> bool:
        """Check if Gemini API is accessible."""
        if not self.api_key:
            return False

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    params={"key": self.api_key},
                )
                return response.status_code == 200
        except Exception:
            return False


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.default_response = json.dumps({
            "intent_type": "unknown",
            "confidence": 0.5,
            "data": None,
            "clarification_question": "I couldn't understand your request. Could you please rephrase?"
        })

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Return mock response based on prompt keywords."""
        prompt_lower = prompt.lower()

        # Simple keyword matching for testing
        if "schedule" in prompt_lower or "meeting" in prompt_lower or "create" in prompt_lower:
            return json.dumps({
                "intent_type": "create_event",
                "confidence": 0.9,
                "data": {
                    "title": "Test Meeting",
                    "date": "2024-01-20",
                    "start_time": "14:00",
                    "end_time": "15:00"
                }
            })
        elif "free" in prompt_lower or "available" in prompt_lower:
            return json.dumps({
                "intent_type": "find_free_slots",
                "confidence": 0.85,
                "data": {
                    "date_range": {
                        "start_date": "2024-01-20",
                        "end_date": "2024-01-26"
                    },
                    "duration_minutes": 60
                }
            })
        elif "move" in prompt_lower or "reschedule" in prompt_lower:
            return json.dumps({
                "intent_type": "move_event",
                "confidence": 0.8,
                "data": {
                    "title": "meeting",
                    "new_date": "2024-01-22",
                    "new_start_time": "10:00",
                    "new_end_time": "11:00"
                }
            })
        elif "delete" in prompt_lower or "cancel" in prompt_lower:
            return json.dumps({
                "intent_type": "delete_event",
                "confidence": 0.85,
                "data": {
                    "title": "meeting",
                    "date": "2024-01-20"
                }
            })

        return self.default_response

    async def is_available(self) -> bool:
        """Mock client is always available."""
        return True


def get_llm_client() -> BaseLLMClient:
    """Factory function to get the appropriate LLM client based on settings."""
    settings = get_agent_settings()

    if settings.agent_enable_gemini and settings.gemini_api_key:
        return GeminiClient()

    # Default to Ollama
    return OllamaClient()
