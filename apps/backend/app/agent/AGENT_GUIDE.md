# Agent-Backend Integration Guide

This guide explains how the AI Agent connects to the backend and how to implement new features.

---

## 🎯 Overview: How Agent Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER                                            │
│                     "Schedule a meeting tomorrow at 2pm"                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         1. ROUTER (agent.py)                                 │
│                     POST /agent/parse-and-execute                            │
│                     - Receives user text                                     │
│                     - Coordinates parsing and execution                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         2. PARSER (parser.py)                                │
│                     - Calls LLM with user text                               │
│                     - LLM returns structured JSON                            │
│                     - Validates JSON → Intent object                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         3. INTENT (schemas.py)                               │
│                     {                                                        │
│                       "intent_type": "create_event",                         │
│                       "confidence": 0.95,                                    │
│                       "data": {                                              │
│                         "title": "Meeting",                                  │
│                         "date": "2026-02-12",                                │
│                         "start_time": "14:00",                               │
│                         "end_time": "15:00"                                  │
│                       }                                                      │
│                     }                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         4. EXECUTOR (executor.py)                            │
│                     - Routes intent to correct handler                       │
│                     - _execute_create_event()                                │
│                     - _execute_find_free_slots()                             │
│                     - _execute_move_event()                                  │
│                     - _execute_delete_event()                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐     ┌─────────────────────────────┐
│   5a. PROLOG (Optional)     │     │   5b. SERVICES/DATABASE     │
│   - Constraint validation   │     │   - Create event in DB      │
│   - Check conflicts         │     │   - Query availability      │
│   - Logic-based rules       │     │   - Update/delete events    │
└─────────────────────────────┘     └─────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         6. RESPONSE                                          │
│                     {                                                        │
│                       "success": true,                                       │
│                       "message": "Event 'Meeting' created for Feb 12",       │
│                       "result": { ... }                                      │
│                     }                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Key Files and Their Purpose

| File | Purpose | When to modify |
|------|---------|----------------|
| `routers/agent.py` | API endpoints for agent | Add new endpoints |
| `agent/schemas.py` | Data models (Intent, Request, Response) | Add new intent types or fields |
| `agent/parser.py` | Converts text → Intent via LLM | Change parsing logic |
| `agent/executor.py` | Executes Intent → Action | **Main file** to add business logic |
| `agent/llm_clients.py` | LLM API wrappers (Ollama, Gemini) | Add new LLM providers |
| `agent/prompts/intent_parser.py` | LLM prompts | Modify how LLM interprets text |
| `integrations/prolog_client.py` | Prolog integration | Modify constraint checking |

---

## 🔧 How to Add New Functionality

### Example: Connect `create_event` to actually save in database

Currently, `_execute_create_event()` in `executor.py` returns a stub response.
To make it actually create events, modify the function:

```python
# In executor.py

async def _execute_create_event(
    self,
    intent: Intent,
    request: ExecuteRequest,
) -> ExecuteResponse:
    """Execute create_event intent."""
    
    # 1. Parse the intent data
    data = CreateEventData(**intent.data)
    
    # 2. Convert to datetime
    start_dt = datetime.strptime(f"{data.date} {data.start_time}", "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(f"{data.date} {data.end_time}", "%Y-%m-%d %H:%M")
    
    # 3. Check for conflicts (via Prolog or service)
    conflicts = await check_event_conflicts(
        db=self.db,
        calendar_id=request.calendar_id,
        start_at=start_dt,
        end_at=end_dt,
    )
    
    if conflicts:
        return ExecuteResponse(
            success=False,
            error="Time conflict with existing events",
            result={"conflicting_events": [str(e.id) for e in conflicts]}
        )
    
    # 4. Create the event in database
    from app.models.event import Event
    
    event = Event(
        calendar_id=request.calendar_id,
        title=data.title,
        description=data.description,
        location=data.location,
        start_at=start_dt,
        end_at=end_dt,
        status="confirmed",
        created_by="agent",  # Mark as created by agent
    )
    
    self.db.add(event)
    await self.db.flush()
    
    # 5. Return success response
    return ExecuteResponse(
        success=True,
        result={
            "event_id": str(event.id),
            "title": event.title,
            "start_at": event.start_at.isoformat(),
            "end_at": event.end_at.isoformat(),
        },
        message=f"Created event '{event.title}' on {data.date} from {data.start_time} to {data.end_time}",
    )
```

---

## 🧪 Testing the Agent

### 1. Test with curl

```bash
# Parse only (no execution)
curl -X POST http://localhost:8000/agent/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Schedule a team meeting tomorrow at 2pm for 1 hour"}'

# Parse and execute (dry run)
curl -X POST "http://localhost:8000/agent/parse-and-execute?text=Schedule%20meeting%20tomorrow%20at%202pm&user_id=348baf59-3495-4ea9-8874-3b1033d1bf58&calendar_id=f292fa89-94a5-4b98-94b4-c4581be000ff&dry_run=true"
```

### 2. Test with Swagger UI
Open http://localhost:8000/docs and use the interactive API.

### 3. Test with Python
```python
import httpx
import asyncio

async def test_agent():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/agent/parse",
            json={"text": "Find me a free 30-minute slot tomorrow"}
        )
        print(response.json())

asyncio.run(test_agent())
```

---

## 📝 Adding a New Intent Type

### Step 1: Add to IntentType enum (schemas.py)
```python
class IntentType(str, Enum):
    CREATE_EVENT = "create_event"
    FIND_FREE_SLOTS = "find_free_slots"
    MOVE_EVENT = "move_event"
    DELETE_EVENT = "delete_event"
    LIST_EVENTS = "list_events"  # NEW!
    UNKNOWN = "unknown"
```

### Step 2: Add data model (schemas.py)
```python
class ListEventsData(BaseModel):
    """Data for list_events intent."""
    date: str = Field(..., description="Date to list events (YYYY-MM-DD)")
    include_cancelled: bool = Field(False, description="Include cancelled events")
```

### Step 3: Add to SUPPORTED_INTENTS (executor.py)
```python
SUPPORTED_INTENTS = [
    IntentType.CREATE_EVENT,
    IntentType.FIND_FREE_SLOTS,
    IntentType.MOVE_EVENT,
    IntentType.DELETE_EVENT,
    IntentType.LIST_EVENTS,  # NEW!
]
```

### Step 4: Add handler in executor.py
```python
# In handler_map
handler_map = {
    IntentType.CREATE_EVENT: self._execute_create_event,
    IntentType.FIND_FREE_SLOTS: self._execute_find_free_slots,
    IntentType.MOVE_EVENT: self._execute_move_event,
    IntentType.DELETE_EVENT: self._execute_delete_event,
    IntentType.LIST_EVENTS: self._execute_list_events,  # NEW!
}

# Add new method
async def _execute_list_events(
    self,
    intent: Intent,
    request: ExecuteRequest,
) -> ExecuteResponse:
    """Execute list_events intent."""
    data = ListEventsData(**intent.data)
    
    # Query database for events
    from sqlalchemy import select
    from app.models.event import Event
    
    target_date = datetime.strptime(data.date, "%Y-%m-%d").date()
    
    query = select(Event).where(
        Event.calendar_id == request.calendar_id,
        Event.start_at >= target_date,
        Event.start_at < target_date + timedelta(days=1),
    )
    
    if not data.include_cancelled:
        query = query.where(Event.status != "cancelled")
    
    result = await self.db.execute(query)
    events = result.scalars().all()
    
    return ExecuteResponse(
        success=True,
        result={
            "date": data.date,
            "event_count": len(events),
            "events": [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "start": e.start_at.strftime("%H:%M"),
                    "end": e.end_at.strftime("%H:%M"),
                }
                for e in events
            ]
        },
        message=f"Found {len(events)} events on {data.date}",
    )
```

### Step 5: Update LLM prompt (prompts/intent_parser.py)
Add the new intent type description so LLM knows when to use it.

---

## 🔑 Key Concepts

### 1. Intent
A structured representation of what the user wants to do.

### 2. Parser
Uses LLM to convert natural language → Intent JSON.

### 3. Executor
Routes Intent to appropriate handler and performs the action.

### 4. Services
Reusable business logic (availability, conflicts) that can be used by both:
- REST API (routers)
- Agent (executor)

### 5. Prolog
Optional logic engine for complex constraint checking.

---

## ❓ Common Questions

**Q: Why use LLM for parsing?**
A: LLM can understand natural language variations like "tomorrow", "next Monday", "in 2 hours" and convert them to structured dates/times.

**Q: Why is executor separate from parser?**
A: Separation of concerns. Parser only understands text. Executor only performs actions. This makes testing and maintenance easier.

**Q: When should I use Prolog vs Python services?**
A: 
- Use **Python services** for simple CRUD and database queries
- Use **Prolog** for complex logical reasoning and constraint satisfaction

**Q: How do I test without LLM?**
A: Create a mock LLM client or call the `/agent/execute` endpoint directly with a pre-built Intent JSON.
