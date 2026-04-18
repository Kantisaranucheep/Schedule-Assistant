# Chapter 5: Techniques and Algorithms Used for the System Development

## Overview

The Schedule Assistant employs a combination of artificial intelligence, search algorithms, logic programming, and modern software engineering techniques to deliver an intelligent calendar management system. This chapter describes the key techniques and algorithms used across the system.

---

## 1. A\* Search Algorithm for Schedule Optimization

### 1.1 Problem Definition

When a user adds a new event that conflicts with existing events, the system must find an optimal rescheduling plan that minimizes disruption while respecting both hard and soft constraints. This is modeled as a **state-space search problem** where each state represents a possible arrangement of events on the user's calendar.

### 1.2 State Representation

Each state in the search space is defined by:

- **Events list**: The set of all events with their current time placements (represented as minutes from midnight).
- **Moves list**: The sequence of event moves taken to reach this state from the initial configuration.
- **Cost scores**:
  - `g(n)` — the cumulative displacement cost (how far events have been moved from their original times).
  - `h(n)` — the priority loss heuristic (estimated cost of remaining conflicts).
  - `f(n) = g(n) + h(n)` — the total evaluation score used by A\* to select the next state to explore.

```
@dataclass(order=True)
class ScheduleState:
    f_score: float
    events: List[ScheduleEvent]
    moves: List[MoveAction]
    g_cost: float
    h_cost: float
```

A state key, derived from the sorted `(event_id, start_minutes)` tuples, is used for deduplication to prevent revisiting equivalent configurations.

### 1.3 Cost Functions

**Displacement Cost — g(n)**

For each moved event, the displacement cost is calculated as:

```
g(n) = Σ [ base_penalty(3) + hours_shifted × 2.0 + priority × 0.5 ]
```

This penalizes moving events far from their original times and makes moving high-priority events more expensive.

**Priority Loss Heuristic — h(n)**

For each remaining conflict pair, the heuristic cost uses a quadratic penalty on the higher-priority event involved:

```
h(n) = Σ [ max_priority² × strategy_weight ]
```

The quadratic scaling ensures that conflicts involving high-priority events (e.g., exams, deadlines) are far more costly than conflicts involving low-priority events, guiding the search to resolve critical conflicts first.

**Strategy Weights**

The system supports three scheduling strategies that modulate the cost function:

| Strategy          | g(n) Weight | h(n) Weight | Description                              |
|-------------------|-------------|-------------|------------------------------------------|
| `minimize_moves`  | 0.7         | 0.5         | Fewest events rescheduled                |
| `maximize_quality`| 1.8 (high-pri) / 0.5 (low-pri) | 2.0 | Protect high-priority events |
| `balanced`        | 1.0         | 1.0         | Weighted combination (default)           |

### 1.4 Search Process

The A\* optimizer (`ScheduleOptimizer`) performs the following steps:

1. **Conflict Detection**: Identify all pairwise overlaps between the new event and existing events.
2. **Option Generation**: Generate up to three candidate solutions:
   - **Option A (Move New)**: Find the best free slot for the new event, leaving existing events untouched.
   - **Option B (Move Existing)**: Keep the new event in place and relocate conflicting events, processing lowest-priority events first.
   - **Option C (A\* Search)**: Explore multi-move solutions using the A\* algorithm with a priority queue (`heapq`), bounded by a maximum of 200 iterations and a search depth of 5 moves.
3. **State Expansion**: For each conflict, try moving each involved (non-fixed) event to the best available free slot. Compute new `g`, `h`, and `f` scores. Push the resulting state onto the open list if not already visited.
4. **Goal Check**: A state with zero conflicts is the goal. The search terminates when the goal is found or the iteration limit is reached.
5. **Recommendation**: The three options are sorted by total cost, and the lowest-cost feasible option is recommended to the user.

### 1.5 Hard and Soft Constraints

**Hard Constraints** (must be satisfied — violations make a solution infeasible):

- No time overlap between events.
- Events must fall within scheduling bounds (default 06:00–23:00).
- Event duration must be positive.
- Fixed events (exams, deadlines) cannot be moved.

**Soft Constraints** (preferences — violations incur penalty costs):

- **Preferred Time Windows**: Each event type has a preferred time range (e.g., meetings prefer 09:00–17:00, exercise prefers 06:00–08:00). Events scheduled outside their preferred window incur a penalty proportional to the distance.
- **Buffer Time**: Events with less than 15 minutes of gap between them incur a proximity penalty of 3 per neighbor.
- **Priority Scheduling**: High-priority events (priority ≥ 8) scheduled outside peak hours (09:00–17:00) incur an additional penalty of `(priority − 7) × 3`.

---

## 2. Natural Language Processing via LLM Intent Parsing

### 2.1 Architecture

The system uses a **prompt-engineered Large Language Model (LLM)** pipeline to convert natural language scheduling requests into structured, executable intents. The pipeline consists of three stages:

```
User Text → [Intent Parser + LLM] → Structured JSON Intent → [Intent Executor] → Action
```

### 2.2 Intent Classification

The LLM receives a system prompt containing a strict JSON schema and few-shot examples. It classifies user input into one of the following intent types:

| Intent Type        | Description                          | Example Trigger                                  |
|--------------------|--------------------------------------|--------------------------------------------------|
| `create_event`     | Create a new calendar event          | "Schedule a meeting with John tomorrow at 2pm"   |
| `find_free_slots`  | Find available time slots            | "When am I free next week?"                      |
| `move_event`       | Reschedule an existing event         | "Move my dentist appointment to Friday"          |
| `delete_event`     | Cancel/remove an event               | "Cancel my meeting tomorrow"                     |

Each parsed intent includes:
- `intent_type`: The classified action.
- `confidence`: A float score (0.0–1.0) indicating the LLM's certainty.
- `data`: Intent-specific structured fields (title, date, time, etc.).
- `clarification_question`: A follow-up question if required fields are ambiguous or missing.

### 2.3 JSON Extraction with Fallback

The parser employs a **multi-stage JSON extraction** strategy to handle LLM output variability:

1. **Direct Parse**: Attempt `json.loads()` on the raw response.
2. **Markdown Code Block Extraction**: Regex-match `` ```json ... ``` `` blocks.
3. **Embedded JSON Object Detection**: Regex-scan for `{ ... }` patterns within free-form text.

This ensures robustness even when the LLM wraps its output in commentary or formatting.

### 2.4 Schema Validation

Extracted JSON is validated against **Pydantic models** (`Intent`, `CreateEventData`, `FindFreeSlotsData`, etc.) which enforce:
- Field presence and types (e.g., date in `YYYY-MM-DD` format, time in `HH:MM` format).
- Value ranges (e.g., `duration_minutes` between 15 and 480).
- Confidence thresholds — intents below 0.7 confidence trigger clarification prompts.

### 2.5 LLM Provider Abstraction

The system abstracts LLM communication behind a `BaseLLMClient` interface with concrete implementations for:
- **Ollama** (local LLM, default): Runs models like `llama3.2` locally via Docker, using low temperature (0.1) for consistent JSON output.
- **Google Gemini** (cloud API): For higher-accuracy parsing when available.
- **MockLLMClient**: Keyword-matching fallback for testing and when LLM services are unavailable.

---

## 3. LLM-Based Priority Extraction from User Persona

### 3.1 Technique

The system uses a **persona-driven priority extraction** technique where the user provides a natural language description of themselves (their "story"), and the LLM infers event-type priority weights on a 1–10 scale.

For example, a user who says *"I'm a final year computer science student preparing for my thesis defense and job interviews"* would receive high priorities for `exam` (10), `deadline` (10), and `interview` (10), but lower priorities for `social` (3) and `party` (2).

### 3.2 Process

1. The user's story is sent to the LLM with a system prompt defining 18 event types and the expected JSON output schema.
2. The LLM returns a JSON object with:
   - `priorities`: A mapping of event type → weight (1–10).
   - `persona_summary`: A brief characterization of the user.
   - `reasoning`: An explanation of how the priorities were derived.
   - `recommended_strategy`: One of `minimize_moves`, `maximize_quality`, or `balanced`.
3. Priorities are **normalized and clamped** to the valid range `[1, 10]`, with a default of 5 for unrecognized or invalid entries.
4. Extracted priorities are persisted in the `UserProfile` model and are used by the A\* scheduling optimizer to weight conflict resolution decisions.

---

## 4. Prolog-Based Constraint Logic Programming

### 4.1 Why Prolog

The system integrates **SWI-Prolog** for declarative constraint-based scheduling logic. Prolog's strengths for this domain include:

- **Declarative Rules**: Scheduling constraints are expressed as logical rules ("what" must hold) rather than imperative procedures ("how" to check).
- **Backtracking Search**: Prolog's built-in backtracking automatically explores alternative solutions when conflicts arise.
- **Pattern Matching**: Complex event structures are matched naturally using Prolog unification.

### 4.2 Knowledge Base (kb.pl)

The knowledge base stores **dynamic facts** representing the scheduling domain:

```prolog
%% event(Id, CalendarId, Title, StartTime, EndTime, Status, CreatedBy)
:- dynamic event/7.

%% working_hours(UserId, StartTime, EndTime)
:- dynamic working_hours/3.

%% buffer_minutes(UserId, Minutes)
:- dynamic buffer_minutes/2.
```

Facts can be asserted and retracted at runtime, enabling the Prolog knowledge base to stay synchronized with the PostgreSQL database.

### 4.3 Scheduling Rules (rules.pl)

**Overlap Detection**:

Two events overlap if the start of one falls before the end of the other and vice versa. The rule filters out cancelled events:

```prolog
events_overlap(event(_, _, _, Start1, End1, Status1, _),
               event(_, _, _, Start2, End2, Status2, _)) :-
    Status1 \= cancelled,
    Status2 \= cancelled,
    Start1 @< End2,
    End1 @> Start2.
```

**Conflict Query using `findall/3`**:

The `check_overlap/4` predicate collects all event IDs that conflict with a proposed time range using Prolog's `findall/3` meta-predicate:

```prolog
check_overlap(CalendarId, ProposedStart, ProposedEnd, ConflictIds) :-
    findall(Id,
        (event(Id, CalendarId, _, Start, End, Status, _),
         Status \= cancelled,
         ProposedStart @< End,
         ProposedEnd @> Start),
        ConflictIds).
```

**Working Hours Validation**:

The system validates that events fall within the user's configured working hours, with a default of 09:00–18:00 if no custom hours are set:

```prolog
is_within_working_hours(UserId, StartTime, EndTime) :-
    working_hours(UserId, WorkStart, WorkEnd),
    extract_time(StartTime, StartHM),
    extract_time(EndTime, EndHM),
    StartHM @>= WorkStart,
    EndHM @=< WorkEnd.
```

**Event Validation**:

The `validate_event_time/5` predicate chains multiple checks, returning an `ok`, `overlap(Conflicts)`, or `outside_hours` result:

```prolog
validate_event_time(CalendarId, UserId, Start, End, Result) :-
    (   check_overlap(CalendarId, Start, End, Conflicts),
        Conflicts \= []
    ->  Result = overlap(Conflicts)
    ;   ( \+ is_within_working_hours(UserId, Start, End)
        ->  Result = outside_hours
        ;   Result = ok
        )
    ).
```

### 4.4 Python–Prolog Integration

The `PrologClient` bridges the Python backend with SWI-Prolog through two modes:

- **Subprocess Mode** (default): Spawns a `swipl` process for each query. Simple deployment but higher latency due to process startup.
- **Service Mode**: Connects to a persistent SWI-Prolog HTTP server for lower-latency, production-grade queries.

The integration follows the flow: **Agent Executor → PrologClient → SWI-Prolog → Constraint Validation Result**.

---

## 5. Free Slot Finding Algorithm (Greedy Scan)

### 5.1 Approach

The `AvailabilityService` uses a **greedy linear scan** algorithm to find available time slots within a date range:

1. For each day in the requested range, define the working hours window (e.g., 09:00–18:00).
2. Retrieve all events for that day and sort them by start time.
3. Scan from the start of working hours: for each gap between consecutive events (or between working hours and the first/last event), check if the gap duration meets the minimum required.
4. Collect all qualifying gaps as free slots.

### 5.2 Complexity

Given `n` events on a single day, the algorithm runs in **O(n log n)** due to sorting, followed by an **O(n)** linear scan — making it efficient for typical daily event counts.

---

## 6. Notification Scheduling (Periodic Job Scheduling)

### 6.1 Technique

The `NotificationScheduler` uses **APScheduler** (Advanced Python Scheduler) with an `AsyncIOScheduler` to periodically check for upcoming events and trigger email notifications.

### 6.2 Process

1. A periodic job runs at a configurable interval (e.g., every 60 seconds).
2. For each user with notifications enabled, the scheduler queries events within a look-ahead window defined by the user's notification preferences (e.g., 15 minutes before, 1 hour before).
3. For each event-notification pair, the scheduler calculates the target notification time (`event_start − minutes_before`) and checks if the current time falls within a ±1-minute window.
4. A **deduplication set** (`_sent_notifications`) keyed by `"{event_id}_{minutes_before}"` prevents duplicate notifications.

---

## 7. Real-Time Communication via WebSocket

### 7.1 Technique

The system uses **WebSocket** connections (via FastAPI's WebSocket support) to enable real-time push updates from the server to the frontend. This is used for:

- Notifying the client of schedule changes made by collaborators.
- Pushing real-time event updates without requiring client-side polling.

A `ConnectionManager` maintains active WebSocket connections keyed by `user_id`, allowing targeted message delivery.

---

## 8. RESTful API Design with Async I/O

### 8.1 Technique

The backend is built using **FastAPI** with full **asynchronous I/O** support:

- All database operations use **SQLAlchemy's AsyncSession** with the `asyncpg` PostgreSQL driver, enabling non-blocking database queries.
- HTTP calls to external LLM services (Ollama, Gemini) use the **httpx** async HTTP client.
- Prolog subprocess calls use `asyncio.create_subprocess_exec` for non-blocking process management.

This architecture allows the server to handle many concurrent requests efficiently without thread-blocking.

### 8.2 Database Migrations

Schema evolution is managed using **Alembic**, which provides:

- Auto-generated migration scripts from SQLAlchemy model changes.
- Version-controlled, reversible database migrations.
- Support for both upgrade and downgrade operations.

---

## 9. Containerization with Docker Compose

The system uses **Docker Compose** for multi-service orchestration:

| Service    | Image/Build         | Purpose                                   |
|------------|---------------------|-------------------------------------------|
| `postgres` | `postgres:16-alpine`| Relational database (PostgreSQL)          |
| `backend`  | Custom Dockerfile   | FastAPI backend API                       |
| `ollama`   | `ollama/ollama`     | Local LLM inference server (GPU-enabled)  |

Service health checks, volume persistence, and inter-service networking are configured declaratively, ensuring reproducible deployments.

---

## Summary Table

| Technique / Algorithm           | Purpose                                           | Location in Codebase                  |
|---------------------------------|---------------------------------------------------|---------------------------------------|
| A\* Search Algorithm            | Optimal schedule rescheduling with constraints     | `services/scheduling_service.py`      |
| LLM Intent Parsing (NLP)       | Natural language → structured scheduling commands  | `agent/parser.py`, `agent/llm_clients.py` |
| LLM Priority Extraction        | Persona → event-type priority weights              | `services/priority_extractor.py`      |
| Prolog Constraint Logic         | Declarative overlap detection & validation         | `apps/prolog/rules.pl`, `apps/prolog/kb.pl` |
| Greedy Free Slot Scan           | Find available time slots in a date range          | `services/availability_service.py`    |
| Periodic Job Scheduling         | Time-based event notifications                     | `services/notification_scheduler.py`  |
| WebSocket Real-Time Push        | Live schedule update notifications                 | `routers/ws.py`                       |
| Async I/O (FastAPI + asyncpg)   | Non-blocking concurrent request handling           | Entire backend                        |
| Docker Compose Orchestration    | Multi-service containerized deployment             | `docker/docker-compose.yml`           |
