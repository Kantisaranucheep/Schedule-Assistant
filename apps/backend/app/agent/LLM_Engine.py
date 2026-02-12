import json
import os
from typing import Any, Dict, Optional

import requests
from datetime import datetime

from app.agent.config import get_agent_settings


class LLM_Engine:
    """Core engine that sends user text to a local Ollama LLM and returns
    a structured intent dict parsed from the model's JSON output.

    Usage:
        engine = LLM_Engine()
        result = engine.parse("Schedule a meeting tomorrow at 3pm", "2024-01-01T12:00:00")
        reply  = engine.generate_reply(result)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        ollama_url: Optional[str] = None,
    ):
        settings = get_agent_settings()
        self.model = model or settings.ollama_model
        self.ollama_url = ollama_url or f"{settings.ollama_base_url}/api/generate"
        
        # Load the template once
        template_path = os.path.join(
            os.path.dirname(__file__), "prompts", "sys_prompt.txt"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            self.sys_prompt_template = f.read()

    def _build_sys_prompt(self, current_time_str: str) -> str:
        """Inject the user's current time context into the prompt template.
        Expects current_time_str in ISO format or similar, will parse to display nicely.
        """
        try:
            # Try to parse ISO format if possible to make it readable
            # e.g., "2024-01-01T12:00:00.000Z"
            # Remove 'Z' if present as fromisoformat only supports it in Python 3.11+
            # For older python, we might need to handle it manually or strip it.
            # Simple approach: take the first 19 chars "YYYY-MM-DDTHH:MM:SS"
            dt_str = current_time_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(dt_str)
            
            date_str = dt.strftime("%Y-%m-%d")
            day_name = dt.strftime("%A")
            time_str = dt.strftime("%H:%M")
        except Exception:
            # Fallback if unknown format
            date_str = current_time_str
            day_name = "Unknown"
            time_str = "Unknown"

        return self.sys_prompt_template.format(
            date_str=date_str,
            day_name=day_name,
            time_str=time_str,
        )

    def parse(self, user_input: str, current_time: str) -> Dict[str, Any]:
        """Send *user_input* to the Ollama model with *current_time* context.
        Returns the parsed JSON intent dictionary.
        """
        # Build prompt with dynamic time
        sys_prompt = self._build_sys_prompt(current_time)
        
        payload = {
            "model": self.model,
            "prompt": f"{sys_prompt}\nUser input: {user_input}\nJSON:",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
            },
        }

        try:
            response = requests.post(self.ollama_url, json=payload)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(
                "Could not connect to Ollama. Is it running?"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        raw_text = response.json().get("response", "")

        try:
            data: Dict[str, Any] = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON.\nRaw output: {raw_text}"
            ) from exc

        return data

    @staticmethod
    def generate_reply(data: Dict[str, Any]) -> str:
        """Produce a human-friendly reply string from a parsed intent dict."""

        intent = data.get("intent")

        if intent == "add_event":
            if data.get("needs_clarification"):
                return "I need a bit more information to schedule that event."
            return f"I have added your {data.get('title')} to your schedule."

        if intent == "remove_event":
            return f"I have removed the event {data.get('title')}."

        if intent == "query_events":
            return "Here are the events you have for that period."

        if intent == "check_free_time":
            if data.get("needs_clarification"):
                return "Please tell me the time range you want to check."
            return "Let me check your availability."

        if intent == "update_event":
            if data.get("needs_clarification"):
                return "I need more details to reschedule your event."
            return f"I have updated the time for {data.get('title')}."

        if intent == "small_talk":
            msg_type = data.get("message_type")
            if msg_type == "greeting":
                return "Hello! How can I help you schedule today?"
            if msg_type == "thanks":
                return "You're welcome!"
            if msg_type == "goodbye":
                return "Goodbye! Have a great day."
            return "How can I help you?"

        if intent == "clarification":
            missing = ", ".join(data.get("missing_fields", []))
            return f"I need more information: {missing}"

        return "I'm not sure how to help with that."