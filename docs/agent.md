# Agent Module Documentation

The agent module provides LLM-based natural language understanding for scheduling requests.

## Overview

The agent parses user text into structured intents that the backend can execute:

```
User: "Schedule a meeting with John tomorrow at 2pm for 1 hour"
  ↓
Agent parses to:
  {
    "type": "create_event",
    "title": "Meeting with John",
    "date": "2024-01-21",
    "time": "14:00",
    "duration_minutes": 60
  }
  ↓
Backend creates event
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent Module                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │   Parser    │───▶│ LLM Client  │───▶│ Ollama/Gemini   │  │
│  │             │◀───│             │◀───│                 │  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │  Executor   │───▶│   Prolog    │───▶│  Validation     │  │
│  │             │◀───│   Client    │◀───│                 │  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Intent Parser (`parser.py`)

Converts user text to structured intent using LLM.

```python
from app.agent import IntentParser

parser = IntentParser()
result = await parser.parse("Schedule lunch with Alice tomorrow at noon")

# Result:
# {
#   "type": "create_event",
#   "title": "Lunch with Alice",
#   "date": "2024-01-21",
#   "time": "12:00",
#   "duration_minutes": 60,
#   "confidence": 0.95
# }
```

### 2. LLM Clients (`llm_clients.py`)

Supports multiple LLM providers:

- **Ollama** (default): Local LLM, no API key needed
- **Gemini**: Google AI, requires API key

```python
from app.agent.llm_clients import create_llm_client

# Uses AGENT_LLM_PROVIDER env var
client = create_llm_client()
response = await client.generate("Parse this: schedule meeting tomorrow")
```

### 3. Intent Executor (`executor.py`)

Executes parsed intents by calling the appropriate backend services.

```python
from app.agent import IntentExecutor

executor = IntentExecutor(db_session, prolog_client)
result = await executor.execute(parsed_intent, user_id="user-123")
```

### 4. Prompts (`prompts/`)

System prompts for the LLM:

- `intent_parser.py`: Prompt for parsing user text to structured intent

## Supported Intents

### `create_event`

Create a new calendar event.

**Input:**
```json
{
  "type": "create_event",
  "title": "Team standup",
  "date": "2024-01-20",
  "time": "09:00",
  "duration_minutes": 30,
  "calendar_id": "cal-001"
}
```

**Triggers:**
- "Schedule a meeting..."
- "Create an event..."
- "Book a room for..."

### `find_free_slots`

Find available time slots.

**Input:**
```json
{
  "type": "find_free_slots",
  "date_range_start": "2024-01-20",
  "date_range_end": "2024-01-26",
  "duration_minutes": 60,
  "calendar_id": "cal-001"
}
```

**Triggers:**
- "When am I free..."
- "Find available slots..."
- "What times work for..."

### `move_event`

Reschedule an existing event.

**Input:**
```json
{
  "type": "move_event",
  "event_id": "evt-001",
  "new_date": "2024-01-22",
  "new_time": "15:00"
}
```

**Triggers:**
- "Move my meeting to..."
- "Reschedule the standup to..."
- "Change the time of..."

### `delete_event`

Cancel an event.

**Input:**
```json
{
  "type": "delete_event",
  "event_id": "evt-001"
}
```

**Triggers:**
- "Cancel my meeting..."
- "Delete the event..."
- "Remove the appointment..."

### `query_schedule`

Ask about existing schedule.

**Input:**
```json
{
  "type": "query_schedule",
  "query_type": "day",
  "date": "2024-01-20",
  "calendar_id": "cal-001"
}
```

**Triggers:**
- "What's on my calendar..."
- "Do I have any meetings..."
- "Show my schedule for..."

## API Endpoints

### POST `/api/v1/agent/parse`

Parse user text to intent without executing.

**Request:**
```json
{
  "text": "Schedule a meeting tomorrow at 2pm",
  "user_id": "user-123",
  "calendar_id": "cal-001"
}
```

**Response:**
```json
{
  "success": true,
  "intent": {
    "type": "create_event",
    "title": "Meeting",
    "date": "2024-01-21",
    "time": "14:00",
    "duration_minutes": 60
  },
  "confidence": 0.92,
  "missing_fields": []
}
```

### POST `/api/v1/agent/execute`

Parse and execute an intent.

**Request:**
```json
{
  "text": "Schedule a meeting tomorrow at 2pm",
  "user_id": "user-123",
  "calendar_id": "cal-001"
}
```

**Response:**
```json
{
  "success": true,
  "action_taken": "created_event",
  "result": {
    "event_id": "evt-new-123",
    "title": "Meeting",
    "start_time": "2024-01-21T14:00:00"
  }
}
```

### POST `/api/v1/agent/clarify`

Handle ambiguous intents that need clarification.

**Request:**
```json
{
  "text": "Schedule a meeting",
  "user_id": "user-123",
  "partial_intent": {
    "type": "create_event",
    "title": "Meeting"
  }
}
```

**Response:**
```json
{
  "needs_clarification": true,
  "missing_fields": ["date", "time"],
  "suggested_questions": [
    "What date would you like to schedule the meeting?",
    "What time works for you?"
  ]
}
```

## Configuration

Set these environment variables:

```bash
# LLM Provider
AGENT_LLM_PROVIDER=ollama  # or "gemini"

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Gemini (cloud)
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-1.5-flash
```

## Error Handling

The agent handles errors gracefully:

| Error | Response |
|-------|----------|
| LLM unavailable | Falls back to keyword matching |
| Unparseable text | Returns `needs_clarification: true` |
| Missing fields | Lists required fields |
| Conflict detected | Suggests alternative times |

## Prolog Integration

The agent uses Prolog for:

1. **Conflict detection** before creating events
2. **Finding free slots** with complex constraints
3. **Validating working hours**

See [docs/prolog.md](./prolog.md) for details.

## Testing

```bash
# Run agent tests
cd apps/backend
pytest tests/agent/ -v

# Test intent parsing
pytest tests/agent/test_parser.py -v

# Test with specific LLM
AGENT_LLM_PROVIDER=ollama pytest tests/agent/ -v
```

## Adding New Intents

1. Define the intent schema in `schemas.py`:

```python
class NewIntent(BaseModel):
    type: Literal["new_intent"] = "new_intent"
    field1: str
    field2: int
```

2. Update the union type:

```python
IntentData = Union[..., NewIntent]
```

3. Update the parser prompt in `prompts/intent_parser.py`

4. Add executor logic in `executor.py`:

```python
async def _execute_new_intent(self, intent: NewIntent) -> dict:
    # Implementation
    pass
```

5. Add tests in `tests/agent/test_new_intent.py`
