# apps/backend/app/agent/exceptions.py
"""Custom exceptions for the agent module."""

from typing import Any, Dict, List, Optional


class AgentError(Exception):
    """Base exception for agent-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidJSONError(AgentError):
    """Raised when LLM output is not valid JSON."""

    def __init__(self, raw_output: str, parse_error: str):
        super().__init__(
            message="Failed to parse LLM output as JSON",
            details={
                "raw_output": raw_output[:500],  # Truncate for safety
                "parse_error": parse_error,
            },
        )
        self.raw_output = raw_output
        self.parse_error = parse_error


class SchemaValidationError(AgentError):
    """Raised when JSON doesn't match expected schema."""

    def __init__(self, json_data: Dict[str, Any], validation_errors: List[Dict[str, Any]]):
        super().__init__(
            message="JSON does not match Intent schema",
            details={
                "json_data": json_data,
                "validation_errors": validation_errors,
            },
        )
        self.json_data = json_data
        self.validation_errors = validation_errors


class UnsupportedIntentError(AgentError):
    """Raised when intent type is not supported."""

    def __init__(self, intent_type: str, supported_types: List[str]):
        super().__init__(
            message=f"Unsupported intent type: {intent_type}",
            details={
                "intent_type": intent_type,
                "supported_types": supported_types,
            },
        )
        self.intent_type = intent_type
        self.supported_types = supported_types


class LLMConnectionError(AgentError):
    """Raised when LLM service is unavailable."""

    def __init__(self, service: str, error: str):
        super().__init__(
            message=f"Failed to connect to LLM service: {service}",
            details={
                "service": service,
                "error": error,
            },
        )
        self.service = service
        self.error = error


class MissingRequiredFieldsError(AgentError):
    """Raised when intent is missing required fields."""

    def __init__(self, intent_type: str, missing_fields: List[str], clarification: str):
        super().__init__(
            message=f"Intent {intent_type} missing required fields",
            details={
                "intent_type": intent_type,
                "missing_fields": missing_fields,
                "clarification_question": clarification,
            },
        )
        self.intent_type = intent_type
        self.missing_fields = missing_fields
        self.clarification = clarification


class PrologExecutionError(AgentError):
    """Raised when Prolog query execution fails."""

    def __init__(self, query: str, error: str):
        super().__init__(
            message="Prolog execution failed",
            details={
                "query": query,
                "error": error,
            },
        )
        self.query = query
        self.error = error


class ExecutionError(AgentError):
    """Raised when intent execution fails."""

    def __init__(self, intent_type: str, error: str):
        super().__init__(
            message=f"Failed to execute intent: {intent_type}",
            details={
                "intent_type": intent_type,
                "error": error,
            },
        )
        self.intent_type = intent_type
        self.error = error
