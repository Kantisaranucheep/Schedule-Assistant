# Chat Feature Implementation Documentation

## Overview

This document describes the implementation of the **Chat Feature with Conflict Resolution** - a standalone conversational interface for managing calendar events with intelligent scheduling conflict detection and resolution.

**Version**: 1.0
**Status**: Full Stack Implementation Complete
**Date**: 2024-01-20

---

## Table of Contents

1. [Architecture](#architecture)
2. [Backend Implementation](#backend-implementation)
3. [Prolog Engine](#prolog-engine)
4. [Frontend Implementation](#frontend-implementation)
5. [API Endpoints](#api-endpoints)
6. [State Flow & Examples](#state-flow--examples)
7. [User Workflow](#user-workflow)
8. [Deployment & Testing](#deployment--testing)
9. [Future Enhancements](#future-enhancements)

---

## Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React/TypeScript)              │
│  ChatModalV2 Component with Interactive UI                  │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTP REST API
                  ↓
┌─────────────────────────────────────────────────────────────┐
│           FastAPI Backend (/agent/chat-v2/*)               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Chat Router - Request/Response Handler              │     │
│  └────────────────────────────────────────────────────┘     │
│           ↓ Route to Handler                                │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Chat Executor - Execute Intent with State Mgmt    │     │
│  └────────────────────────────────────────────────────┘     │
│    ↓                          ↓                              │
│  ┌──────────────────┐  ┌────────────────────┐               │
│  │ Event Service    │  │ Prolog Client      │               │
│  │ (DB Operations)  │  │ (Constraint Logic) │               │
│  └────────┬─────────┘  └────────┬───────────┘               │
└───────────┼──────────────────────┼─────────────────────────┘
            ↓                      ↓
┌─────────────────────────────────────────────────────────────┐
│              Prolog Engine (SWI-Prolog)                     │
│  - Conflict Detection                                       │
│  - Alternative Time Finding                                │
│  - Constraint Satisfaction                                 │
└─────────────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────┐
│         PostgreSQL Database                                 │
│  - Events, Tasks, Categories                               │
│  - Chat Sessions & Messages (persisted on /stop)          │
└─────────────────────────────────────────────────────────────┘
```

### State Machine

The chat feature uses a **7-state conversation model**:

```
INITIAL
  ↓ (User asks to add/edit/remove/list events)
CHECK_CONFLICT (if conflict detected)
  ├─ Yes → STRATEGY_CHOICE
  └─ No → CANCELLED
STRATEGY_CHOICE
  ├─ 1: Find Slot → PREFERENCE_SELECT
  └─ 2: Move Event → PREFERENCE_SELECT
PREFERENCE_SELECT
  ├─ 1: Same time, diff day → query Prolog
  ├─ 2: Specific day → ask user for day
  ├─ 3: Specific time → ask user for time
  └─ 4: Any time → query Prolog
SELECTING_OPTION
  ├─ 1-3: Select option → CONFIRMING
  └─ 4: More options → repeat with offset
CONFIRMING
  ├─ Yes → Execute changes → COMPLETED
  └─ No → CANCELLED
COMPLETED/CANCELLED
  └─ Session ready for next action or close
```

---

## Backend Implementation

### 1. Chat State Manager (`chat_state_manager.py`)

**Purpose**: Maintain in-memory conversation state and session management

**Key Classes**:

- `ConversationStateEnum`: 7 conversation states
- `ChatConversationState`: Holds session data (id, user_id, calendar_id, current_state, messages, intent_data, etc.)
- `ChatStateManager`: Singleton managing all active sessions

**Features**:
- 30-minute auto-cleanup on inactivity
- Message history tracking in memory
- State transitions with validation
- Lazy loading and cleanup

**Usage**:
```python
state_manager = get_chat_state_manager()
session = state_manager.create_session(session_id, user_id, calendar_id)
session.add_message("user", "Add event tomorrow")
state_manager.update_state(session_id, ConversationStateEnum.CHECK_CONFLICT)
```

### 2. Chat Intent Parser (`chat_intent_parser.py`)

**Purpose**: Parse user input with state-aware context

**Key Features**:

- **State-specific system prompts** - Each conversation state has a tailored system prompt
- **Dynamic prompt switching** - Guides LLM to understand user intent in context
- **Helper methods** for quick parsing:
  - `parse_affirmative()` - Detect yes/no
  - `parse_numbered_option()` - Extract number 1-N
  - `parse_with_state()` - Full parsing with context

**System Prompts by State**:

| State | Purpose | LLM Focus |
|-------|---------|-----------|
| INITIAL | Natural conversation | "Help user schedule events" |
| CHECK_CONFLICT | Yes/no detection | "Detect affirmative/negative words" |
| STRATEGY_CHOICE | Binary selection | "User choosing 1 or 2" |
| PREFERENCE_SELECT | 4-option selection | "User choosing 1-4 preference" |
| SELECTING_OPTION | List selection | "User picking from numbered list" |
| CONFIRMING | Confirmation | "User confirming or canceling" |

**Usage**:
```python
parser = get_chat_intent_parser()
result = await parser.parse_with_state(
    text="I want meeting tomorrow",
    current_state=ConversationStateEnum.INITIAL,
    current_date="2024-01-20",
    timezone="Asia/Bangkok"
)
```

### 3. Chat Executor (`chat_executor.py`)

**Purpose**: Execute chat intents and manage state transitions

**Key Methods**:

- `_handle_initial_state()` - Route initial user input
- `_handle_conflict_response()` - Process yes/no to help
- `_handle_strategy_choice()` - Route to find/move strategy
- `_handle_preference_select()` - Handle preference selection
- `_handle_option_select()` - Handle option selection
- `_handle_confirmation()` - Execute or cancel changes

**Core Intent Handlers** (called from INITIAL state):

- `_execute_add_event_chat()` - Add new event with conflict detection
- `_execute_edit_event_chat()` - Edit existing event
- `_execute_remove_event_chat()` - Remove event
- `_execute_update_daily()` - List events (day/week/month format)

**Prolog Queries**:

- `_query_prolog_alternatives()` - Find alternative time slots
- `_query_prolog_alternatives_for_day()` - Find slots on specific day

**Usage**:
```python
executor = ChatExecutor(db)
result = await executor.execute(
    session_id=uuid.uuid4(),
    user_id=uuid.uuid4(),
    calendar_id=uuid.uuid4(),
    current_state=ConversationStateEnum.INITIAL,
    user_message="I need a customer meeting 9-13 tomorrow"
)
# Returns: {"text": "...", "state": "...", "buttons": [...], "table": ...}
```

### 4. Chat Router v2 (`chat_v2.py`)

**Endpoints**:

```
POST   /agent/chat-v2/start
  Start new chat session

POST   /agent/chat-v2/send
  Send message (main interaction endpoint)
  - Input: session_id, user_id, calendar_id, message, timezone
  - Output: reply, state, buttons, table, error

POST   /agent/chat-v2/stop
  Stop chat and persist to database
  - Saves all in-memory messages to ChatSession/ChatMessage

GET    /agent/chat-v2/status/{session_id}
  Get current session status and state

GET    /agent/chat-v2/health
  Health check
```

**Response Format**:
```json
{
  "reply": "Agent response text",
  "state": "current_state",
  "buttons": [
    {"label": "Yes, help me", "value": "yes"},
    {"label": "No, thanks", "value": "no"}
  ],
  "table": {
    "headers": ["Name", "Start", "End"],
    "rows": [["Meeting", "09:00", "10:00"]]
  },
  "error": null
}
```

### 5. Schema Updates (`schemas.py`)

**New Intent Types**:
```python
ADD_EVENT_CHAT = "add_event_chat"
EDIT_EVENT_CHAT = "edit_event_chat"
REMOVE_EVENT_CHAT = "remove_event_chat"
UPDATE_DAILY_CHAT = "update_daily_chat"
RESPOND_AFFIRMATIVE = "respond_affirmative"
RESPOND_NEGATIVE = "respond_negative"
SELECT_PREFERENCE = "select_preference"
SELECT_OPTION = "select_option"
CONFIRM_CHANGES = "confirm_changes"
```

**New Data Models**:
```python
AddEventChatData(title, date, start_time, end_time, location?, description?)
EditEventChatData(event_id?, original_title?, new_title?, new_date?, ...)
RemoveEventChatData(event_id?, title?, date?)
UpdateDailyChatData(date_range: "today|this week|this month", specific_date?)
RespondAffirmativeData(response)
RespondNegativeData(response)
SelectPreferenceData(selected_preference: 1-4)
SelectOptionData(selected_option: int)
ConfirmChangesData(confirmed: bool)
```

---

## Prolog Engine

### Overview

**File**: `apps/prolog/rules_chat.pl`

The Prolog engine handles all constraint satisfaction logic using **First Order Logic (FOL)** with **Resolution**.

### Key Predicates

#### 1. Conflict Detection

```prolog
% Check if two time slots overlap
overlap(StartA, EndA, StartB, EndB) :-
    StartA < EndB,
    EndA > StartB.

% Find all conflicts for a proposed event
check_conflict(CalendarId, ProposedStart, ProposedEnd, ConflictIds) :-
    findall(EventId,
        (event(EventId, CalendarId, _, Start, End),
         overlap(ProposedStart, ProposedEnd, Start, End)),
        ConflictIds).
```

#### 2. Alternative Time Finding (Preference-Based)

**Preference 1: Same time, different day**
```prolog
find_alternatives_same_time(Event, CalendarId, NumDays, AlternativeDays) :-
    findall(date(Day),
        (day_in_range(Day, 1, 60),
         is_time_available_on_day(CalendarId, Day, Start, End)),
        AllDays),
    take_n(min(NumDays, AllDays), AllDays, AlternativeDays).
```

**Preference 2: Specific day**
```prolog
find_alternatives_specific_day(Event, CalendarId, Date, NumSlots, Slots) :-
    findall(slot(Start, End),
        (time_slot(Hour, Start, End),
         is_time_available_on_day(CalendarId, Date, Start, End)),
        AllSlots),
    take_n(min(NumSlots, AllSlots), AllSlots, Slots).
```

**Preference 3: Specific date & time (validation only)**
```prolog
validate_specific_datetime(CalendarId, Date, Start, End, IsValid) :-
    (is_time_available_on_day(CalendarId, Date, Start, End),
     within_working_hours(Start, End, 9, 18))
    -> IsValid = true
    ;  IsValid = false.
```

**Preference 4: Any available time**
```prolog
find_alternatives_any_time(Event, CalendarId, NumSlots, Slots) :-
    findall(slot(StartDT, EndDT),
        (between(0, 180, DayOffset),
         between(9, 17, Hour),
         date_offset_future(DayOffset, Date),
         is_time_available_on_day(CalendarId, Date, Start, End)),
        AllSlots),
    take_n(min(NumSlots, AllSlots), AllSlots, Slots).
```

#### 3. Main Routing

```prolog
suggest_alternative(EventId, CalendarId, PreferenceType, Start, End, Count, Result) :-
    (PreferenceType = 1 -> find_alternatives_same_time(...)
    ; PreferenceType = 2 -> Result = preference_requires_user_input
    ; PreferenceType = 3 -> Result = preference_requires_user_input
    ; PreferenceType = 4 -> find_alternatives_any_time(...)
    ; Result = error_invalid_preference).
```

### First Order Logic & Resolution

**FOL Concepts Used**:

1. **Predicates**: `overlap/4`, `check_conflict/4`, `within_working_hours/3`
2. **Quantifiers**: `findall/3` (∃ existential), universal rules
3. **Unification**: Pattern matching for pattern (Event1, CalendarId, Title, Start, End)
4. **Resolution**: Backtracking and proof search through rules
5. **Constraint Solving**: No-overlap constraint via `is_time_available_on_day/4`

**Example Resolution**:
```
find_alternatives_same_time(e1, cal1, 3, Result)
  ↓ (unify with rule)
findall(date(Day), (day_in_range(Day, 1, 60),
                     is_time_available_on_day(cal1, Day, 9:00, 10:00)), AllDays)
  ↓ (collect all days where time slot is free)
Result = [date(Mon), date(Tue), date(Wed)]
```

---

## Frontend Implementation

### Components

#### ChatModalV2 (`ChatModalV2.tsx`)

**Features**:
- Responsive modal dialog
- Message display with role-based styling
- Interactive buttons (populate input, user reviews, then sends)
- Table display for daily updates (day/week/month)
- Typing indicator with animation
- Session management (start/stop with DB persistence)
- Auto-scroll to latest message

**Props**:
```typescript
interface ChatModalV2Props {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  calendarId: string;
}
```

**State**:
```typescript
- messages: ChatMessage[]
- chatInput: string
- isTyping: boolean
- sessionId: string | null
- currentState: string
- loading: boolean
```

**Lifecycle**:
1. User opens modal → Call `/agent/chat-v2/start` → Get session_id
2. User types message → Click Send or click Button
3. Button click → Populate input field → User reviews → Presses Enter
4. Message sent → `/agent/chat-v2/send` → Update state & display response
5. Response contains buttons/table → Render interactively
6. User closes → `/agent/chat-v2/stop` → Save to DB → Close modal

#### Styling (`ChatModalV2.module.css`)

- **Backdrop**: Full-screen overlay with semi-transparent background
- **Modal**: Centered container with flexbox layout
- **Messages**: Role-based styling (user=blue right, agent=gray left)
- **Buttons**: Interactive action buttons with hover effects
- **Table**: Responsive table with hover rows
- **Input**: Text input with focus styling
- **Responsive**: Mobile-friendly with adjusted sizes

### Integration (`page.tsx`)

- Import: `import ChatModalV2 from "./components/Modals/ChatModal/ChatModalV2"`
- State: `const [chatV2Open, setChatV2Open] = useState(false)`
- Render: `<ChatModalV2 isOpen={chatV2Open} onClose={() => setChatV2Open(false)} ... />`

### Types (`types.ts`)

```typescript
interface ChatButtonV2 {
  label: string;
  value: string;
}

interface ChatTableV2 {
  headers: string[];
  rows: (string | number)[][];
}

interface ChatMessageV2 {
  id: string;
  role: "user" | "agent";
  text: string;
  timestamp: number;
  buttons?: ChatButtonV2[];
  table?: ChatTableV2;
}

interface ChatSessionV2 {
  id: string;
  title: string;
  messages: ChatMessageV2[];
  currentState: string;
  createdAt: string;
}
```

---

## API Endpoints

### POST /agent/chat-v2/start
**Start new chat session**

Request:
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "calendar_id": "00000000-0000-0000-0000-000000000001",
  "title": "Chat 2024-01-20 14:30"
}
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Hi! I'm your calendar assistant...",
  "state": "initial"
}
```

### POST /agent/chat-v2/send
**Send message in chat**

Request:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "calendar_id": "00000000-0000-0000-0000-000000000001",
  "message": "I need a customer meeting 9-13 tomorrow",
  "timezone": "Asia/Bangkok"
}
```

Response:
```json
{
  "reply": "I found a conflict with 'Have lunch' (8:30-10:00). Would you like me to help reschedule?",
  "state": "check_conflict",
  "buttons": [
    {"label": "Yes, help me", "value": "yes"},
    {"label": "No, thanks", "value": "no"}
  ],
  "table": null,
  "error": null
}
```

### POST /agent/chat-v2/stop
**Stop chat and persist to database**

Request:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Conversation saved. Thank you!",
  "message_count": 12
}
```

### GET /agent/chat-v2/status/{session_id}
**Get current session status**

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_state": "selecting_option",
  "message_count": 8,
  "last_message": "Here are available days:",
  "last_message_role": "agent",
  "created_at": "2024-01-20T14:30:00Z",
  "last_activity": "2024-01-20T14:35:00Z"
}
```

---

## State Flow & Examples

### Example 1: Add Event with Conflict Resolution

```
User: "I need a customer meeting 9-13 tomorrow"
  ↓
State: INITIAL
Parser: ADD_EVENT_CHAT intent
Executor: Check conflicts with Prolog
  Conflict found: "Have lunch" 8:30-10:00
  ↓
State: CHECK_CONFLICT
Agent: "I found a conflict with 'Have lunch' (8:30-10:00). Would you like me to help reschedule?"
Buttons: [Yes, No]

User: (clicks "Yes, help me")
  ↓
State: STRATEGY_CHOICE
Agent: "I can help! Would you like me to:\n1) Find a different time for your new event\n2) Move the conflicting event"
Buttons: [Find a slot, Move event]

User: (clicks "Find a slot")
  ↓
State: PREFERENCE_SELECT
Agent: "What's your preference?\n1) Same time on different day\n2) Specific day\n3) Specific date & time\n4) Any available time"
Buttons: [1, 2, 3, 4]

User: (clicks "1 - Same time on different day")
  ↓
Query Prolog: find_alternatives_same_time(event, cal, 3, Result)
State: SELECTING_OPTION
Agent: "Here are available days:\n1. Monday 9:00-13:00\n2. Tuesday 9:00-13:00\n3. Wednesday 9:00-13:00\n4. More options"
Buttons: [1, 2, 3, 4]

User: (clicks "1 - Monday")
  ↓
State: CONFIRMING
Agent: "Confirm these changes:\n❌ Cancel: 'Have lunch' (8:30-10:00 tomorrow)\n✅ Create: 'Customer meeting' Monday 9:00-13:00"
Buttons: [Confirm, Cancel]

User: (clicks "Confirm")
  ↓
Execute: Delete "Have lunch" event, Create "Customer meeting" event
State: COMPLETED
Agent: "✅ Done! Your events have been updated."

User: (clicks "Stop & Save")
  ↓
POST /agent/chat-v2/stop
Save conversation to ChatSession + ChatMessage tables
Close modal
```

### Example 2: Update Daily (List Events)

```
User: "Show me my events for today"
  ↓
State: INITIAL
Parser: UPDATE_DAILY_CHAT intent
Executor: Query events for today
  ↓
State: INITIAL (unchanged)
Agent: Displays table with events
Table:
| Name                | Start  | End    |
|---------------------|--------|--------|
| Morning Standup      | 09:00  | 09:30  |
| Client Call         | 10:00  | 11:00  |
| Lunch               | 12:00  | 13:00  |
| Project Review      | 14:00  | 15:30  |
```

---

## User Workflow

### First-Time Chat Usage

1. **Open Chat**: Click chat button in sidebar or use keyboard shortcut
2. **Start Session**: `/start` endpoint initializes session
3. **Natural Request**: "I need to schedule X", "Show my events", etc.
4. **Conversational Flow**: Follow state machine prompts with interactive buttons
5. **Confirm Changes**: Review and approve modifications
6. **Save & Close**: Click "Stop & Save" to persist conversation

### Chat Features

- **Add Events**: "Add meeting tomorrow 2-3pm"
- **Edit Events**: "Change lunch time to 12:30"
- **Remove Events**: "Delete the team sync on Friday"
- **List Events**: "Show my events for this week"
- **Conflict Resolution**: Automatic detection & guided resolution

### Button Interaction

- **Click Button**: Populates input field
- **Review**: User can edit or confirm
- **Send**: Click Send or press Enter
- **Smart Options**: "More options" (option 4) for additional choices

---

## Deployment & Testing

### Setup

1. **Environment**:
   - Ollama running locally (Docker container)
   - Model: gemme:3.2b or llama3.2
   - PostgreSQL database
   - SWI-Prolog installed

2. **Backend Start**:
   ```bash
   cd apps/backend
   poetry install
   poetry run uvicorn app.main:app --reload
   ```

3. **Frontend Start**:
   ```bash
   cd apps/frontend/frontend
   npm install
   npm run dev
   ```

### Testing Scenarios

**Scenario 1: Successful Addition**
- User adds event without conflicts
- Verify: Event created, COMPLETED state, DB persistence

**Scenario 2: Conflict Resolution**
- User adds event with conflict
- Resolve via different strategies (find slot, move event)
- Verify: Both events updated correctly

**Scenario 3: Daily Update**
- List events for today/week/month
- Verify: Table displays correctly, sorted by time

**Scenario 4: Session Timeout**
- Chat inactive for 30+ minutes
- Verify: Session auto-deleted from memory
- Verify: Can start new chat session

**Scenario 5: Stop & Persist**
- Start chat, send messages, click Stop
- Verify: All messages saved to ChatSession + ChatMessage
- Verify: Can query saved chat history

### Debug Commands

```bash
# Check Ollama connection
curl http://localhost:11434/api/tags

# Check Prolog rules loaded
swipl -f apps/prolog/rules_chat.pl -t "api_check_conflicts('cal1', '09:00', '10:00', R), write(R), nl, halt."

# View active chat sessions
# (In backend, query ChatStateManager._sessions)

# Monitor logs
tail -f docker-compose.log | grep schedule-assistant-api
```

---

## Future Enhancements

### Phase 2 (Next Iteration)

1. **Recurring Events**
   - Support "every Monday" patterns
   - Handle recurrence exceptions

2. **Smart Suggestions**
   - ML-based optimal time prediction
   - Calendar patterns analysis

3. **Multi-Event Operations**
   - "Move all meetings to afternoon"
   - "Block 2 hours for deep work"

4. **Integration**
   - Google Calendar sync
   - Slack notifications
   - Email confirmations

5. **Advanced Preferences**
   - Time zone handling
   - Travel time buffer
   - Focus time blocks

### Phase 3 (Optimization)

1. **Performance**
   - Cache Prolog query results
   - Optimize Ollama inference
   - Stream responses to frontend

2. **UX Improvements**
   - Voice input/output
   - Natural language clarifications
   - Undo/redo functionality

3. **Analytics**
   - Chat conversation metrics
   - Scheduling patterns
   - Time management insights

---

## Troubleshooting

### Issue: LLM not responding

**Solution**:
- Check Ollama container: `docker ps | grep ollama`
- Pull model: `ollama pull gemme:3.2b`
- Verify endpoint: `curl http://ollama:11434/api/tags`

### Issue: Prolog query fails

**Solution**:
- Validate Prolog syntax: `swipl --syntax-check rules_chat.pl`
- Check subprocess mode: `which swipl`
- Enable debug mode in executor

### Issue: Session timeout too aggressive

**Solution**:
- Adjust `_timeout_minutes` in ChatStateManager
- Implement heartbeat pings from frontend

### Issue: Buttons not populating input

**Solution**:
- Verify onClick handlers bound correctly
- Check input ref focus: `inputRef.current?.focus()`
- Debug button value extraction

---

## Files Summary

### Backend
- `apps/backend/app/agent/chat_state_manager.py` (230 lines)
- `apps/backend/app/agent/chat_intent_parser.py` (180 lines)
- `apps/backend/app/agent/chat_executor.py` (620 lines)
- `apps/backend/app/routers/chat_v2.py` (250 lines)
- `apps/backend/app/agent/schemas.py` (10 new IntentTypes + 9 data models)

### Prolog
- `apps/prolog/rules_chat.pl` (260 lines)

### Frontend
- `apps/frontend/frontend/app/components/Modals/ChatModal/ChatModalV2.tsx` (280 lines)
- `apps/frontend/frontend/app/components/Modals/ChatModal/ChatModalV2.module.css` (240 lines)
- `apps/frontend/frontend/app/page.tsx` (~5 lines modified)
- `apps/frontend/frontend/app/types.ts` (~30 lines added)

### Modified Files
- `apps/backend/app/main.py` (2 lines: import + include router)
- `apps/backend/app/routers/__init__.py` (1 line: import + export)

**Total**: ~2,500 lines of code

---

## Contact & Support

For questions or issues:
1. Check troubleshooting section
2. Enable debug logging
3. Review API response format
4. Check browser console for frontend errors
5. Review Prolog query logs

---

**Document Version**: 1.0
**Last Updated**: 2024-01-20
**Implementation Status**: ✅ Complete - Ready for Testing
