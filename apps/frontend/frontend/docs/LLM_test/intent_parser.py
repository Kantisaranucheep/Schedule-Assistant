"""
Extracts structured JSON intent from LLM responses.
"""

import json
import re


def extract_json(response_text: str) -> dict | None:
    """
    Scan the LLM response for a ```json ... ``` fenced code block.
    Returns the parsed dict if found, otherwise None.
    """
    # Match ```json ... ``` blocks (with optional whitespace)
    pattern = r"```json\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, response_text, re.DOTALL)

    if not match:
        return None

    json_str = match.group(1).strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def strip_json_block(response_text: str) -> str:
    """
    Remove the ```json ... ``` block from the response text,
    returning only the conversational part for display / TTS.
    """
    pattern = r"```json\s*\n?.*?\n?\s*```"
    cleaned = re.sub(pattern, "", response_text, flags=re.DOTALL)
    return cleaned.strip()
