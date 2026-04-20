# Schedule Assistant System

# Chapter 5: Techniques and Algorithms Used for System Development

**Technical Design Report — Full Meta-Interpreter Edition**

---

## Overview

The Schedule Assistant employs a combination of artificial intelligence, search algorithms, logic programming, knowledge representation and reasoning (KRR), and modern software engineering techniques to deliver an intelligent calendar management system. This chapter describes the key techniques and algorithms used across the system.

**Key architectural change:** The Prolog reasoning engine has been upgraded from a *restricted/wrapper meta-interpreter* (`call(Goal)` catch-all) to a **full meta-interpreter** (`clause(Goal, Body), demo(Body)`). This means every domain predicate resolution step is now transparent, traceable, and controllable by our code — nothing is hidden inside Prolog's internal resolution.

---

## 1. A* Search Algorithm for Schedule Optimisation

### 1.1 Problem Definition

When a user adds a new event that conflicts with one or more existing events, the system must find an optimal rescheduling plan that minimises disruption to the user's calendar while respecting both hard and soft constraints. This is modelled as a state-space search problem: each state represents a complete arrangement of events on a single day, and transitions correspond to moving one event to a new time slot. The search must balance two competing objectives — resolving all time conflicts and minimising the total cost of the changes applied.

The A* algorithm is chosen because it is both complete (it will always find a solution if one exists) and optimal (it finds the least-cost solution) when the heuristic function is admissible. For calendar rescheduling, this guarantees that the system recommends the solution that causes the least overall disruption to the user's existing schedule.

### 1.2 State Representation

Each state in the search space is a Prolog compound term:

```prolog
state(Events, OrigEvents, CurrentCost, Moves, Conflicts)
```

| Component | Description |
|-----------|-------------|
| Events | The full list of events with their current time placements in this state. Each event is an eight-argument term: `event(Id, Title, StartHour, StartMinute, EndHour, EndMinute, Priority, Type)`. |
| OrigEvents | The original (unmodified) event list as it existed before any rescheduling. Preserved unchanged throughout the search to compute displacement costs. |
| CurrentCost | The accumulated g(n) cost to reach this state from the initial state. |
| Moves | An ordered list of `move(Id, NewSH, NewSM, NewEH, NewEM)` records describing every event move applied so far. |
| Conflicts | A list of `conflict(Id1, Id2)` pairs representing all remaining pairwise overlaps. An empty list means the state is a goal state. |

**State-Key Deduplication:** To prevent the search from revisiting equivalent configurations, each state is mapped to a canonical key derived from the sorted list of (EventId, StartMinutes) tuples. States already in the closed set are never expanded again.

### 1.3 Cost Functions

The A* evaluation function is a composite of two components:

**f(n) = g(n) + h(n)**

In the full meta-interpreter, the heuristic computation is routed through `demo/1` so that every sub-goal (fact lookups, arithmetic, strategy weights) passes through clause-based resolution:

```prolog
solve(heuristic(OrigEvents, CurrState, RemConflicts, Strategy), FScore) :-
    solve(displacement_cost(OrigEvents, CurrState), G),
    solve(priority_loss(RemConflicts, Strategy), H),
    FScore is G + H.
```

#### 1.3.1 Displacement Cost — g(n): Actual Cost of Moves

The displacement cost g(n) measures the real, accumulated cost of all event moves made to reach the current state. For every event whose time differs between the original schedule and the current state, a per-event cost is computed.

In the full meta-interpreter version (`constraint_solve.pl`), `solve(displacement_cost(...), G)` uses `demo(event_displacement_cost(...))` — meaning the `event_displacement_cost/3` rule body is retrieved via `clause/2` and each sub-goal (`time_to_minutes`, `fact(move_penalty, ...)`, arithmetic) is recursively proved by `demo/1`:

```prolog
solve(displacement_cost(OriginalEvents, ModifiedEvents), GCost) :-
    findall(EC, (
        member(OrigEvent, OriginalEvents),
        OrigEvent = event(Id, _, _, _, _, _, _, _),
        member(ModEvent, ModifiedEvents),
        ModEvent = event(Id, _, _, _, _, _, _, _),
        demo(event_displacement_cost(OrigEvent, ModEvent, EC))
    ), Costs),
    sum_list(Costs, GCost).
```

The underlying rule:

```prolog
event_displacement_cost(
    event(Id, _, OSH, OSM, OEH, OEM, Priority, _),
    event(Id, _, NSH, NSM, NEH, NEM, _, _),
    EventCost
) :-
    time_to_minutes(OSH, OSM, OldStart),
    time_to_minutes(OEH, OEM, OldEnd),
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    (   (OldStart =\= NewStart ; OldEnd =\= NewEnd)
    ->  fact(move_penalty, MovePen),
        fact(shift_weight, ShiftW),
        fact(priority_factor, PriFactor),
        Shift is abs(NewStart - OldStart),
        ShiftHours is Shift / 60.0,
        EventCost is MovePen + ShiftHours * ShiftW + Priority * PriFactor
    ;   EventCost = 0
    ).
```

The per-event displacement formula is:

**EventCost = MovePenalty + ShiftHours × ShiftWeight + Priority × PriorityFactor**

| Parameter | Fact name | Default | Role |
|-----------|-----------|---------|------|
| MovePenalty | `fact(move_penalty, 3)` | 3 | Fixed penalty incurred whenever an event is moved, regardless of distance. Discourages unnecessary moves. |
| ShiftWeight | `fact(shift_weight, 2)` | 2 | Multiplier on hours displaced. Moving 2 hours costs 4; moving 30 min costs 1. Encourages nearby slots. |
| PriorityFactor | `fact(priority_factor, 0.5)` | 0.5 | Multiplier on priority value (1–10). Priority-10 adds 5.0; priority-2 adds 1.0. Makes moving high-priority events expensive. |

The total g(n) for a state is the sum of EventCost across all events that have moved:

**g(n) = Σᵢ EventCostᵢ** (for each event i that has moved)

Worked micro-example for g(n): Moving a priority-7 meeting from 09:00 to 10:00 (shift = 60 min = 1 hour):

**EventCost = 3 + (1.0 × 2) + (7 × 0.5) = 3 + 2 + 3.5 = 8.5**

#### 1.3.2 Priority Loss Heuristic — h(n): Estimated Future Cost

The heuristic h(n) estimates the minimum remaining cost to resolve all unresolved conflicts. For each event that is part of at least one remaining conflict, the system computes a loss value via `demo(event_priority_loss(...))`:

```prolog
solve(priority_loss(ConflictingEvents, Strategy), HCost) :-
    findall(Loss, (
        member(Event, ConflictingEvents),
        demo(event_priority_loss(Event, Strategy, Loss))
    ), Losses),
    sum_list(Losses, HCost).
```

The underlying rule:

```prolog
event_priority_loss(event(_Id, _T, _SH, _SM, _EH, _EM, Priority, _Ty), Strategy, Loss) :-
    strategy_weight(Strategy, W),
    Loss is Priority * Priority * W.
```

Per-event formula: **Loss = Priority² × W**

Total heuristic: **h(n) = Σⱼ (Priorityⱼ² × W)** for each event j in a remaining conflict

Why a quadratic penalty? A linear penalty treats a priority-10 event as only twice as urgent as a priority-5. Quadratic scaling creates a much steeper gradient:

| Priority | Linear (Priority × 1.0) | Quadratic (Priority² × 1.0) |
|----------|--------------------------|------------------------------|
| 3 | 3 | 9 |
| 5 | 5 | 25 |
| 7 | 7 | 49 |
| 10 | 10 | 100 |

This ensures the search strongly prioritises resolving conflicts involving high-priority events (exams, deadlines, interviews) before addressing lower-priority ones.

#### 1.3.3 Combined f(n) = g(n) + h(n)

The total evaluation score f(n) is computed for every state in the open list. The A* search always expands the state with the lowest f(n) first. This ensures:

- States with cheap moves and few remaining high-priority conflicts are explored first.
- States with expensive moves or many difficult conflicts are deferred.

### 1.4 Scheduling Strategies

The system supports three user-selectable scheduling strategies, each tuning how aggressively the search protects high-priority events versus minimising total moves.

```prolog
strategy_weight(minimize_moves,   0.5).
strategy_weight(maximize_quality, 2.0).
strategy_weight(balanced,         1.0).
```

#### 1.4.1 Minimize Moves (W = 0.5)

Goal: Reschedule as few events as possible, even if slightly sub-optimal in priority preservation.

- h(n) impact: Low weight (0.5) means unresolved high-priority conflicts contribute less to the heuristic. Search favours fewer total moves.
- Option A cost multiplied by 0.7 (discounted — moves affecting only the new event are cheaper).
- Option B cost multiplied by 1.3 (penalised — moves affecting existing events are more expensive).
- Effect: System prefers to move the single new event rather than rearrange multiple existing events.

#### 1.4.2 Maximize Quality (W = 2.0)

Goal: Protect high-priority events at all costs, even if more events must be moved.

- h(n) impact: High weight (2.0) dramatically amplifies the estimated cost of unresolved conflicts. Priority-10 event contributes 200 to h(n).
- If new event has high priority (≥ 8): Option A cost × 2.0, Option B cost × 0.5.
- If new event has low priority (< 8): Option A cost × 0.5, Option B cost × 1.5.
- Effect: High-priority events are treated as near-immovable anchors.

#### 1.4.3 Balanced (W = 1.0)

Goal: A neutral default that equally weighs displacement cost and priority protection.

- h(n) impact: Unit weight (1.0) provides a moderate heuristic signal. Priority-10 conflict contributes 100 to h(n).
- No adjustment multipliers applied — raw computed costs determine the decision.
- Effect: The system makes case-by-case decisions based on actual costs without any bias.

#### 1.4.4 Strategy Comparison Summary

| Aspect | minimize_moves (W=0.5) | balanced (W=1.0) | maximize_quality (W=2.0) |
|--------|------------------------|-------------------|--------------------------|
| h(n) for priority-10 conflict | 100 × 0.5 = 50 | 100 × 1.0 = 100 | 100 × 2.0 = 200 |
| h(n) for priority-3 conflict | 9 × 0.5 = 4.5 | 9 × 1.0 = 9 | 9 × 2.0 = 18 |
| Option A (move new) multiplier | ×0.7 | ×1.0 | ×2.0 (high-pri) / ×0.5 (low-pri) |
| Option B (move existing) multiplier | ×1.3 | ×1.0 | ×0.5 (high-pri) / ×1.5 (low-pri) |
| Typical outcome | Fewest events rescheduled | Balanced trade-off | High-priority events protected |

### 1.5 Option Generation and Comparison

Before launching the full A* state-space search, the solver generates up to three quick candidate solutions. This two-tier approach — fast heuristic options first, deep search as fallback — ensures simple conflicts are resolved instantly while complex multi-event conflicts receive optimal treatment.

#### 1.5.1 Option A: Move the New Event

The system finds the best alternative time slot for the new event while keeping all existing events in place. Candidates are generated at 30-minute intervals, filtered for conflicts, and scored:

**Score = DisplacementCost + SoftCost**

Total Option A cost: **Option1Cost = SlotCost + NewPriority × 0.5**

#### 1.5.2 Option B: Move Conflicting Existing Events

For each conflicting existing event, the system attempts relocation. If all conflicting events can be successfully relocated:

**Option2Cost = Σ SlotCostₖ + PriorityLoss**

If any conflicting event cannot be moved (no valid slot), Option B is marked infeasible with cost 9999.

#### 1.5.3 Option C: A* Deep Search

When neither quick option produces a satisfactory result, the full A* search explores the state space systematically. This handles complex cases where resolving one conflict creates another (chain conflicts), requiring coordinated multi-event rearrangement.

#### 1.5.4 Strategy-Adjusted Option Comparison (pick_best_option)

```prolog
pick_best_option(
    Strategy, NewPriority,
    option(move_new, Slot, Cost1),
    option(place_new, MovedEvents, Cost2),
    Result
) :-
    (   Strategy = minimize_moves
    ->  AdjCost1 is Cost1 * 0.7,
        AdjCost2 is Cost2 * 1.3
    ;   Strategy = maximize_quality
    ->  (   NewPriority >= 8
        ->  AdjCost1 is Cost1 * 2.0,
            AdjCost2 is Cost2 * 0.5
        ;   AdjCost1 is Cost1 * 0.5,
            AdjCost2 is Cost2 * 1.5
        )
    ;   AdjCost1 is Cost1,
        AdjCost2 is Cost2
    ),
    ...
```

### 1.6 Hard and Soft Constraints

#### 1.6.1 Hard Constraints

Hard constraints are binary — a solution violating any hard constraint is infeasible and immediately discarded. The system enforces four hard constraints:

| # | Constraint | Prolog rule | Formal definition |
|---|-----------|-------------|-------------------|
| H1 | No time overlap | `violation(no_overlap, ...)` | ¬overlap: ¬(StartA < EndB ∧ StartB < EndA) |
| H2 | Within scheduling bounds | `violation(before_working_hours, ...)` / `violation(after_working_hours, ...)` | Start ≥ 06:00 (360 min) ∧ End ≤ 23:00 (1380 min) |
| H3 | Positive duration | `violation(positive_duration, ...)` | End > Start |
| H4 | Fixed events immovable | (enforced in search) | Events of type exam or deadline are never moved during search. |

**Full meta-interpreter difference:** In `constraint_solve.pl`, hard constraint checking uses `demo/1`:

```prolog
%% OLD (constraint_solver.pl — wrapper):
check_hard(no_overlap, [Event, AllEvents]) :-
    \+ violation(no_overlap, Event, AllEvents, _).

%% NEW (constraint_solve.pl — full meta-interpreter):
check_hard(no_overlap, [Event, AllEvents]) :-
    \+ demo(violation(no_overlap, Event, AllEvents, _)).
```

When `demo(violation(...))` is called, `clause/2` retrieves the violation rule body, and `demo/1` recursively proves every sub-goal (`time_to_minutes`, `member`, arithmetic comparisons) — making the entire constraint-checking path transparent.

#### 1.6.2 Soft Constraints

Soft constraints are preferences — violations incur penalty costs that the optimiser minimises. The total soft cost for an event aggregates four components:

```prolog
solve(soft_cost(Event, AllEvents, Preferences), TotalCost) :-
    evaluate_soft(preferred_time,    [Event, AllEvents, Preferences], C1),
    evaluate_soft(buffer_proximity,  [Event, AllEvents, Preferences], C2),
    evaluate_soft(daily_overload,    [Event, AllEvents, Preferences], C3),
    evaluate_soft(priority_schedule, [Event, AllEvents, Preferences], C4),
    TotalCost is C1 + C2 + C3 + C4.
```

**Full meta-interpreter difference:** `evaluate_soft/3` calls `demo(soft_cost(...))` instead of direct `soft_cost(...)`. This means the soft cost rule bodies are opened via `clause/2`:

```prolog
evaluate_soft(preferred_time, [Event, AllEvents, Prefs], Cost) :-
    demo(soft_cost(preferred_time, Event, AllEvents, Prefs, Cost)).
```

**Soft Constraint 1 — Preferred Time Windows:**

Formula: PreferredCost = min( |Start − NearestWindowBoundary| ÷ 30, MaxPenalty )

| Event type | Preferred window(s) | Penalty cap |
|-----------|---------------------|-------------|
| meeting | 09:00–17:00 (540–1020 min) | 10 |
| study | 08:00–12:00 (480–720 min), 14:00–18:00 (840–1080 min) | 5 |
| exercise | 06:00–08:00 (360–480 min), 17:00–23:00 (1020–1380 min) | 3 |

**Soft Constraint 2 — Buffer Proximity:**

Events with less than a 15-minute gap between them incur: BufferCost = NumCloseEvents × 3

**Soft Constraint 3 — Daily Overload:**

| Condition | Cost formula |
|-----------|-------------|
| Total events > hard limit (8) | (N − 8) × 5 |
| Total events > soft limit (6) but ≤ 8 | (N − 6) × 2 |
| Total events ≤ 6 | 0 |

**Soft Constraint 4 — Priority Scheduling:**

High-priority events (priority ≥ 8) outside peak hours (09:00–17:00) incur: PriorityScheduleCost = (Priority − 7) × 3

Example: A priority-10 event outside peak hours costs (10 − 7) × 3 = 9.

### 1.7 Search Process

The full A* search is invoked when the quick option comparison cannot resolve all conflicts or when the system needs to verify optimality. The `astar_search/6` predicate follows the classic A* loop:

1. Sort the open list by f(n) cost (lowest first) using `sort_states_by_cost/2`.
2. Pop the best state — the state with the lowest f(n).
3. Goal check — if Conflicts = [], the state is a solution; return it immediately.
4. Expand successors — for each conflict, try moving each involved event to its best available slot. Compute new costs, record moves, add to open list if not in closed set.
5. Add current state to the closed set and recurse.

| Condition | Behaviour |
|-----------|-----------|
| Conflicts = [] | Goal found — return `solution(Events, Cost, Moves)` |
| Open = [] | No solution — return `solution([], 9999, [no_solution])` |
| MaxDepth = 0 | Budget exhausted — return best state found so far |

Depth Limit: The search has a configurable maximum depth. When depth reaches 0, the search returns the best state found so far rather than continuing indefinitely.

### 1.8 Worked Example

This section walks through a complete rescheduling scenario step by step.

**Setup — Existing events on Tuesday:**

| Event | Id | Time | Priority | Type |
|-------|-----|------|----------|------|
| Team Meeting | E1 | 09:00–10:00 | 7 | meeting |
| Lunch | E2 | 12:00–13:00 | 4 | personal |
| Study Session | E3 | 14:00–16:00 | 8 | study |

New event: **Exam Review (E_new), 09:30–11:00, Priority 10, Type: exam** | Strategy: balanced (W = 1.0)

**Step 1 — Conflict Detection (via full meta-interpreter):**

```
Python → check_conflict/6 → solve(check_conflict(9,30,11,0,Events), Conflicts)
  → demo(time_to_minutes(9, 30, NewStart))
      → clause/2 retrieves body → demo recursively → NewStart = 570
  → demo(time_to_minutes(11, 0, NewEnd))
      → clause/2 retrieves body → demo recursively → NewEnd = 660
  → findall(... demo(conflict(interval(570,660), Event, _)) ...)
```

- E_new vs E1: 570 < 600 AND 540 < 660 → Overlap detected ✗
- E_new vs E2: 720 is not < 660 → No overlap ✓
- E_new vs E3: 840 is not < 660 → No overlap ✓

Result: One conflict — `conflict(E_new, E1)`.

**Step 2 — Option A (Move Exam Review to 10:00–11:30):**

- Displacement: |10:00 − 09:30| = 30 min → ShiftHours = 0.5
- DisplacementCost = 3 + (0.5 × 2) + (10 × 0.5) = 3 + 1 + 5 = 9.0
- SoftCost: Within preferred window → 0. Buffer to E2 (12:00) = 30 min > 15 min → 0. Priority-10 within peak hours → 0.
- Total Option A cost = 9.0 + 0 = 9.0

**Step 3 — Option B (Move Team Meeting E1 to 11:00–12:00):**

- Displacement: |11:00 − 09:00| = 120 min → ShiftHours = 2.0
- SlotCost = 3 + (2.0 × 2) + (7 × 0.5) = 3 + 4 + 3.5 = 10.5
- PriorityLoss for E1 (priority 7, balanced W=1.0) = 7² × 1.0 = 49
- Total Option B cost = 10.5 + 49 = 59.5

**Step 4 — Strategy Adjustment (Balanced):** No multipliers applied.

**Step 5 — Decision:** Option A (9.0) < Option B (59.5) → System recommends moving the Exam Review to 10:00–11:30.

### 1.9 Chain Conflict Handling

When the solver moves an event to resolve one conflict, the new position may create a chain conflict — a secondary overlap with an event not previously involved. The A* search handles this naturally:

- After every move, `find_all_conflicts/2` is called to detect all pairwise overlaps including newly introduced ones.
- If new conflicts appear, the successor state's Conflicts list is non-empty, so the search continues.
- The depth limit prevents infinite chains from causing runaway computation.

### 1.10 Admissibility and Optimality

For A* to guarantee finding the optimal solution, the heuristic h(n) must be admissible — it must never overestimate the true remaining cost.

- h(n) = Σ Priority² × W estimates future cost by assuming each conflicting event will need to be moved.
- For balanced (W=1.0) and minimize_moves (W=0.5), the heuristic remains a lower bound.
- For maximize_quality (W=2.0), the heuristic may slightly overestimate in edge cases involving only low-priority events. This trade-off is intentional — it causes the search to favour protecting high-priority events.

---

## 2. Natural Language Processing via LLM Intent Parsing

### 2.1 Architecture

The system uses a prompt-engineered Large Language Model (LLM) pipeline to convert natural language scheduling requests into structured, executable intents. The pipeline consists of three stages:

```
User Text → [Intent Parser + LLM] → Structured JSON Intent → [Intent Executor] → Action
```

### 2.2 Intent Classification

The LLM classifies user input into one of the following intent types:

| Intent Type | Description | Example Trigger |
|------------|-------------|-----------------|
| create_event | Create a new calendar event | "Schedule a meeting with John tomorrow at 2pm" |
| find_free_slots | Find available time slots | "When am I free next week?" |
| move_event | Reschedule an existing event | "Move my dentist appointment to Friday" |
| delete_event | Cancel/remove an event | "Cancel my meeting tomorrow" |

### 2.3 JSON Extraction with Fallback

The parser employs a multi-stage JSON extraction strategy to handle LLM output variability:

1. **Direct Parse:** Attempt `json.loads()` on the raw response.
2. **Markdown Code Block Extraction:** Regex-match `` ```json ... ``` `` blocks.
3. **Embedded JSON Object Detection:** Regex-scan for `{ ... }` patterns within free-form text.

### 2.4 Schema Validation

Extracted JSON is validated against Pydantic models which enforce field presence and types, value ranges (e.g., `duration_minutes` between 15 and 480), and confidence thresholds — intents below 0.7 confidence trigger clarification prompts.

### 2.5 LLM Provider Abstraction

The system abstracts LLM communication behind a `BaseLLMClient` interface with concrete implementations for:

- **Ollama (local LLM, default):** Runs models like llama3.2 locally via Docker, using low temperature (0.1) for consistent JSON output.
- **Google Gemini (cloud API):** For higher-accuracy parsing when available.
- **MockLLMClient:** Keyword-matching fallback for testing and when LLM services are unavailable.

---

## 3. LLM-Based Priority Extraction from User Persona

### 3.1 Technique

The system uses a persona-driven priority extraction technique where the user provides a natural language description of themselves (their "story"), and the LLM infers event-type priority weights on a 1–10 scale. For example, a final-year computer science student preparing for a thesis defence would receive high priorities for exam (10), deadline (10), and interview (10), but lower priorities for social (3) and party (2).

### 3.2 Process

1. The user's story is sent to the LLM with a system prompt defining 18 event types and the expected JSON output schema.
2. The LLM returns a JSON object with priorities (event type → weight 1–10), persona_summary, reasoning, and recommended_strategy.
3. Priorities are normalised and clamped to the valid range [1, 10], with a default of 5 for unrecognised entries.
4. Extracted priorities are persisted in the UserProfile model and are used by the A* scheduling optimiser.

---

## 4. Prolog-Based Knowledge Representation and Reasoning (KRR) with Full Meta-Interpreter

### 4.1 Why Prolog

The system integrates SWI-Prolog as a knowledge-based reasoning engine for declarative constraint-based scheduling logic. Prolog's strengths for this domain include:

- **Declarative Rules:** Scheduling constraints are expressed as logical rules rather than imperative procedures.
- **Backtracking Search:** Prolog's built-in backtracking automatically explores alternative solutions when conflicts arise.
- **Pattern Matching:** Complex event structures are matched naturally using Prolog unification.
- **Knowledge Representation:** Facts, rules, constraints, and metadata are separated from the inference mechanism, following KRR best practices.

### 4.2 Six-Layer KRR Architecture

| Layer | Name | Purpose |
|-------|------|---------|
| 0 | Custom Operators | Domain-specific syntax (e.g., `overlaps_with`, `satisfies`, `violates`) |
| 1 | Facts (Knowledge Base) | Pure ground knowledge — domain constants, preference windows, strategy weights, metadata |
| 2 | Rules (Inference) | Declarative rules that derive new knowledge from facts |
| 3 | Constraints | Named, first-class constraint objects (hard/soft) |
| 4 | **Full Meta-Interpreter** | `demo/1` with `clause/2` — every domain predicate is opened up and recursively proved |
| 5 | Solver | `solve/2` — central entry point; domain reasoning routes through `demo/1` |

### 4.3 Knowledge Base (Facts)

The knowledge base stores domain constants, tunable parameters, preferred time windows, and self-describing metadata as Prolog facts:

```prolog
fact(slot_granularity, 30).
fact(working_hours_start, 360).     %% 6:00 AM
fact(working_hours_end, 1380).      %% 11:00 PM
preferred_window(meeting, 540, 1020).
strategy_weight(balanced, 1.0).
```

### 4.4 Inference Rules and Constraint Checking — Now via Full Meta-Interpreter

Scheduling rules are expressed as declarative inference rules. For example, the interval overlap rule:

```prolog
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.
```

**Key change:** All domain predicates are declared `:- dynamic` so `clause/2` can introspect them. When `demo(intervals_overlap(540, 600, 570, 660))` is called:

1. `clause/2` retrieves the body: `(540 < 660, 570 < 600)`
2. `demo/1` recursively proves: `demo(540 < 660)` → built-in → true, `demo(570 < 600)` → built-in → true

This is fundamentally different from `call(intervals_overlap(...))` which would resolve internally with no visibility.

Hard constraint violations are modelled as independent inference rules:

```prolog
violation(no_overlap, Event, AllEvents, overlap(OtherId, OtherTitle)) :- ...
violation(before_working_hours, Event, _, before_working_hours) :- ...
```

### 4.5 Central Solver (solve/2) — Now with demo/1 Integration

All high-level queries route through the `solve/2` predicate, which selects the appropriate reasoning strategy. **In the full meta-interpreter version, domain sub-goals within solve/2 are wrapped in `demo/1`:**

```prolog
%% OLD (scheduler.pl — wrapper):
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :-
    time_to_minutes(NSH, NSM, NewStart),     %% direct call
    ...

%% NEW (schedule.pl — full meta-interpreter):
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :-
    demo(time_to_minutes(NSH, NSM, NewStart)),   %% via clause/2
    demo(time_to_minutes(NEH, NEM, NewEnd)),     %% via clause/2
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        demo(conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), _Reason)),
        Conflicts
    ).
```

Public API predicates that Python calls are thin wrappers delegating to the solver:

```prolog
validate_hard_constraints(Event, AllEvents, Violations) :-
    solve(validate_hard(Event, AllEvents), Violations).
```

### 4.6 Python–Prolog Integration

The PrologService bridges the Python backend with SWI-Prolog through the pyswip library for in-process Prolog querying. If SWI-Prolog is unavailable at runtime, an equivalent Python fallback implementation is provided, ensuring the system operates identically regardless of the Prolog runtime's presence.

Integration flow: `Agent Executor → PrologService → SWI-Prolog (solve/2 → demo/1 → clause/2) → Constraint Validation Result`

---

## 5. Free Slot Finding Algorithm (Greedy Scan + CSP)

### 5.1 Approach

The system uses a Constraint Satisfaction Problem (CSP) approach combined with a greedy linear scan to find available time slots:

1. For each day in the requested range, define the working hours window (e.g., 06:00–23:00).
2. Generate candidate start times at 30-minute intervals within the allowed time bounds.
3. Test each candidate against all constraints (positive duration, within bounds, no overlap).
4. Collect all valid slots.

**Full meta-interpreter difference:** `check_all_slot_constraints` is called via `demo/1`:

```prolog
%% In solve(find_free_slots(...)):
demo(check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events))
```

This means `check_all_slot_constraints/5` is opened via `clause/2`, which in turn calls `demo(check_constraint(...))`, which opens `constraint/3` and proves the condition via `demo(Condition)`. Every step is transparent.

```prolog
check_all_slot_constraints(Start, End, MinStart, MaxEnd, Events) :-
    check_constraint(positive_duration, [Start, End]),
    check_constraint(within_bounds, [Start, End, MinStart, MaxEnd]),
    check_constraint(no_overlap, [Start, End, Events]).

check_constraint(Name, Args) :-
    constraint(Name, Args, Condition),
    demo(Condition).     %% ← demo/1 instead of call/1
```

### 5.2 Complexity

Given n events on a single day, the algorithm runs in O(n log n) due to sorting, followed by an O(n) linear scan — making it efficient for typical daily event counts.

---

## 6. Notification Scheduling (Periodic Job Scheduling)

### 6.1 Technique

The NotificationScheduler uses APScheduler (Advanced Python Scheduler) with an AsyncIOScheduler to periodically check for upcoming events and trigger email notifications.

### 6.2 Process

1. A periodic job runs at a configurable interval (e.g., every 60 seconds).
2. For each user with notifications enabled, the scheduler queries events within a look-ahead window defined by the user's notification preferences.
3. For each event-notification pair, the scheduler calculates the target notification time and checks if the current time falls within a ±1-minute window.
4. A deduplication set (`_sent_notifications`) keyed by `"{event_id}_{minutes_before}"` prevents duplicate notifications.

---

## 7. Real-Time Communication via WebSocket

### 7.1 Technique

The system uses WebSocket connections (via FastAPI's WebSocket support) to enable real-time push updates from the server to the frontend. This is used for:

- Notifying the client of schedule changes made by collaborators.
- Pushing real-time event updates without requiring client-side polling.

A ConnectionManager maintains active WebSocket connections keyed by user_id, allowing targeted message delivery.

---

## 8. RESTful API Design with Async I/O

### 8.1 Technique

The backend is built using FastAPI with full asynchronous I/O support:

- All database operations use SQLAlchemy's AsyncSession with the asyncpg PostgreSQL driver, enabling non-blocking database queries.
- HTTP calls to external LLM services (Ollama, Gemini) use the httpx async HTTP client.
- Prolog subprocess calls use `asyncio.create_subprocess_exec` for non-blocking process management.

### 8.2 Database Migrations

Schema evolution is managed using Alembic, which provides auto-generated migration scripts from SQLAlchemy model changes, version-controlled and reversible database migrations, and support for both upgrade and downgrade operations.

---

## 9. Containerisation with Docker Compose

The system uses Docker Compose for multi-service orchestration:

| Service | Image / Build | Purpose |
|---------|---------------|---------|
| postgres | postgres:16-alpine | Relational database (PostgreSQL) |
| backend | Custom Dockerfile | FastAPI backend API |
| ollama | ollama/ollama | Local LLM inference server (GPU-enabled) |

Service health checks, volume persistence, and inter-service networking are configured declaratively, ensuring reproducible deployments.

---

## Summary of Techniques and Algorithms

| Technique / Algorithm | Purpose | Location in Codebase |
|-----------------------|---------|---------------------|
| A* Search Algorithm | Optimal schedule rescheduling with constraints | constraint_solve.pl |
| LLM Intent Parsing (NLP) | Natural language → structured scheduling commands | agent/parser.py, agent/llm_clients.py |
| LLM Priority Extraction | Persona → event-type priority weights | services/priority_extractor.py |
| **Full Meta-Interpreter (demo/1 with clause/2)** | **Every domain predicate resolved transparently via clause-based resolution** | **schedule.pl, constraint_solve.pl** |
| Six-Layer KRR Architecture | Facts, rules, constraints, meta-interpreter, solver | schedule.pl, constraint_solve.pl |
| Central Solver (solve/2) with demo/1 | Unified reasoning entry point; domain goals route through demo/1 | schedule.pl, constraint_solve.pl |
| CSP Free Slot Finding via demo/1 | Constraint-based available time slot discovery | schedule.pl |
| Greedy Free Slot Scan | Find available time slots in a date range | services/availability_service.py |
| Periodic Job Scheduling | Time-based event notifications | services/notification_scheduler.py |
| WebSocket Real-Time Push | Live schedule update notifications | routers/ws.py |
| Async I/O (FastAPI + asyncpg) | Non-blocking concurrent request handling | Entire backend |
| Docker Compose Orchestration | Multi-service containerised deployment | docker/docker-compose.yml |
| demo_trace/2 (Proof Trees) | Builds explanation trees showing which rules fired and why | schedule.pl, constraint_solve.pl |
| demo_depth/2 (Depth-Limited) | Prevents infinite recursion in meta-interpreted resolution | schedule.pl, constraint_solve.pl |
| Cross-Module Fallback | constraint_solve.pl falls back to schedule:demo(Goal) for shared predicates | constraint_solve.pl |
