# apps/backend/app/agent/parser.py
"""Intent parser - converts user text to structured intent via LLM."""

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import ValidationError

from app.agent.config import get_agent_settings
from app.agent.exceptions import (
    InvalidJSONError,
    SchemaValidationError,
    LLMConnectionError,
)
from app.agent.llm_clients import BaseLLMClient, get_llm_client
from app.agent.prompts.intent_parser import (
    INTENT_PARSER_SYSTEM_PROMPT,
    INTENT_PARSER_USER_TEMPLATE,
    INTENT_SCHEMA_DESCRIPTION,
)
from app.agent.schemas import Intent, IntentType, ParseRequest, ParseResponse


class IntentParser:
    """Parses user text into structured Intent using LLM."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        """Initialize parser with optional custom LLM client.

        Args:
            llm_client: Custom LLM client (defaults to configured client)
        """
        self.llm_client = llm_client or get_llm_client()
        self.settings = get_agent_settings()

    async def parse(
        self,
        request: ParseRequest,
        timezone: str = "Asia/Bangkok",
    ) -> ParseResponse:
        """Parse user text into structured intent.

        Args:
            request: Parse request containing user text
            timezone: User's timezone for date resolution

        Returns:
            ParseResponse with intent or error
        """
        try:
            # Build prompts
            system_prompt = INTENT_PARSER_SYSTEM_PROMPT.format(
                schema_description=INTENT_SCHEMA_DESCRIPTION
            )

            user_prompt = INTENT_PARSER_USER_TEMPLATE.format(
                current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
                timezone=timezone,
                user_text=request.text,
            )

            # Call LLM
            raw_response = await self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            # Extract and parse JSON
            json_data = self._extract_json(raw_response)

            # Validate against schema
            intent = self._validate_intent(json_data, request.text)

            return ParseResponse(
                success=True,
                intent=intent,
            )

        except InvalidJSONError as e:
            return ParseResponse(
                success=False,
                error=e.message,
                error_details=e.details,
            )
        except SchemaValidationError as e:
            return ParseResponse(
                success=False,
                error=e.message,
                error_details=e.details,
            )
        except LLMConnectionError as e:
            return ParseResponse(
                success=False,
                error=e.message,
                error_details=e.details,
            )
        except Exception as e:
            return ParseResponse(
                success=False,
                error=f"Unexpected error: {str(e)}",
                error_details={"exception_type": type(e).__name__},
            )

    def _extract_json(self, raw_response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response.

        Handles cases where LLM might include markdown code blocks
        or extra text around the JSON.

        Args:
            raw_response: Raw LLM output

        Returns:
            Parsed JSON as dictionary

        Raises:
            InvalidJSONError: If no valid JSON found
        """
        # Clean up response
        text = raw_response.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0].strip())
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Nothing worked
        raise InvalidJSONError(
            raw_output=raw_response,
            parse_error="Could not extract valid JSON from LLM response",
        )

    def _validate_intent(self, json_data: Dict[str, Any], raw_text: str) -> Intent:
        """Validate JSON data against Intent schema.

        Args:
            json_data: Parsed JSON data
            raw_text: Original user text for debugging

        Returns:
            Validated Intent object

        Raises:
            SchemaValidationError: If validation fails
        """
        # Add raw_text for debugging
        json_data["raw_text"] = raw_text

        # Ensure required fields have defaults
        if "intent_type" not in json_data:
            json_data["intent_type"] = IntentType.UNKNOWN.value
        if "confidence" not in json_data:
            json_data["confidence"] = 0.5

        try:
            return Intent.model_validate(json_data)
        except ValidationError as e:
            errors = [
                {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
                for err in e.errors()
            ]
            raise SchemaValidationError(json_data=json_data, validation_errors=errors)

    async def check_llm_available(self) -> bool:
        """Check if the configured LLM is available.

        Returns:
            True if LLM is accessible
        """
        return await self.llm_client.is_available()
