# Schedule Assistant System

# Chapter 5: Techniques and Algorithms Used for System Development

**Technical Design Report**

---

## Overview

The Schedule Assistant employs a combination of artificial intelligence, search algorithms, logic programming, knowledge representation and reasoning (KRR), and modern software engineering techniques to deliver an intelligent calendar management system. This chapter describes the key techniques and algorithms used across the system.

---

## 1. A\* Search Algorithm for Schedule Optimisation

### 1.1 Problem Definition

When a user adds a new event that conflicts with one or more existing events, the system must find an optimal rescheduling plan that minimises disruption to the user's calendar while respecting both hard and soft constraints. This is modelled as a **state-space search problem**: each state represents a complete arrangement of events on a single day, and transitions correspond to moving one event to a new time slot. The search must balance two competing objectives — resolving all time conflicts and minimising the total cost of the changes applied.

The A\* algorithm is chosen because it is both **complete** (it will always find a solution if one exists) and **optimal** (it finds the least-cost solution) when the heuristic function is admissible. For calendar rescheduling, this guarantees that the system recommends the solution that causes the least overall disruption to the user's existing schedule.

### 1.2 State Representation

Each state in the search space is a Prolog compound term:

```prolog
state(Events, OrigEvents, CurrentCost, Moves, Conflicts)
```

| Component | Description |
|---|---|
| `Events` | The full list of events with their current time placements in this state. Each event is an eight-argument term: `event(Id, Title, StartHour, StartMinute, EndHour, EndMinute, Priority, Type)`. |
| `OrigEvents` | The original (unmodified) event list as it existed before any rescheduling. This is preserved unchanged throughout the search and is used to compute displacement costs against the baseline. |
| `CurrentCost` | The accumulated g(n) cost to reach this state from the initial state. |
| `Moves` | An ordered list of `move(Id, NewSH, NewSM, NewEH, NewEM)` records describing every event move applied so far. |
| `Conflicts` | A list of `conflict(Id1, Id2)` pairs representing all remaining pairwise overlaps in this state. An empty list means the state is a goal state. |

**State-Key Deduplication**

To prevent the search from revisiting equivalent configurations, each state is mapped to a canonical key derived from the sorted list of `(EventId, StartMinutes)` tuples. Two states that have the same set of events at the same times — regardless of the order in which moves were applied — produce the same key and are treated as identical. States already in the **closed set** are never expanded again. This is implemented through the check `\+ member(NextState, Closed)` before a successor state is added to the open list.

### 1.3 Cost Functions

The A\* evaluation function is a composite of two components:

> **f(n) = g(n) + h(n)**

This is implemented in the solver as:

```prolog
solve(heuristic(OrigEvents, CurrState, RemConflicts, Strategy), FScore) :-
    solve(displacement_cost(OrigEvents, CurrState), G),
    solve(priority_loss(RemConflicts, Strategy), H),
    FScore is G + H.
```

#### 1.3.1 Displacement Cost — g(n): Actual Cost of Moves

The displacement cost g(n) measures the real, accumulated cost of all event moves that have been made to reach the current state. For every event whose time differs between the original schedule (`OrigEvents`) and the current state, a per-event cost is computed:

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

> **EventCost = MovePenalty + ShiftHours × ShiftWeight + Priority × PriorityFactor**

The three parameters are declared as Prolog facts (Layer 1 of the KRR architecture), making them inspectable and modifiable without changing any rule logic:

| Parameter | Fact name | Default value | Role |
|---|---|---|---|
| MovePenalty | `fact(move_penalty, 3)` | 3 | A fixed penalty incurred whenever an event is moved at all, regardless of how far. This discourages unnecessary moves. |
| ShiftWeight | `fact(shift_weight, 2)` | 2 | A multiplier on the number of hours the event is displaced. Moving an event by 2 hours costs 2 × 2 = 4, while moving it by 30 minutes costs 0.5 × 2 = 1. This encourages the solver to prefer nearby time slots. |
| PriorityFactor | `fact(priority_factor, 0.5)` | 0.5 | A multiplier on the event's priority value (1–10). A priority-10 event adds 10 × 0.5 = 5.0 to its displacement cost, while a priority-2 event adds only 2 × 0.5 = 1.0. This makes it progressively more expensive to move high-priority events. |

The total g(n) for a state is the sum of `EventCost` across all events whose positions differ from the original:

> **g(n) = Σᵢ EventCostᵢ** (for each event *i* that has moved)

An event that has not moved contributes zero to g(n) by the guard clause `(OldStart =\= NewStart ; OldEnd =\= NewEnd)`.

**Worked micro-example for g(n):** Moving a priority-7 meeting from 09:00 to 10:00 (shift = 60 min = 1 hour):

> EventCost = 3 + (1.0 × 2) + (7 × 0.5) = 3 + 2 + 3.5 = **8.5**

#### 1.3.2 Priority Loss Heuristic — h(n): Estimated Future Cost

The heuristic h(n) estimates the minimum remaining cost to resolve all unresolved conflicts. For each event that is part of at least one remaining conflict, the system computes a loss value:

```prolog
event_priority_loss(event(_Id, _T, _SH, _SM, _EH, _EM, Priority, _Ty), Strategy, Loss) :-
    strategy_weight(Strategy, W),
    Loss is Priority * Priority * W.
```

The per-event formula is:

> **Loss = Priority² × W**

Where `W` is the strategy weight (see Section 1.4). The total heuristic is:

> **h(n) = Σⱼ (Priorityⱼ² × W)** (for each event *j* involved in a remaining conflict)

**Why a quadratic penalty?** A linear penalty (Priority × W) would treat a priority-10 event as only twice as urgent as a priority-5 event. The quadratic scaling (Priority²) creates a much steeper gradient:

| Priority | Linear (Priority × 1.0) | Quadratic (Priority² × 1.0) |
|---|---|---|
| 3 | 3 | 9 |
| 5 | 5 | 25 |
| 7 | 7 | 49 |
| 10 | 10 | 100 |

This ensures that the search strongly prioritises resolving conflicts involving high-priority events (exams, deadlines, interviews) before addressing lower-priority ones (social gatherings, personal errands). A single unresolved conflict with a priority-10 event contributes 100 × W to h(n), making it extremely expensive to leave that conflict unresolved.

#### 1.3.3 Combined f(n) = g(n) + h(n)

The total evaluation score f(n) is computed for every state in the open list. The A\* search always expands the state with the lowest f(n) first (`sort_states_by_cost/2`). This ensures:

- States that have taken cheap moves *and* have few remaining high-priority conflicts are explored first.
- States that have taken expensive moves or still face many difficult conflicts are deferred.

### 1.4 Scheduling Strategies

The system supports three user-selectable scheduling strategies, each of which tunes how aggressively the search protects high-priority events versus minimising the total number of moves. Strategies affect both the **h(n) heuristic weight** and the **option comparison adjustments** applied by `pick_best_option/5`.

The strategy weights are declared as Prolog facts:

```prolog
strategy_weight(minimize_moves,  0.5).
strategy_weight(maximize_quality, 2.0).
strategy_weight(balanced,         1.0).
```

#### 1.4.1 Minimize Moves (W = 0.5)

**Goal:** Reschedule as few events as possible, even if the result is slightly sub-optimal in terms of priority preservation.

- **h(n) impact:** The low weight (0.5) means that unresolved conflicts involving high-priority events contribute less to the heuristic. The search is less aggressively steered toward resolving high-priority conflicts first and instead favours states that require fewer total moves.
- **Option comparison adjustment:** When comparing Option A (move the new event) against Option B (move existing events), the costs are adjusted:
  - Option A cost is multiplied by **0.7** (discounted — moves that affect only the new event are cheaper).
  - Option B cost is multiplied by **1.3** (penalised — moves that affect existing events are more expensive).
- **Effect:** The system prefers to move the single new event rather than rearrange multiple existing events, reducing user disruption.

#### 1.4.2 Maximize Quality (W = 2.0)

**Goal:** Protect high-priority events at all costs, even if it means moving more events or moving them farther.

- **h(n) impact:** The high weight (2.0) dramatically amplifies the estimated cost of unresolved conflicts. A priority-10 event in conflict contributes 10² × 2.0 = 200 to h(n), creating enormous pressure to resolve that conflict immediately.
- **Option comparison adjustment:** The adjustment depends on the **new event's priority**:
  - If the new event has **high priority (≥ 8):**
    - Option A cost is multiplied by **2.0** (heavily penalised — do not move the important new event).
    - Option B cost is multiplied by **0.5** (heavily discounted — prefer moving lower-priority existing events instead).
  - If the new event has **low priority (< 8):**
    - Option A cost is multiplied by **0.5** (discounted — the new event is less important, move it).
    - Option B cost is multiplied by **1.5** (penalised — protect the existing events).
- **Effect:** High-priority events are treated as near-immovable anchors; the system rearranges lower-priority events around them.

#### 1.4.3 Balanced (W = 1.0)

**Goal:** A neutral default that equally weighs displacement cost and priority protection.

- **h(n) impact:** The unit weight (1.0) provides a moderate heuristic signal. A priority-10 conflict contributes 100 to h(n), which is significant but not overwhelming.
- **Option comparison adjustment:** No adjustment is applied — `AdjCost1 = Cost1` and `AdjCost2 = Cost2`. The raw computed costs determine the decision directly.
- **Effect:** The system makes a case-by-case decision based on the actual costs without any bias toward moving or preserving any particular event.

#### 1.4.4 Strategy Comparison Summary

| Aspect | minimize\_moves (W=0.5) | balanced (W=1.0) | maximize\_quality (W=2.0) |
|---|---|---|---|
| h(n) for priority-10 conflict | 100 × 0.5 = 50 | 100 × 1.0 = 100 | 100 × 2.0 = 200 |
| h(n) for priority-3 conflict | 9 × 0.5 = 4.5 | 9 × 1.0 = 9 | 9 × 2.0 = 18 |
| Option A (move new) multiplier | ×0.7 | ×1.0 | ×2.0 (high-pri new) / ×0.5 (low-pri new) |
| Option B (move existing) multiplier | ×1.3 | ×1.0 | ×0.5 (high-pri new) / ×1.5 (low-pri new) |
| Typical outcome | Fewest events rescheduled | Balanced trade-off | High-priority events protected |

### 1.5 Option Generation and Comparison

Before launching the full A\* state-space search, the solver generates up to three quick candidate solutions and compares them. This two-tier approach — fast heuristic options first, deep search as fallback — ensures that simple conflicts are resolved instantly while complex multi-event conflicts still receive optimal treatment.

#### 1.5.1 Option A: Move the New Event

The system calls `solve(find_best_slot(NewEvent, ExistingEvents, MinH, MinM, MaxH, MaxM), Slot)` to find the best alternative time slot for the new event while keeping all existing events in place. The best slot is selected by:

1. Generating candidate start times at 30-minute intervals across the full scheduling window.
2. Filtering out candidates that would conflict with any existing event.
3. Scoring each valid candidate: `Score = DisplacementCost + SoftCost`, where displacement measures how far the new event moves from its requested time and soft cost captures preference violations.
4. Returning the lowest-scoring slot.

The total Option A cost is:

> **Option1Cost = SlotCost + NewPriority × 0.5**

The `NewPriority × 0.5` term adds a penalty proportional to the new event's importance — moving a high-priority new event is inherently more costly.

#### 1.5.2 Option B: Move Conflicting Existing Events

For each existing event that conflicts with the new event, the system attempts to relocate it to a free slot (using the same `find_best_slot` mechanism). If all conflicting events can be successfully relocated:

> **Option2Cost = Σ SlotCostₖ + PriorityLoss**

Where `PriorityLoss` is computed by `solve(priority_loss(ConflictingEvents, Strategy), PLoss)`, adding the quadratic priority penalty for each displaced existing event. If any conflicting event cannot be moved (no valid slot exists), Option B is marked as infeasible with a cost of 9999.

#### 1.5.3 Option C: A\* Deep Search

When neither quick option produces a satisfactory result, the full A\* search (Section 1.7) explores the state space systematically. This handles complex cases where resolving one conflict creates another (chain conflicts), requiring a coordinated multi-event rearrangement.

#### 1.5.4 Strategy-Adjusted Option Comparison (`pick_best_option`)

After computing raw costs for Options A and B, the strategy-specific multipliers are applied:

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

The option with the lowest adjusted cost wins. If both options are infeasible (cost = 9999), the solver falls back to `result(no_solution, [], 9999)`. The decision logic also ensures that a 9999-cost option is never chosen when a feasible alternative exists.

### 1.6 Hard and Soft Constraints

#### 1.6.1 Hard Constraints

Hard constraints are binary — a solution that violates any hard constraint is **infeasible** and is immediately discarded. The system enforces four hard constraints, each modelled as a separate Prolog inference rule:

| # | Constraint | Prolog rule | Formal definition |
|---|---|---|---|
| H1 | **No time overlap** | `violation(no_overlap, ...)` | For any two events *A* and *B*: ¬(StartA < EndB ∧ StartB < EndA), i.e., their time intervals must not overlap. |
| H2 | **Within scheduling bounds** | `violation(before_working_hours, ...)` / `violation(after_working_hours, ...)` | For every event: Start ≥ WorkStart (360 min = 06:00) ∧ End ≤ WorkEnd (1380 min = 23:00). |
| H3 | **Positive duration** | `violation(positive_duration, ...)` | For every event: End > Start. |
| H4 | **Fixed events immovable** | (enforced in search) | Events of type `exam` or `deadline` are never selected as candidates for moving during the search. |

#### 1.6.2 Soft Constraints

Soft constraints are preferences — violations incur **penalty costs** that the optimiser minimises. The total soft cost for an event is:

```prolog
solve(soft_cost(Event, AllEvents, Preferences), TotalCost) :-
    evaluate_soft(preferred_time,    [Event, AllEvents, Preferences], C1),
    evaluate_soft(buffer_proximity,  [Event, AllEvents, Preferences], C2),
    evaluate_soft(daily_overload,    [Event, AllEvents, Preferences], C3),
    evaluate_soft(priority_schedule, [Event, AllEvents, Preferences], C4),
    TotalCost is C1 + C2 + C3 + C4.
```

**Soft Constraint 1 — Preferred Time Windows**

Each event type has one or more preferred time windows defined as facts:

| Event type | Preferred window(s) | Penalty cap |
|---|---|---|
| `meeting` | 09:00–17:00 (540–1020 min) | 10 |
| `study` | 08:00–12:00 (480–720 min), 14:00–18:00 (840–1080 min) | 5 |
| `exercise` | 06:00–08:00 (360–480 min), 17:00–23:00 (1020–1380 min) | 3 |

If an event's start time falls within any of its preferred windows, the cost is 0. Otherwise, the penalty is the distance from the nearest window boundary divided by the slot step (30 min), capped at the event type's maximum penalty:

> **PreferredCost = min( |Start − NearestWindowBoundary| ÷ 30, MaxPenalty )**

**Soft Constraint 2 — Buffer Proximity**

Events with less than a 15-minute gap between them are considered "too close." The cost is calculated by counting the number of neighbouring events that fall within the buffer zone:

> **BufferCost = NumCloseEvents × 3**

Where `NumCloseEvents` is the count of events that end within 15 minutes before the event starts, or start within 15 minutes after the event ends.

**Soft Constraint 3 — Daily Overload**

The system discourages packing too many events into a single day using a two-tier penalty:

| Condition | Cost formula |
|---|---|
| Total events > hard limit (8) | (N − 8) × 5 |
| Total events > soft limit (6) but ≤ 8 | (N − 6) × 2 |
| Total events ≤ 6 | 0 |

**Soft Constraint 4 — Priority Scheduling**

High-priority events (priority ≥ 8) are expected to be placed during peak productivity hours (09:00–17:00). Events outside this window incur:

> **PriorityScheduleCost = (Priority − 7) × 3**

For example, a priority-10 event outside peak hours costs (10 − 7) × 3 = 9. Events with priority < 8 incur no penalty regardless of placement.

### 1.7 Search Process

The full A\* search is invoked when the quick option comparison (Section 1.5) cannot resolve all conflicts or when the system needs to verify optimality. The search is initialised in `find_optimal_schedule/6`:

```prolog
find_optimal_schedule(Events, NewEvent, Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution) :-
    append([NewEvent], Events, InitialEvents),
    find_all_conflicts(InitialEvents, Conflicts),
    (   Conflicts = []
    ->  Solution = solution(InitialEvents, 0, [])
    ;   InitialState = state(InitialEvents, Events, 0, [], Conflicts),
        astar_search([InitialState], [], Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution)
    ).
```

The `astar_search/6` predicate follows the classic A\* loop:

1. **Sort the open list** by f(n) cost (lowest first) using `sort_states_by_cost/2`.
2. **Pop the best state** — the state with the lowest f(n).
3. **Goal check** — if `Conflicts = []`, the state is a solution; return it immediately.
4. **Expand successors** — for each conflict `conflict(Id1, Id2)`, try moving each involved event (`Id1` or `Id2`) to its best available slot via `solve(find_best_slot(...), Slot)`. For each successful move:
   - Replace the event's time in the events list (`replace_event_time/7`).
   - Recompute all conflicts in the new state (`find_all_conflicts/2`).
   - Compute the new accumulated cost.
   - Record the move in the moves list.
   - Add the successor state to the open list if it is not in the closed set.
5. **Add the current state to the closed set** and recurse.

**Depth Limit:** The search has a configurable maximum depth (`MaxDepth`). When depth reaches 0, the search returns the best state found so far (the first state in the sorted open list) rather than continuing indefinitely. This provides a safety bound for pathological cases.

**Termination Conditions:**

| Condition | Behaviour |
|---|---|
| `Conflicts = []` | Goal found — return `solution(Events, Cost, Moves)` |
| `Open = []` | No solution — return `solution([], 9999, [no_solution])` |
| `MaxDepth = 0` | Budget exhausted — return the best state found so far |

### 1.8 Worked Example

This section walks through a complete rescheduling scenario step by step, showing how conflict detection, cost calculation, strategy adjustment, and the final decision work together.

#### Setup

**Existing events on Tuesday:**

| Event | Id | Time | Priority | Type |
|---|---|---|---|---|
| Team Meeting | `E1` | 09:00–10:00 | 7 | meeting |
| Lunch | `E2` | 12:00–13:00 | 4 | personal |
| Study Session | `E3` | 14:00–16:00 | 8 | study |

**New event to add:** Exam Review (`E_new`), 09:30–11:00, Priority 10, Type: exam

**Strategy:** balanced (W = 1.0)

#### Step 1 — Conflict Detection

The system computes pairwise overlaps between E\_new and every existing event:

- **E\_new vs E1:** 09:30 (NewStart) < 10:00 (E1 End) **and** 09:00 (E1 Start) < 11:00 (NewEnd) → **Overlap detected** ✗
- **E\_new vs E2:** 09:30 < 13:00 **but** 12:00 ≮ 11:00 → No overlap ✓
- **E\_new vs E3:** 09:30 < 16:00 **but** 14:00 ≮ 11:00 → No overlap ✓

**Result:** One conflict — `conflict(E_new, E1)`.

#### Step 2 — Option A: Move the New Event (Exam Review)

The system searches for the best free slot for a 90-minute event (09:30–11:00 duration = 90 min):

- **Candidate 10:00–11:30:** No overlap with E1 (ends 10:00), E2 (starts 12:00), E3 (starts 14:00). Valid.
  - Displacement: |10:00 − 09:30| = 30 min → ShiftHours = 0.5
  - DisplacementCost = 3 + (0.5 × 2) + (10 × 0.5) = 3 + 1 + 5 = **9.0**
  - SoftCost: Start 10:00 = 600 min, within meeting window 540–1020 → preferred\_time = 0; buffer to E2 (12:00) = 30 min > 15 min → buffer = 0; priority 10 ≥ 8, start 600 within 540–1020 → priority\_schedule = 0.
  - **Total Option A cost = 9.0 + 0 = 9.0**

#### Step 3 — Option B: Move Team Meeting (E1) to Make Room

The system tries to relocate the priority-7 Team Meeting (1-hour event) while keeping E\_new at 09:30–11:00:

- **Candidate 11:00–12:00:** No overlap with E\_new (ends 11:00), E2 (starts 12:00 — edge case, no overlap since 12:00 is not < 12:00). Valid.
  - Displacement: |11:00 − 09:00| = 120 min → ShiftHours = 2.0
  - SlotCost = 3 + (2.0 × 2) + (7 × 0.5) = 3 + 4 + 3.5 = **10.5**
  - PriorityLoss for E1 (priority 7, balanced W=1.0) = 7² × 1.0 = **49**
  - **Total Option B cost = 10.5 + 49 = 59.5**

#### Step 4 — Strategy Adjustment (Balanced)

Under the balanced strategy, no adjustment multipliers are applied:

- **Adjusted Option A cost = 9.0 × 1.0 = 9.0**
- **Adjusted Option B cost = 59.5 × 1.0 = 59.5**

#### Step 5 — Decision

Option A (9.0) < Option B (59.5) → The system recommends **moving the Exam Review to 10:00–11:30**.

#### What If the Strategy Were Different?

- **minimize\_moves:** AdjA = 9.0 × 0.7 = 6.3, AdjB = 59.5 × 1.3 = 77.35 → Still Option A (same decision, even more strongly).
- **maximize\_quality:** Since the new event has priority 10 (≥ 8): AdjA = 9.0 × 2.0 = **18.0**, AdjB = 59.5 × 0.5 = **29.75** → Still Option A, but the gap narrows significantly. If Option A had a higher base cost (e.g., the only free slot was far away), maximize\_quality could flip the decision to Option B to protect the high-priority new event.

### 1.9 Chain Conflict Handling

When the solver moves an event to resolve one conflict, the new position may create a **chain conflict** — a secondary overlap with an event that was not previously involved. The A\* search handles this naturally:

1. After every move, `find_all_conflicts/2` is called on the updated event list to detect all pairwise overlaps, including newly introduced ones.
2. If new conflicts appear, the successor state's `Conflicts` list is non-empty, so it is not a goal state and the search continues expanding.
3. The depth limit prevents infinite chains from causing runaway computation.

Additionally, the `detect_chain_conflicts/4` predicate is available for targeted chain-conflict detection after a specific event move, enabling the Python layer to warn the user if a proposed move would create downstream conflicts before committing to it.

### 1.10 Admissibility and Optimality

For A\* to guarantee finding the **optimal** (lowest-cost) solution, the heuristic h(n) must be **admissible** — it must never overestimate the true remaining cost to reach a goal state.

**Why h(n) is admissible in this system:**

- h(n) = Σ Priority² × W estimates the future cost by assuming each conflicting event will need to be moved. In practice, resolving a conflict always incurs at least the displacement cost of moving one event, which itself includes a base penalty of 3 plus time-shift and priority components.
- However, the priority-loss heuristic does not account for the actual displacement costs that will be incurred — it only uses the priority-based estimate. Since the displacement cost (move penalty + shift + priority factor) adds on top of the heuristic estimate, the true cost of resolving each conflict is at least as high as the heuristic predicts for events with moderate-to-high priority, while for low-priority events the heuristic is conservative.
- The strategy weight W scales the heuristic uniformly. For the balanced strategy (W = 1.0) and minimize\_moves (W = 0.5), the heuristic remains a lower bound. For maximize\_quality (W = 2.0), the heuristic may slightly overestimate in edge cases involving only low-priority events, but this trade-off is intentional — it causes the search to favour protecting high-priority events even at the expense of strict optimality in trivial cases.

In practice, the depth limit and closed-set deduplication ensure that the search always terminates efficiently, and the three-option comparison (Section 1.5) provides rapid solutions for the common case of single-conflict scenarios.

---

## 2. Natural Language Processing via LLM Intent Parsing

### 2.1 Architecture

The system uses a prompt-engineered Large Language Model (LLM) pipeline to convert natural language scheduling requests into structured, executable intents. The pipeline consists of three stages:

> User Text → \[Intent Parser + LLM\] → Structured JSON Intent → \[Intent Executor\] → Action

### 2.2 Intent Classification

The LLM classifies user input into one of the following intent types:

| Intent Type | Description | Example Trigger |
|---|---|---|
| create\_event | Create a new calendar event | "Schedule a meeting with John tomorrow at 2pm" |
| find\_free\_slots | Find available time slots | "When am I free next week?" |
| move\_event | Reschedule an existing event | "Move my dentist appointment to Friday" |
| delete\_event | Cancel/remove an event | "Cancel my meeting tomorrow" |

Each parsed intent includes: intent\_type, confidence (0.0–1.0), structured data fields, and an optional clarification question.

### 2.3 JSON Extraction with Fallback

The parser employs a multi-stage JSON extraction strategy to handle LLM output variability:

1. **Direct Parse**: Attempt `json.loads()` on the raw response.
2. **Markdown Code Block Extraction**: Regex-match `` ```json ... ``` `` blocks.
3. **Embedded JSON Object Detection**: Regex-scan for `{ ... }` patterns within free-form text.

### 2.4 Schema Validation

Extracted JSON is validated against Pydantic models which enforce field presence and types, value ranges (e.g., duration\_minutes between 15 and 480), and confidence thresholds — intents below 0.7 confidence trigger clarification prompts.

### 2.5 LLM Provider Abstraction

The system abstracts LLM communication behind a `BaseLLMClient` interface with concrete implementations for:

- **Ollama** (local LLM, default): Runs models like llama3.2 locally via Docker, using low temperature (0.1) for consistent JSON output.
- **Google Gemini** (cloud API): For higher-accuracy parsing when available.
- **MockLLMClient**: Keyword-matching fallback for testing and when LLM services are unavailable.

---

## 3. LLM-Based Priority Extraction from User Persona

### 3.1 Technique

The system uses a persona-driven priority extraction technique where the user provides a natural language description of themselves (their "story"), and the LLM infers event-type priority weights on a 1–10 scale. For example, a final-year computer science student preparing for a thesis defence would receive high priorities for exam (10), deadline (10), and interview (10), but lower priorities for social (3) and party (2).

### 3.2 Process

1. The user's story is sent to the LLM with a system prompt defining 18 event types and the expected JSON output schema.
2. The LLM returns a JSON object with priorities (event type → weight 1–10), persona\_summary, reasoning, and recommended\_strategy.
3. Priorities are normalised and clamped to the valid range \[1, 10\], with a default of 5 for unrecognised entries.
4. Extracted priorities are persisted in the `UserProfile` model and are used by the A\* scheduling optimiser.

---

## 4. Prolog-Based Knowledge Representation and Reasoning (KRR)

### 4.1 Why Prolog

The system integrates SWI-Prolog as a knowledge-based reasoning engine for declarative constraint-based scheduling logic. Prolog's strengths for this domain include:

- **Declarative Rules**: Scheduling constraints are expressed as logical rules rather than imperative procedures.
- **Backtracking Search**: Prolog's built-in backtracking automatically explores alternative solutions when conflicts arise.
- **Pattern Matching**: Complex event structures are matched naturally using Prolog unification.
- **Knowledge Representation**: Facts, rules, constraints, and metadata are separated from the inference mechanism, following KRR best practices.

### 4.2 Six-Layer KRR Architecture

The Prolog reasoning engine follows a six-layer Knowledge Representation and Reasoning (KRR) architecture:

| Layer | Name | Purpose |
|---|---|---|
| 0 | **Custom Operators** | Domain-specific syntax (e.g., `overlaps_with`, `satisfies`, `violates`) |
| 1 | **Facts (Knowledge Base)** | Pure ground knowledge — domain constants, preference windows, strategy weights, metadata |
| 2 | **Rules (Inference)** | Declarative rules that derive new knowledge from facts |
| 3 | **Constraints** | Named, first-class constraint objects (hard/soft) |
| 4 | **Meta-Interpreter** | `demo/1` / `holds/1` — a lightweight prove-engine for explicit reasoning |
| 5 | **Solver** | `solve/2` — central entry point; all queries dispatch through the solver |

### 4.3 Knowledge Base (Facts)

The knowledge base stores domain constants, tunable parameters, preferred time windows, and self-describing metadata as Prolog facts:

```prolog
fact(slot_granularity, 30).
fact(working_hours_start, 360).     %% 6:00 AM
fact(working_hours_end, 1380).      %% 11:00 PM
preferred_window(meeting, 540, 1020).
strategy_weight(balanced, 1.0).
```

Facts can be queried, composed, and reasoned about — they are separate from the inference mechanism.

### 4.4 Inference Rules and Constraint Checking

Scheduling rules are expressed as declarative inference rules. For example, the interval overlap rule:

```prolog
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.
```

Hard constraint violations are modelled as independent inference rules:

```prolog
violation(no_overlap, Event, AllEvents, overlap(OtherId, OtherTitle)) :- ...
violation(before_working_hours, Event, _, before_working_hours) :- ...
```

### 4.5 Central Solver (`solve/2`)

All high-level queries route through the `solve/2` predicate, which selects the appropriate reasoning strategy. Public API predicates that Python calls are thin wrappers delegating to the solver:

```prolog
validate_hard_constraints(Event, AllEvents, Violations) :-
    solve(validate_hard(Event, AllEvents), Violations).
```

### 4.6 Python–Prolog Integration

The `PrologService` bridges the Python backend with SWI-Prolog through the `pyswip` library for in-process Prolog querying. If SWI-Prolog is unavailable at runtime, an equivalent Python fallback implementation is provided, ensuring the system operates identically regardless of the Prolog runtime's presence.

The integration follows the flow:

> Agent Executor → PrologService → SWI-Prolog (solve/2) → Constraint Validation Result

---

## 5. Free Slot Finding Algorithm (Greedy Scan + CSP)

### 5.1 Approach

The system uses a Constraint Satisfaction Problem (CSP) approach combined with a greedy linear scan to find available time slots:

1. For each day in the requested range, define the working hours window (e.g., 06:00–23:00).
2. Generate candidate start times at 30-minute intervals within the allowed time bounds.
3. Test each candidate against all constraints (positive duration, within bounds, no overlap with any existing event).
4. Collect all valid slots.

The constraint check leverages first-class named constraint objects:

```prolog
check_all_slot_constraints(Start, End, MinStart, MaxEnd, Events) :-
    check_constraint(positive_duration, [Start, End]),
    check_constraint(within_bounds, [Start, End, MinStart, MaxEnd]),
    check_constraint(no_overlap, [Start, End, Events]).
```

### 5.2 Complexity

Given n events on a single day, the algorithm runs in O(n log n) due to sorting, followed by an O(n) linear scan — making it efficient for typical daily event counts.

---

## 6. Notification Scheduling (Periodic Job Scheduling)

### 6.1 Technique

The `NotificationScheduler` uses APScheduler (Advanced Python Scheduler) with an `AsyncIOScheduler` to periodically check for upcoming events and trigger email notifications.

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

A `ConnectionManager` maintains active WebSocket connections keyed by `user_id`, allowing targeted message delivery.

---

## 8. RESTful API Design with Async I/O

### 8.1 Technique

The backend is built using FastAPI with full asynchronous I/O support:

- All database operations use SQLAlchemy's `AsyncSession` with the `asyncpg` PostgreSQL driver, enabling non-blocking database queries.
- HTTP calls to external LLM services (Ollama, Gemini) use the `httpx` async HTTP client.
- Prolog subprocess calls use `asyncio.create_subprocess_exec` for non-blocking process management.

### 8.2 Database Migrations

Schema evolution is managed using Alembic, which provides auto-generated migration scripts from SQLAlchemy model changes, version-controlled and reversible database migrations, and support for both upgrade and downgrade operations.

---

## 9. Containerisation with Docker Compose

The system uses Docker Compose for multi-service orchestration:

| Service | Image / Build | Purpose |
|---|---|---|
| postgres | postgres:16-alpine | Relational database (PostgreSQL) |
| backend | Custom Dockerfile | FastAPI backend API |
| ollama | ollama/ollama | Local LLM inference server (GPU-enabled) |

Service health checks, volume persistence, and inter-service networking are configured declaratively, ensuring reproducible deployments.

---

## Summary of Techniques and Algorithms

The following table summarises all key techniques used in the Schedule Assistant system, their purpose, and their location in the codebase.

| Technique / Algorithm | Purpose | Location in Codebase |
|---|---|---|
| A\* Search Algorithm | Optimal schedule rescheduling with constraints | `services/scheduling_service.py` |
| LLM Intent Parsing (NLP) | Natural language → structured scheduling commands | `agent/parser.py`, `agent/llm_clients.py` |
| LLM Priority Extraction | Persona → event-type priority weights | `services/priority_extractor.py` |
| Prolog KRR Engine | Declarative knowledge-based reasoning for scheduling | `apps/backend/app/chat/prolog/scheduler.pl`, `constraint_solver.pl` |
| Six-Layer KRR Architecture | Facts, rules, constraints, meta-interpreter, solver | `scheduler.pl`, `constraint_solver.pl` |
| Meta-Interpreter (`demo/1`) | Explicit provability reasoning over the knowledge base | `scheduler.pl`, `constraint_solver.pl` |
| Central Solver (`solve/2`) | Unified reasoning entry point for all scheduling queries | `scheduler.pl`, `constraint_solver.pl` |
| CSP Free Slot Finding | Constraint-based available time slot discovery | `scheduler.pl` |
| Greedy Free Slot Scan | Find available time slots in a date range | `services/availability_service.py` |
| Periodic Job Scheduling | Time-based event notifications | `services/notification_scheduler.py` |
| WebSocket Real-Time Push | Live schedule update notifications | `routers/ws.py` |
| Async I/O (FastAPI + asyncpg) | Non-blocking concurrent request handling | Entire backend |
| Docker Compose Orchestration | Multi-service containerised deployment | `docker/docker-compose.yml` |
