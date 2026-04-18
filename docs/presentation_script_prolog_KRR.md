# Presentation Script: Prolog & KRR in Schedule Assistant

> **How to use this script**: Each section = one slide or talking point. Read the **"Say:"** parts aloud. The code/diagrams are what you show on screen.

---

## SLIDE 1: Introduction — What is KRR and Why Prolog?

**Say:**

"Our Schedule Assistant uses **Knowledge Representation and Reasoning (KRR)** to handle scheduling logic. KRR is about two things:

1. **Knowledge Representation** — How do we store facts about the world? (events, calendars, working hours)
2. **Reasoning** — How do we derive new conclusions from those facts? (conflict detection, finding free slots, rescheduling)

We chose **Prolog** (specifically SWI-Prolog) because:

- It's **declarative** — we write *what* the rules are, not *how* to check them step by step
- It has **built-in backtracking** — it automatically tries different possibilities
- It uses **unification and pattern matching** — perfect for matching event structures
- It's a natural fit for **First-Order Logic** — the foundation of KRR"

---

## SLIDE 2: The Big Picture — How Prolog Fits Into Our System

**Show this architecture diagram:**

```
┌──────────────────────────────────────────────────────┐
│              Python Backend (FastAPI)                  │
│                                                        │
│  User says: "Schedule meeting at 2pm tomorrow"         │
│       │                                                │
│       ▼                                                │
│  ┌──────────┐     ┌──────────────────┐                │
│  │  LLM     │     │  PrologService   │                │
│  │  Parser   │────▶│  (prolog_service │                │
│  └──────────┘     │    .py)          │                │
│                    └───────┬──────────┘                │
│                            │ calls via pyswip          │
│                            ▼                           │
│                    ┌──────────────────┐                │
│                    │   SWI-Prolog     │                │
│                    │  ┌────────────┐  │                │
│                    │  │ scheduler  │  │                │
│                    │  │   .pl      │  │                │
│                    │  ├────────────┤  │                │
│                    │  │ constraint │  │                │
│                    │  │ _solver.pl │  │                │
│                    │  └────────────┘  │                │
│                    └──────────────────┘                │
│                            │                           │
│                            ▼                           │
│                   Result: ok / overlap / outside_hours  │
│                            │                           │
│                            ▼                           │
│                 ┌─────────────────────┐               │
│                 │  A* Schedule        │               │
│                 │  Optimizer (Python) │               │
│                 │  if conflicts exist │               │
│                 └─────────────────────┘               │
└──────────────────────────────────────────────────────┘
```

**Say:**

"Here's the flow: The user speaks in natural language → LLM parses it into a structured intent → `PrologService` sends queries to SWI-Prolog → Prolog checks constraints using logical rules → If conflicts exist, the A* optimizer (which also uses Prolog's heuristic calculations) finds the best rescheduling."

---

## SLIDE 3: The 5 Prolog Files You Need to Know

**Say:**

"There are 5 key Prolog-related files. Let me explain what each one does:"

| # | File | Location | What It Does |
|---|------|----------|--------------|
| 1 | **`kb.pl`** | `apps/prolog/` | **Knowledge Base** — stores facts (events, calendars, working hours) |
| 2 | **`rules.pl`** | `apps/prolog/` | **Rules** — overlap detection, working hours validation, free slot finding |
| 3 | **`main.pl`** | `apps/prolog/` | **Entry Point** — loads kb + rules, provides API predicates for the backend |
| 4 | **`scheduler.pl`** | `apps/backend/app/chat/prolog/` | **Advanced Scheduler** — time-to-minutes conversion, conflict detection with `findall`, free slot CSP |
| 5 | **`constraint_solver.pl`** | `apps/backend/app/chat/prolog/` | **A\* Rescheduling** — hard/soft constraints, g(n)/h(n) heuristic, 3 reschedule strategies |

And 2 Python files that **bridge** Python ↔ Prolog:

| # | File | What It Does |
|---|------|--------------|
| 6 | **`prolog_client.py`** | Spawns `swipl` subprocess or calls HTTP service to run Prolog queries |
| 7 | **`prolog_service.py`** | High-level service — calls Prolog for conflicts, free slots, rescheduling; has Python fallbacks |

---

## SLIDE 4: Knowledge Representation — How We Store Facts (kb.pl)

**Say:**

"In KRR, **knowledge representation** is about encoding real-world information into a formal structure that a reasoner can process. In Prolog, we use **facts** — statements that are unconditionally true."

**Show this code:**

```prolog
%% An event fact has 7 fields:
%% event(Id, CalendarId, Title, StartTime, EndTime, Status, CreatedBy)

event('evt-001', 'cal-001', 'Team Meeting',
      '2024-01-20T10:00:00', '2024-01-20T11:00:00',
      confirmed, user).

%% Working hours for a user
working_hours('user-001', '09:00', '18:00').

%% Buffer time between events
buffer_minutes('user-001', 10).
```

**Say:**

"Each event is a **fact** with 7 arguments. Think of it like a row in a database — but instead of SQL, Prolog can *reason* over these facts using logical rules.

These facts are **dynamic** — we can add (`assertz`) or remove (`retract`) them at runtime. This lets us keep the Prolog knowledge base in sync with our PostgreSQL database."

**Key KRR concepts here:**
- **Facts** = ground atoms (no variables) — they represent what we know
- **Dynamic predicates** = the knowledge base can change over time
- **Closed-world assumption** = if a fact isn't in the KB, it's false

---

## SLIDE 5: Reasoning — Overlap Detection Rules (rules.pl + scheduler.pl)

**Say:**

"Now let's look at **reasoning** — how Prolog derives new knowledge from facts. The most important rule is **overlap detection**."

**Show this:**

```
Two events overlap if:   Start1 < End2  AND  Start2 < End1

Timeline example:
  Event A:  |----10:00=======11:00----|
  Event B:       |----10:30======11:30----|
                        ↑ OVERLAP ↑
```

**In Prolog (rules.pl):**

```prolog
events_overlap(event(_, _, _, Start1, End1, Status1, _),
               event(_, _, _, Start2, End2, Status2, _)) :-
    Status1 \= cancelled,    %% ignore cancelled events
    Status2 \= cancelled,
    Start1 @< End2,          %% Start1 is before End2
    End1 @> Start2.          %% End1 is after Start2
```

**In scheduler.pl (uses minutes for easier math):**

```prolog
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.
```

**Say:**

"This is **First-Order Logic Resolution** in action. In formal logic:

`overlap(A, B) ≡ ¬(Start_A ≥ End_B ∨ Start_B ≥ End_A)`

Which simplifies to: `Start_A < End_B ∧ Start_B < End_A`

Prolog checks this condition directly. The `@<` operator does string comparison (for ISO dates), while `<` does numeric comparison (for minutes)."

---

## SLIDE 6: Finding Conflicts with `findall/3` — A Core Prolog Meta-Predicate

**Say:**

"When we need to find *all* events that conflict with a proposed time, we use `findall/3` — one of Prolog's most powerful predicates."

**Show:**

```prolog
check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents, Conflicts) :-
    time_to_minutes(NewStartH, NewStartM, NewStart),
    time_to_minutes(NewEndH, NewEndM, NewEnd),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),          %% Template: what to collect
        (
            member(event(ID, Title, SH, SM, EH, EM), ExistingEvents),  %% For each event
            time_to_minutes(SH, SM, ExStart),
            time_to_minutes(EH, EM, ExEnd),
            events_overlap(NewStart, NewEnd, ExStart, ExEnd)           %% that overlaps
        ),
        Conflicts                                       %% Collect into this list
    ).
```

**Say:**

"Let me break down `findall(Template, Goal, Results)`:
- **Template**: what shape of data to collect (here: `conflict(ID, Title, ...)`)
- **Goal**: the condition to check (here: for each event in the list, does it overlap?)
- **Results**: the list of all matches

This is equivalent to a `SELECT` in SQL but with logical inference. The `member/2` predicate iterates through the list (like existential quantification ∃), and Prolog's backtracking automatically tries every event."

---

## SLIDE 7: Working Hours Validation — Rules with Default Fallback

**Say:**

"Another example of reasoning: checking if an event falls within the user's working hours."

**Show:**

```prolog
%% Rule 1: If user has custom working hours, use those
is_within_working_hours(UserId, StartTime, EndTime) :-
    working_hours(UserId, WorkStart, WorkEnd),   %% Look up from KB
    extract_time(StartTime, StartHM),
    extract_time(EndTime, EndHM),
    StartHM @>= WorkStart,
    EndHM @=< WorkEnd.

%% Rule 2: If no custom hours exist, default to 09:00–18:00
is_within_working_hours(UserId, StartTime, EndTime) :-
    \+ working_hours(UserId, _, _),              %% No fact in KB
    extract_time(StartTime, StartHM),
    extract_time(EndTime, EndHM),
    StartHM @>= '09:00',
    EndHM @=< '18:00'.
```

**Say:**

"Notice the two clauses for the same predicate. Prolog tries Rule 1 first. If the user has working hours in the KB, it uses them. If not (`\+` means 'not provable'), it falls back to Rule 2 with defaults.

This is **Negation as Failure** — `\+ working_hours(UserId, _, _)` means 'we cannot prove that working hours exist for this user', so we assume they don't."

---

## SLIDE 8: The Complete Validation Flow — validate_event_time

**Say:**

"Now let's see how all the rules chain together into one validation:"

**Show:**

```prolog
validate_event_time(CalendarId, UserId, Start, End, Result) :-
    (   check_overlap(CalendarId, Start, End, Conflicts),
        Conflicts \= []                           %% Step 1: Any overlaps?
    ->  Result = overlap(Conflicts)               %%   YES → return conflicts
    ;   ( \+ is_within_working_hours(UserId, Start, End)
        ->  Result = outside_hours                %% Step 2: Outside hours?
        ;   Result = ok                           %% Step 3: All good!
        )
    ).
```

**Flow diagram:**

```
validate_event_time(calendar, user, start, end, ?)
        │
        ▼
   check_overlap → found conflicts?
        │                    │
       YES                  NO
        │                    │
        ▼                    ▼
  Result = overlap    is_within_working_hours?
                            │           │
                           YES         NO
                            │           │
                            ▼           ▼
                      Result = ok   Result = outside_hours
```

**Say:**

"This is the main predicate that Python calls. It chains: overlap check → working hours check → return ok. The `->` operator is Prolog's if-then-else. This is a classic example of **rule chaining** in KRR."

---

## SLIDE 9: Constraint Satisfaction Problem — Finding Free Slots (scheduler.pl)

**Say:**

"Finding free time slots is modeled as a **Constraint Satisfaction Problem (CSP)**."

**Show the formal definition:**

```
CSP Definition:
  Variables:  SlotStart, SlotEnd
  Domain:     0–1440 (minutes in a day, where 0 = midnight, 540 = 9:00 AM)
  Constraints:
    C1: SlotEnd - SlotStart = Duration          (correct length)
    C2: ∀e ∈ Events: ¬overlaps(Slot, e)         (no conflicts)
    C3: SlotStart ≥ MinStart                     (within bounds)
    C4: SlotEnd ≤ MaxEnd                         (within bounds)
```

**In Prolog:**

```prolog
find_free_slots(Duration, Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeSlots) :-
    time_to_minutes(MinStartH, MinStartM, MinStart),
    time_to_minutes(MaxEndH, MaxEndM, MaxEnd),
    Step = 30,     %% 30-minute granularity
    generate_candidate_slots(MinStart, MaxEnd, Duration, Step, CandidateStarts),
    findall(
        slot(SH, SM, EH, EM),
        (
            member(SlotStart, CandidateStarts),        %% Try each candidate
            SlotEnd is SlotStart + Duration,
            SlotEnd =< MaxEnd,                          %% C4: within bounds
            slot_is_free(SlotStart, SlotEnd, Events),   %% C2: no conflicts
            minutes_to_time(SlotStart, SH, SM),
            minutes_to_time(SlotEnd, EH, EM)
        ),
        FreeSlots
    ).
```

**Say:**

"The approach is:
1. **Generate** candidate time slots (every 30 minutes)
2. **Test** each candidate against ALL constraints
3. **Collect** only the ones that pass

Prolog's backtracking does the work — for each candidate, if `slot_is_free` fails (there's a conflict), Prolog automatically backtracks and tries the next candidate. This is the essence of **constraint solving**."

---

## SLIDE 10: Hard vs. Soft Constraints (constraint_solver.pl)

**Say:**

"Now we get to the advanced part — **Phase 2** of our system. We distinguish between **hard constraints** (must be satisfied) and **soft constraints** (nice to have, with penalty costs)."

**Show:**

```
┌─────────────────────────────────────────────────────────┐
│  HARD CONSTRAINTS (Violations = infeasible solution)     │
├─────────────────────────────────────────────────────────┤
│  1. No time overlap between events                       │
│  2. Events within bounds (06:00 – 23:00)                 │
│  3. End time > Start time (positive duration)            │
│  4. Fixed events (exams, deadlines) cannot move          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  SOFT CONSTRAINTS (Violations = penalty cost added)      │
├─────────────────────────────────────────────────────────┤
│  1. Preferred time windows:                              │
│     - Meetings prefer 09:00–17:00                        │
│     - Study prefers 08:00–12:00 or 14:00–18:00           │
│     - Exercise prefers before 08:00 or after 17:00       │
│  2. Buffer time: < 15 min gap → penalty of 3 per event  │
│  3. Daily overload: > 6 events → penalty per extra       │
│  4. High priority at peak hours: priority ≥ 8 outside    │
│     09:00–17:00 → penalty = (priority − 7) × 3          │
└─────────────────────────────────────────────────────────┘
```

**In Prolog (validate_hard_constraints):**

```prolog
validate_hard_constraints(Event, AllEvents, Violations) :-
    findall(Violation, (
        % Check overlap with each other event
        (   member(OtherEvent, AllEvents),
            OtherId \= Id,
            events_overlap(...),
            Violation = overlap(OtherId, OtherTitle)
        )
        ;
        % Check working hours bounds
        (   StartMin < 360,    %% 360 min = 6:00 AM
            Violation = before_working_hours
        )
        ;
        (   EndMin > 1380,     %% 1380 min = 23:00
            Violation = after_working_hours
        )
    ), Violations).
```

**Say:**

"Hard constraints use `findall` to collect ALL violations at once. If the `Violations` list is empty, the schedule is feasible. Otherwise, we must resolve them."

---

## SLIDE 11: The Heuristic — How A* Decides What's Best

**Say:**

"This is the most important part for KRR. Our A* search uses two cost functions:"

**Show:**

```
f(n) = g(n) + h(n)

where:
  g(n) = DISPLACEMENT COST (actual moves made so far)
  h(n) = PRIORITY LOSS HEURISTIC (estimated remaining cost)
```

### g(n) — Displacement Cost

```
For each moved event:
  g(n) += base_penalty(3) + hours_shifted × 2.0 + priority × 0.5

Example:
  Move "Team Meeting" (priority 5) by 2 hours:
  g = 3 + (2 × 2.0) + (5 × 0.5) = 3 + 4 + 2.5 = 9.5
```

**In Prolog:**

```prolog
calculate_displacement_cost(OriginalEvents, ModifiedEvents, GCost) :-
    findall(EventCost, (
        member(event(Id, _, OSH, OSM, ..., Priority, _), OriginalEvents),
        member(event(Id, _, NSH, NSM, ..., _, _), ModifiedEvents),
        Shift is abs(NewStart - OldStart),
        ShiftHours is Shift / 60.0,
        EventCost is 3 + ShiftHours * 2 + Priority * 0.5
    ), Costs),
    sum_list(Costs, GCost).
```

### h(n) — Priority Loss Heuristic

```
For each remaining conflict:
  h(n) += priority² × strategy_weight

Example:
  Conflict involves event with priority 8, using "balanced" strategy:
  h = 8² × 1.0 = 64

  Same conflict with "maximize_quality" strategy:
  h = 8² × 2.0 = 128  (much more urgent to resolve!)
```

**In Prolog:**

```prolog
calculate_priority_loss(ConflictingEvents, Strategy, _, HCost) :-
    strategy_weight(Strategy, StratWeight),
    findall(EventHCost, (
        member(event(_, _, _, _, _, _, Priority, _), ConflictingEvents),
        ConflictSeverity is Priority * Priority,     %% Quadratic penalty!
        EventHCost is ConflictSeverity * StratWeight
    ), HCosts),
    sum_list(HCosts, HCost).
```

**Say:**

"Why **quadratic** penalty? Because a conflict with a priority-10 event (like an exam) should be **100× more costly** than a priority-1 event (like a casual chat). This ensures A* resolves high-priority conflicts first.

The combined heuristic:

```prolog
calculate_heuristic(OriginalEvents, CurrentState, RemainingConflicts, Strategy, FScore) :-
    calculate_displacement_cost(OriginalEvents, CurrentState, GCost),
    calculate_priority_loss(RemainingConflicts, Strategy, [], HCost),
    FScore is GCost + HCost.
```

This is what drives A* — it always expands the state with the **lowest f(n)**."

---

## SLIDE 12: The 3 Reschedule Strategies

**Say:**

"Users can choose one of three strategies. Each strategy changes the **weights** in the cost function, which changes which solution A* finds first."

**Show:**

```
┌─────────────────┬─────────────┬─────────────┬──────────────────────────────┐
│    Strategy      │ g(n) Weight │ h(n) Weight │ Behavior                     │
├─────────────────┼─────────────┼─────────────┼──────────────────────────────┤
│ minimize_moves   │    0.7      │    0.5      │ Move as few events as        │
│                  │ (cheaper to │ (conflicts  │ possible. Prefer moving      │
│                  │  move)      │  less urgent)│ just the new event.         │
├─────────────────┼─────────────┼─────────────┼──────────────────────────────┤
│ maximize_quality │    varies   │    2.0      │ Protect high-priority        │
│                  │ 1.8 (high)  │ (conflicts  │ events at all costs.         │
│                  │ 0.5 (low)   │  very urgent)│ Move low-priority instead.  │
├─────────────────┼─────────────┼─────────────┼──────────────────────────────┤
│ balanced         │    1.0      │    1.0      │ Fair compromise between      │
│                  │ (standard)  │ (standard)  │ fewer moves and quality.     │
└─────────────────┴─────────────┴─────────────┴──────────────────────────────┘
```

**In Prolog:**

```prolog
strategy_weight(minimize_moves, 0.5).
strategy_weight(maximize_quality, 2.0).
strategy_weight(balanced, 1.0).
```

**In Python (_apply_strategy_weight):**

```python
if strategy == "minimize_moves":
    if is_new_event:
        return base_cost * 0.7   # Cheap to move new event
    return base_cost * 1.3       # Expensive to move existing

elif strategy == "maximize_quality":
    priority_factor = priority / 10.0
    if is_new_event:
        return base_cost * (0.3 + priority_factor * 1.7)  # 0.3 to 2.0
    else:
        return base_cost * (0.3 + priority_factor * 2.7)  # 0.3 to 3.0
```

**Say:**

"**Concrete example:** You have a priority-9 exam at 2pm, and you want to add a priority-3 lunch at 2pm.

- **minimize_moves**: Just move lunch somewhere else (cheapest option)
- **maximize_quality**: Definitely protect the exam! Move lunch far away if needed
- **balanced**: Move lunch, but try to keep it close to 2pm

The strategy affects which option A* returns as the best."

---

## SLIDE 13: The Reschedule Flow — How Options Are Generated

**Say:**

"When a user adds an event that conflicts, the system generates up to **3 options**:"

**Show:**

```
User adds: "Lunch 12:00-13:00"
Existing:  "Meeting 12:30-13:30" (priority 7)

System generates:

  Option A (move_new):
    → Move "Lunch" to 11:00-12:00
    → Cost = displacement(1hr × 2) + soft_cost = 2.0
    → "Lunch stays near preferred time"

  Option B (move_new):
    → Move "Lunch" to 13:30-14:30
    → Cost = displacement(1.5hr × 2) + soft_cost = 3.0

  Option C (move_existing):
    → Move "Meeting" to 14:00-15:00
    → Cost = displacement(1.5hr × 2) + priority(7 × 0.3) + soft_cost = 5.1
    → More expensive because Meeting has higher priority!

Sorted by cost: Option A (2.0) → Option B (3.0) → Option C (5.1)
```

**In code (prolog_service.py):**

```python
def suggest_reschedule_options(self, new_event, existing_events, strategy, ...):
    # 1. Find conflicts
    conflicts = [e for e in existing if overlaps(new, e)]

    # 2. Option A: Move NEW event to free slots (sorted by proximity)
    candidates = generate_slots(30_min_step)
    for slot in candidates:
        score = displacement_cost + soft_cost
        options.append(RescheduleOption("move_new", ...))

    # 3. Option B: Move each CONFLICTING event
    for conflict in conflicts:
        best_slot = find_best_slot(conflict, ...)
        score = displacement + soft_cost + priority * 0.3
        options.append(RescheduleOption("move_existing", ...))

    # 4. Sort by cost, return top 3
    return sorted(options, key=cost)[:3]
```

---

## SLIDE 14: A* Search in Prolog — Finding the Optimal Schedule

**Say:**

"For complex cases with multiple conflicts, we use full A* search in Prolog:"

**Show:**

```prolog
astar_search(Open, Closed, Strategy, Bounds, MaxDepth, Solution) :-
    %% 1. Pick the state with lowest f-score
    sort_states_by_cost(Open, [Current|RestOpen]),
    Current = state(Events, OrigEvents, CurrentCost, Moves, Conflicts),

    (   Conflicts = []
    ->  %% 2. GOAL: No conflicts! Return solution
        Solution = solution(Events, CurrentCost, Moves)
    ;
        %% 3. EXPAND: For each conflict, try moving one event
        findall(NextState, (
            member(conflict(Id1, Id2), Conflicts),
            ( MovedId = Id1 ; MovedId = Id2 ),         %% Try moving either
            find_best_slot(MovedEvent, Events, ...),    %% Find new slot
            replace_event_time(Events, MovedId, ...),   %% Apply move
            find_all_conflicts(NewEvents, NewConflicts), %% Check remaining
            NextState = state(NewEvents, OrigEvents, NewCost, ...)
        ), NewStates),

        %% 4. Add new states to open list, recurse
        append(RestOpen, NewStates, AllOpen),
        astar_search(AllOpen, [Current|Closed], Strategy, Bounds, NewDepth, Solution)
    ).
```

**Say:**

"The A* search works like this:
1. Start with current schedule + new event → find all conflicts
2. Pick the state with lowest f(n) = g(n) + h(n)
3. If no conflicts → **done!** Return the solution
4. Otherwise: for each conflict pair, try moving one event → generate new states
5. Add new states to the open list, repeat
6. Max 200 iterations, max depth 5 moves (to prevent infinite search)"

---

## SLIDE 15: Python ↔ Prolog Integration

**Say:**

"How does the Python backend actually talk to Prolog? Through the `PrologService` class."

**Show:**

```python
# prolog_service.py uses pyswip library
from pyswip import Prolog

class PrologService:
    def __init__(self):
        self._prolog = Prolog()
        # Load Prolog files
        self._prolog.consult("scheduler.pl")
        self._prolog.consult("constraint_solver.pl")

    def check_conflict(self, new_start_h, new_start_m, new_end_h, new_end_m, events):
        # Build Prolog query string
        events_str = self._build_events_list(events)
        query = f"check_conflict({new_start_h}, {new_start_m}, ...{events_str}, Conflicts)"

        # Execute query — Prolog returns results
        results = list(self._prolog.query(query))

        # Parse Prolog results into Python objects
        return ConflictResult(conflicts=parsed_results)
```

**Say:**

"There are two integration modes:
1. **pyswip** (in-process): Python directly calls the Prolog engine via a C library binding. Faster, used in production.
2. **Subprocess**: Spawns a `swipl` process for each query. Simpler but slower (used as fallback).

Both have **Python fallback** — if Prolog is unavailable, the same logic runs in pure Python. This ensures the system always works."

---

## SLIDE 16: Complete End-to-End Flow Example

**Say:**

"Let's walk through a complete example from user input to result."

```
User: "Add exam review tomorrow at 2pm for 2 hours"

Step 1: LLM Parser
  → Intent: create_event
  → Data: title="Exam Review", date=tomorrow, time=14:00, duration=120min

Step 2: PrologService.check_conflict()
  Prolog query: check_conflict(14, 0, 16, 0, [existing_events...], Conflicts)
  Prolog KB check: events_overlap(840, 960, 870, 930) → true!
  → Conflict found: "Team Meeting" 14:30–15:30

Step 3: Determine priority
  User persona: "CS student preparing for finals"
  → exam_review priority = 9 (from LLM priority extraction)
  → meeting priority = 6

Step 4: PrologService.suggest_reschedule_options(strategy="balanced")
  Prolog calculates:
    g(move meeting 1hr) = 3 + (1 × 2) + (6 × 0.5) = 8.0
    h(conflict with pri-6) = 6² × 1.0 = 36
    f = 44

  Returns 3 options:
    Option 1: Move "Team Meeting" to 16:00-17:00 (cost: 8.0)
    Option 2: Move "Exam Review" to 16:00-18:00 (cost: 12.5)
    Option 3: Move "Team Meeting" to 10:00-11:00 (cost: 14.2)

Step 5: User picks Option 1 → Calendar updated!
```

---

## SLIDE 17: Summary — KRR Concepts Used

**Show this table:**

| KRR Concept | How We Use It | Where In Code |
|-------------|---------------|---------------|
| **Facts** | Events, calendars, working hours stored as Prolog facts | `kb.pl` |
| **Rules** | If-then logic for overlap detection, validation | `rules.pl` |
| **First-Order Logic** | `∀e ∈ Events: ¬overlaps(new, e)` — universal/existential quantification | `scheduler.pl` |
| **Resolution** | `overlap ≡ S1 < E2 ∧ S2 < E1` — deriving conclusions | `scheduler.pl` |
| **Negation as Failure** | `\+ working_hours(...)` — default reasoning | `rules.pl` |
| **Constraint Satisfaction** | Free slot finding: variables + domains + constraints | `scheduler.pl` |
| **Backtracking** | Prolog tries all candidates automatically | All `.pl` files |
| **Heuristic Search (A\*)** | f(n) = g(n) + h(n) for optimal rescheduling | `constraint_solver.pl` |
| **Meta-predicates** | `findall/3` for collecting query results | All `.pl` files |
| **Dynamic KB** | `assertz`/`retract` for runtime fact management | `kb.pl` |

**Say:**

"To summarize: Our Schedule Assistant uses Prolog for KRR at every level — from storing knowledge as facts, to reasoning about conflicts with first-order logic rules, to finding optimal schedules using A* search with priority-based heuristics. The 3 strategies give users control over how the system resolves conflicts based on their priorities."

---

## Quick Reference: Which File Does What?

```
WHEN USER ADDS AN EVENT:
  1. prolog_service.py → check_conflict() → scheduler.pl (overlap detection)
  2. If conflict → suggest_reschedule_options() → constraint_solver.pl (A* + heuristic)
  3. Return 3 options to user

WHEN USER ASKS "WHEN AM I FREE?":
  1. prolog_service.py → find_free_slots() → scheduler.pl (CSP solving)
  2. Or → find_free_ranges() → scheduler.pl (gap finding)
  3. Return available time slots

WHEN VALIDATING ANY EVENT:
  1. prolog_service.py → rules.pl → validate_event_time()
  2. Checks: overlaps? → working hours? → ok!
```
