# apps/backend/app/agent/prompts/__init__.py
"""Prompt templates for the agent module."""

from app.agent.prompts.intent_parser import (
    INTENT_PARSER_SYSTEM_PROMPT,
    INTENT_PARSER_USER_TEMPLATE,
    INTENT_SCHEMA_DESCRIPTION,
)

__all__ = [
    "INTENT_PARSER_SYSTEM_PROMPT",
    "INTENT_PARSER_USER_TEMPLATE",
    "INTENT_SCHEMA_DESCRIPTION",
]
