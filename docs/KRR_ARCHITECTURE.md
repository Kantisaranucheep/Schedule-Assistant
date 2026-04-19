# Knowledge Representation and Reasoning (KRR) Architecture

## Schedule Assistant — Prolog Reasoning Engine

This document explains how the Schedule Assistant implements **Knowledge Representation and Reasoning (KRR)** principles using SWI-Prolog as the reasoning engine and Python as a thin interface layer.

---

## Table of Contents

1. [Overall Architecture](#1-overall-architecture)
2. [KRR Concept Checklist](#2-krr-concept-checklist)
3. [Facts](#3-facts)
4. [Rules](#4-rules)
5. [Constraints](#5-constraints)
6. [Custom Operators](#6-custom-operators)
7. [Meta-Interpreter](#7-meta-interpreter)
8. [Metadata (Reasoning Introspection)](#8-metadata-reasoning-introspection)
9. [Solvers (Black Box API)](#9-solvers-black-box-api)
10. [Condition → Action](#10-condition--action)
11. [Dual-Method Architecture](#11-dual-method-architecture)
12. [File Map](#12-file-map)

---

## 1. Overall Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     User / Frontend                       │
└──────────────────────┬───────────────────────────────────┘
                       │  "Add event: Meeting 10:00-11:00"
                       ▼
┌──────────────────────────────────────────────────────────┐
│                  Python (service.py)                       │
│                                                            │
│  Role: QUESTIONER — asks high-level questions              │
│  Does NOT know which Prolog predicates are used internally │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  "Can this event be added? Here is all the data."     │ │
│  │  handle_add_event(10, 0, 11, 0, ExistingEvents, ...) │ │
│  └──────────────────────────┬───────────────────────────┘ │
└─────────────────────────────┼────────────────────────────┘
                              │  pyswip query
                              ▼
┌──────────────────────────────────────────────────────────┐
│               Prolog Knowledge Engine                      │
│                                                            │
│  ┌─────────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │   FACTS     │  │  RULES   │  │   CONSTRAINTS        │ │
│  │             │  │          │  │                       │ │
│  │ working_day │  │ overlap  │  │ no_overlap            │ │
│  │ granularity │  │ conflict │  │ within_bounds         │ │
│  │ priorities  │  │ bounds   │  │ positive_duration     │ │
│  └──────┬──────┘  └────┬─────┘  └───────────┬──────────┘ │
│         │              │                     │             │
│         ▼              ▼                     ▼             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              REASONING ENGINE                        │  │
│  │                                                      │  │
│  │  Meta-Interpreter ← proves goals, returns traces     │  │
│  │  Constraint Solver ← validates all constraints       │  │
│  │  Scoring Engine   ← ranks candidate solutions        │  │
│  │  Custom Operators ← readable KRR syntax              │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│                         ▼                                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │    BLACK BOX SOLVERS (High-Level API)                │  │
│  │                                                      │  │
│  │  handle_add_event/8     → Status, Conflicts, Violations│
│  │  handle_suggest_times/7 → Ranked suggestions + reasons │
│  │  explain_conflicts/6    → Structured explanations      │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
                     Result to Python:
              Status = ok | conflict | invalid
              + Explanations / Suggestions
```

### Key Principle

> **Python is the questioner. Prolog is the reasoner.**
>
> Python sends all necessary data and asks a high-level question ("Can this event be added?").
> Prolog autonomously reasons about constraints, conflicts, and validity — then returns a complete decision.
> Python never calls low-level predicates like `check_conflict` or `valid_placement` directly for main operations.

---

## 2. KRR Concept Checklist

| KRR Concept | Present? | Location | Description |
|---|---|---|---|
| **Fact** | ✅ | `scheduler.pl` §1-2 | Domain knowledge declared as ground truths |
| **Rule** | ✅ | `scheduler.pl` §3 | Inference rules expressed declaratively |
| **Constraint** | ✅ | `scheduler.pl` §2-3, `constraint_solver.pl` §1 | Hard/soft constraints declared as facts |
| **Custom Operator** | ✅ | `scheduler.pl` §6 | `conflicts_with`, `is_valid_in`, `satisfies_all` |
| **Meta-Interpreter** | ✅ | `scheduler.pl` §4, §8 | `demo/1` and `demo_explain/2` |
| **Metadata** | ✅ | `scheduler.pl` §7 | `reasoning_metadata/2` for system introspection |
| **Solver** | ✅ | `scheduler.pl` §9 | Black box solvers for add event, suggest times, explain conflicts |
| **Condition → Action** | ✅ | `scheduler.pl` §9, `constraint_solver.pl` §5 | If-then-else reasoning producing actions/recommendations |

---

## 3. Facts

Facts are **ground truths** about the scheduling domain. They represent **what the system knows** — not how it computes.

### File: `scheduler.pl` — Section 1 & 2

```prolog
%% Domain knowledge about time boundaries
scheduling_fact(working_day_start(6, 0)).      % earliest start: 6:00 AM
scheduling_fact(working_day_end(23, 0)).        % latest end: 11:00 PM
scheduling_fact(slot_granularity(30)).           % 30-minute resolution
scheduling_fact(max_daily_events(8)).            % soft limit

%% Named constraints — declared, not embedded in code
scheduling_fact(constraint(no_overlap)).
scheduling_fact(constraint(within_bounds)).
scheduling_fact(constraint(positive_duration)).
```

### File: `constraint_solver.pl` — Section 1 & 2

```prolog
%% Hard constraints (must hold)
hard_constraint(no_time_overlap).
hard_constraint(within_working_hours).
hard_constraint(positive_duration).

%% Soft constraints (preferences with penalty weights)
soft_constraint(preferred_time_window, 5).
soft_constraint(buffer_proximity, 3).
soft_constraint(daily_overload, 4).

%% Priority knowledge (domain expertise)
priority_knowledge(critical, 10).
priority_knowledge(high, 8).
priority_knowledge(medium, 5).
priority_knowledge(low, 3).
```

### Why this is KRR

Facts separate **knowledge** from **computation**. Adding a new constraint (e.g., `scheduling_fact(constraint(lunch_break))`) only requires adding a fact and its satisfaction rule — no algorithmic code changes needed.

---

## 4. Rules

Rules express **what holds** declaratively — not **how to compute** it.

### File: `scheduler.pl` — Section 2 & 3

```prolog
%% Scheduling rules expressed as knowledge (used by meta-interpreter)
scheduling_rule(
    conflict(S1, E1, S2, E2),
    (S1 < E2, S2 < E1)
).
scheduling_rule(
    within_bounds(Start, End, Min, Max),
    (Start >= Min, End =< Max)
).
scheduling_rule(
    positive_duration(Start, End),
    (End > Start)
).

%% Core declarative rule: two intervals overlap
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.

%% Conflict explanation rule — WHY two intervals conflict
conflict_reason(S1, E1, S2, E2, overlap(S1-E1, S2-E2)) :-
    intervals_overlap(S1, E1, S2, E2).
```

### Why this is KRR

Rules define **logical relationships** between concepts. `intervals_overlap` doesn't "check" anything — it **declares** the mathematical definition of overlap. The Prolog engine infers truth from this declaration.

---

## 5. Constraints

Constraints are **first-class knowledge objects** — they are declared as facts, then reasoned about by generic inference predicates.

### Constraint Declaration (Knowledge)

```prolog
scheduling_fact(constraint(no_overlap)).
scheduling_fact(constraint(within_bounds)).
scheduling_fact(constraint(positive_duration)).
```

### Constraint Satisfaction (Inference)

```prolog
%% Generic constraint checker — dispatches by constraint name
satisfies_constraint(no_overlap, Start, End, Events) :-
    \+ (
        member(event(_, _, SH, SM, EH, EM), Events),
        time_to_minutes(SH, SM, ExStart),
        time_to_minutes(EH, EM, ExEnd),
        intervals_overlap(Start, End, ExStart, ExEnd)
    ).

satisfies_constraint(within_bounds, Start, End, _Events) :-
    scheduling_fact(working_day_start(MinH, MinM)),
    scheduling_fact(working_day_end(MaxH, MaxM)),
    time_to_minutes(MinH, MinM, MinStart),
    time_to_minutes(MaxH, MaxM, MaxEnd),
    Start >= MinStart,
    End =< MaxEnd.

satisfies_constraint(positive_duration, Start, End, _Events) :-
    End > Start.
```

### Valid Placement (Universal Quantification over Constraints)

```prolog
%% A placement is valid iff ALL declared constraints are satisfied
valid_placement(Start, End, Events) :-
    forall(
        scheduling_fact(constraint(C)),
        satisfies_constraint(C, Start, End, Events)
    ).
```

### Hard vs. Soft Constraints (`constraint_solver.pl`)

The constraint solver distinguishes between:

- **Hard constraints** — must hold (e.g., no overlap, positive duration)
- **Soft constraints** — penalize undesirable placements (e.g., suboptimal time, tight buffer)

```prolog
%% Meta-reasoner produces a verdict from constraint analysis
reason_about_constraint(Event, Context, verdict(HardViolations, SoftCost, Recommendation)) :-
    findall(violated(C), (hard_constraint(C), \+ constraint_satisfied(C, Event, Context)), HardViolations),
    total_soft_cost(Event, Context, [], SoftCost),
    (   HardViolations = []
    ->  (SoftCost < 5 -> Recommendation = accept ; Recommendation = accept_with_warning)
    ;   Recommendation = reject
    ).
```

### Why this is KRR

Constraints are **not embedded in code** — they exist as **knowledge** that the system **reasons about**. `valid_placement` doesn't hard-code which constraints to check; it queries the knowledge base with `forall(scheduling_fact(constraint(C)), ...)` and dynamically validates each one.

---

## 6. Custom Operators

Custom operators allow expressing scheduling knowledge in a **natural, domain-close syntax** — like reading English.

### File: `scheduler.pl` — Section 6

```prolog
%% Operator declarations (priority 700, infix, non-associative)
:- op(700, xfx, conflicts_with).
:- op(700, xfx, is_valid_in).
:- op(700, xfx, satisfies_all).
```

### Usage Examples

```prolog
%% "Does event A conflict with event B?"
event(540, 600) conflicts_with event(570, 660).    % 9:00-10:00 vs 9:30-11:00

%% "Is this slot valid in this context?"
slot(9, 0, 10, 0) is_valid_in context(ExistingEvents).

%% "Does this slot satisfy all constraints?"
slot(9, 0, 10, 0) satisfies_all constraints.
```

### Operator Definitions

```prolog
event(S1, E1) conflicts_with event(S2, E2) :-
    intervals_overlap(S1, E1, S2, E2).

slot(SH, SM, EH, EM) is_valid_in context(Events) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    valid_placement(Start, End, Events).

slot(SH, SM, EH, EM) satisfies_all constraints :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    forall(
        scheduling_fact(constraint(C)),
        satisfies_constraint(C, Start, End, [])
    ).
```

### Why this is KRR

Custom operators make the **knowledge representation readable** — close to natural language. Instead of calling `intervals_overlap(540, 600, 570, 660)`, you write `event(540, 600) conflicts_with event(570, 660)`. This is a core KRR principle: knowledge should be **human-readable** and **self-documenting**.

---

## 7. Meta-Interpreter

A meta-interpreter is a program that **interprets itself** — it reasons about goals by proving them against the knowledge base, while being able to **modify or extend** how proof works.

### Basic Meta-Interpreter (`demo/1`)

File: `scheduler.pl` — Section 4

```prolog
demo(true) :- !.
demo((A, B)) :- !, demo(A), demo(B).             % conjunction
demo((A ; B)) :- !, (demo(A) ; demo(B)).          % disjunction
demo(\+ A) :- !, \+ demo(A).                      % negation-as-failure

%% Prove scheduling-specific goals
demo(intervals_overlap(S1, E1, S2, E2)) :- intervals_overlap(S1, E1, S2, E2).
demo(valid_placement(S, E, Evts))       :- valid_placement(S, E, Evts).
demo(satisfies_constraint(C, S, E, Evts)) :- satisfies_constraint(C, S, E, Evts).

%% Prove from declared scheduling rules (stored as knowledge)
demo(Goal) :-
    scheduling_rule(Goal, Body),
    demo(Body).

%% Prove from declared scheduling facts
demo(Goal) :-
    scheduling_fact(Goal).

%% Arithmetic (needed for rule bodies)
demo(A < B) :- A < B.
demo(A > B) :- A > B.
```

### Enhanced Meta-Interpreter with Explanation (`demo_explain/2`)

File: `scheduler.pl` — Section 8

```prolog
demo_explain(true, proved(true)) :- !.

demo_explain((A, B), proved(and(EA, EB))) :-
    !, demo_explain(A, EA), demo_explain(B, EB).

demo_explain(\+ A, proved(negation_as_failure(A))) :-
    !, \+ demo(A).

%% Prove with explanation trace
demo_explain(valid_placement(S, E, Evts),
    proved(valid_placement(all_constraints_satisfied))) :-
    valid_placement(S, E, Evts), !.

demo_explain(valid_placement(S, E, Evts),
    disproved(valid_placement(failed_constraint(C)))) :-
    scheduling_fact(constraint(C)),
    \+ satisfies_constraint(C, S, E, Evts), !.

%% Prove from declared rules
demo_explain(Goal, proved(from_rule(Goal, BodyTrace))) :-
    scheduling_rule(Goal, Body),
    demo_explain(Body, BodyTrace).

%% Prove from declared facts
demo_explain(Goal, proved(from_fact(Goal))) :-
    scheduling_fact(Goal).
```

### Example

```prolog
?- demo_explain(valid_placement(540, 600, []), Trace).
Trace = proved(valid_placement(all_constraints_satisfied)).

?- demo_explain(valid_placement(540, 600, [event("1","Meeting",540,0,600,0)]), Trace).
Trace = disproved(valid_placement(failed_constraint(no_overlap))).
```

### Why this is KRR

The meta-interpreter enables **reasoning about reasoning**:
- `demo/1` proves whether a scheduling goal holds
- `demo_explain/2` proves it AND returns **why** — a structured trace of the proof
- Goals can be proved from `scheduling_rule/2` facts — rules that are themselves stored as **knowledge objects**

This is a hallmark of advanced KRR: the system can **explain its own decisions**.

---

## 8. Metadata (Reasoning Introspection)

Metadata describes **the reasoning system itself** — enabling meta-level queries like "what constraints does this system support?"

### File: `scheduler.pl` — Section 7

```prolog
:- dynamic reasoning_metadata/2.

reasoning_metadata(system_name, schedule_assistant).
reasoning_metadata(reasoning_type, constraint_based).
reasoning_metadata(supported_action, add_event).
reasoning_metadata(supported_action, suggest_times).
reasoning_metadata(supported_action, explain_conflicts).
reasoning_metadata(constraint_type, hard).
reasoning_metadata(constraint_type, soft).
reasoning_metadata(explanation_supported, true).
reasoning_metadata(meta_interpretation, true).
```

### Usage

```prolog
%% "What actions does this system support?"
?- reasoning_metadata(supported_action, Action).
Action = add_event ;
Action = suggest_times ;
Action = explain_conflicts.

%% "Does this system support explanations?"
?- reasoning_metadata(explanation_supported, true).
true.
```

### Why this is KRR

Metadata lets the system **reason about itself**. A front-end or another agent can query the knowledge base to discover what the system is capable of — without hard-coding that information. This supports **extensibility** and **self-description**.

---

## 9. Solvers (Black Box API)

Solvers are **high-level reasoning entry points** that Python calls. They represent the "black box" pattern — Python provides data and a goal; Prolog returns a complete reasoned decision.

### `handle_add_event/8` — "Can I add this event?"

```prolog
handle_add_event(SH, SM, EH, EM, Events, Status, Conflicts, Violations) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    %% Phase 1: Validate constraints (except overlap)
    findall(C,
        (scheduling_fact(constraint(C)), C \= no_overlap,
         \+ satisfies_constraint(C, Start, End, Events)),
        ViolationList),
    (   ViolationList \= []
    ->  Status = invalid, Conflicts = [], Violations = ViolationList
    ;   %% Phase 2: Check overlaps
        findall(conflict(ID, Title, ESH, ESM, EEH, EEM),
            (member(event(ID, Title, ESH, ESM, EEH, EEM), Events),
             time_to_minutes(ESH, ESM, ExStart), time_to_minutes(EEH, EEM, ExEnd),
             intervals_overlap(Start, End, ExStart, ExEnd)),
            ConflictList),
        (   ConflictList = []
        ->  Status = ok, Conflicts = [], Violations = []
        ;   Status = conflict, Conflicts = ConflictList, Violations = []
        )
    ).
```

**Python side** (simplified):
```python
# Python just asks the question — doesn't know HOW Prolog decides
result = prolog.handle_add_event(10, 0, 11, 0, existing_events)
# result.status = 'ok' | 'conflict' | 'invalid'
# result.conflicts = [{"id": ..., "title": ..., ...}]
# result.violations = ["positive_duration", ...]
```

### `handle_suggest_times/7` — "What are the best times?"

Prolog generates candidate slots, validates each against all constraints, scores them using soft constraint reasoning, ranks them, and returns the top 5 with explanations.

### `explain_conflicts/6` — "Why is this time invalid?"

Returns structured explanations: which events overlap, which constraints are violated.

### Why this is KRR

The solver pattern embodies the **core KRR philosophy**:
- Python is the **questioner** — "Can I add this event?"
- Prolog is the **reasoner** — checks constraints, detects conflicts, classifies results
- Python **does not know** which predicates Prolog uses internally
- The separation between knowledge (facts/rules) and reasoning (inference/solvers) is clean

---

## 10. Condition → Action

Prolog's `->` (if-then-else) construct implements **condition-to-action reasoning**: given a condition, choose the appropriate action.

### In `handle_add_event/8`

```prolog
(   ViolationList \= []                           % CONDITION: constraints violated?
->  Status = invalid, ...                          % ACTION: reject with violations
;   (   ConflictList = []                          % CONDITION: any conflicts?
    ->  Status = ok, ...                           % ACTION: approve
    ;   Status = conflict, ...                     % ACTION: report conflicts
    )
)
```

### In `reason_about_constraint/3` (constraint_solver.pl)

```prolog
(   HardViolations = []                            % CONDITION: no hard violations?
->  (   SoftCost < 5                               % CONDITION: low soft cost?
    ->  Recommendation = accept                    % ACTION: accept
    ;   Recommendation = accept_with_warning       % ACTION: accept with warning
    )
;   Recommendation = reject                        % ACTION: reject
)
```

### In `classify_slot_quality/5`

```prolog
classify_slot_quality(Total, _, _, _, ideal_time) :- Total =:= 0, !.
classify_slot_quality(_, BufCost, PrefCost, _, suboptimal_time_and_tight_buffer) :-
    PrefCost > 0, BufCost > 0, !.
classify_slot_quality(_, _, PrefCost, _, outside_preferred_hours) :-
    PrefCost > 0, !.
classify_slot_quality(_, BufCost, _, _, tight_buffer) :-
    BufCost > 0, !.
classify_slot_quality(_, _, _, LoadCost, heavy_day) :-
    LoadCost > 0, !.
classify_slot_quality(_, _, _, _, acceptable).
```

### Why this is KRR

Condition → Action is the reasoning pattern at the **decision level**. The system evaluates conditions (constraint violations, conflict presence, cost thresholds) and maps them to appropriate actions (accept, reject, warn). This is the same pattern used in expert systems and production rule engines.

---

## 11. Dual-Method Architecture

The system uses **two methods** of Python–Prolog interaction:

### Method 1: Direct Calls (Speed-Critical)

Python calls specific low-level Prolog predicates directly. Used for operations where latency matters.

```python
# Direct: Python explicitly calls check_conflict
conflicts = prolog.check_conflict(10, 0, 11, 0, events)
free_slots = prolog.find_free_slots(60, events, 6, 0, 23, 0)
```

**Used for:** `check_conflict`, `find_free_slots`, `find_free_ranges`, `find_free_days`

### Method 2: Black Box (KRR Showcase)

Python sends all data and a high-level goal. Prolog handles all reasoning internally and returns a complete decision with explanations.

```python
# Black box: Python doesn't know how Prolog decides
result = prolog.handle_add_event(10, 0, 11, 0, events)
suggestions = prolog.handle_suggest_times(60, events)
```

**Used for:** `handle_add_event`, `handle_suggest_times`, `explain_conflicts`

### A* Rescheduling (Untouched)

The constraint solver (`constraint_solver.pl`) implements A* search for optimal rescheduling. This is kept as-is because modifying it would change the algorithm's nature.

### Why Both?

| Aspect | Method 1 (Direct) | Method 2 (Black Box) |
|---|---|---|
| **Speed** | Faster (less overhead) | Slightly slower (more reasoning) |
| **KRR Showcase** | Weak (Python orchestrates) | Strong (Prolog reasons autonomously) |
| **Use Case** | Speed-critical sub-queries | Main operations (add, suggest, explain) |
| **Python Role** | Orchestrator | Questioner |
| **Prolog Role** | Utility | Autonomous reasoning agent |

---

## 12. File Map

```
apps/backend/app/chat/prolog/
├── scheduler.pl              ← Main KRR reasoning engine
│   ├── §1  Domain Knowledge (Facts)
│   ├── §2  Scheduling Constraints (Facts + Rules)
│   ├── §3  Core Reasoning Rules (Declarative inference)
│   ├── §4  Meta-Interpreter (demo/1)
│   ├── §5  Legacy Predicates (backward-compatible API)
│   ├── §6  Custom Operators (conflicts_with, is_valid_in, satisfies_all)
│   ├── §7  Reasoning Metadata (system introspection)
│   ├── §8  Enhanced Meta-Interpreter (demo_explain/2 with trace)
│   ├── §9  Black Box Solvers (handle_add_event, handle_suggest_times, explain_conflicts)
│   └── §10 Slot Scoring (soft constraint reasoning)
│
├── constraint_solver.pl      ← A* Rescheduling with KRR
│   ├── §1  Constraint Knowledge Base (hard/soft as facts)
│   ├── §2  Priority Knowledge (domain expertise as facts)
│   ├── §3  Constraint Reasoning (inference over declarations)
│   ├── §4  Soft Cost Reasoning (penalty inference)
│   ├── §5  Meta-Reasoning (reason_about_constraint → verdict)
│   ├── §6  Legacy Predicates (backward-compatible)
│   └── §7  A* Search Engine (optimal rescheduling)

apps/backend/app/chat/
├── prolog_service.py         ← Python ↔ Prolog bridge (pyswip)
│   ├── AddEventResult        — Black box result dataclass
│   ├── TimeSuggestion        — Suggestion result dataclass
│   ├── handle_add_event()    — Method 2: Black box solver call
│   ├── handle_suggest_times()— Method 2: Black box solver call
│   ├── check_conflict()      — Method 1: Direct call
│   ├── find_free_slots()     — Method 1: Direct call
│   └── Python fallbacks      — Backup when Prolog unavailable
│
├── service.py                ← Chat agent state machine
│   ├── _check_and_handle_conflicts()     — Uses Method 2 (black box)
│   ├── _check_edit_conflict_and_apply()  — Uses Method 2 (black box)
│   └── _find_any_free_slots()            — Uses Method 1 (direct, speed)
```

---

## Summary

The Schedule Assistant demonstrates **all core KRR concepts**:

| Concept | Implementation | Purpose |
|---|---|---|
| **Facts** | `scheduling_fact/1`, `hard_constraint/1`, `priority_knowledge/2` | Knowledge representation — ground truths |
| **Rules** | `scheduling_rule/2`, `intervals_overlap/4`, `conflict_reason/5` | Declarative inference — what holds |
| **Constraints** | `satisfies_constraint/4`, `valid_placement/3`, hard/soft distinction | Constraint satisfaction — what's valid |
| **Custom Operators** | `conflicts_with`, `is_valid_in`, `satisfies_all` | Readable domain-specific syntax |
| **Meta-Interpreter** | `demo/1`, `demo_explain/2` | Reasoning about reasoning + explanation traces |
| **Metadata** | `reasoning_metadata/2` | System self-description and introspection |
| **Solvers** | `handle_add_event/8`, `handle_suggest_times/7`, `explain_conflicts/6` | Black box autonomous reasoning |
| **Condition → Action** | `->` patterns in solvers, `classify_slot_quality/5`, `reason_about_constraint/3` | Decision-making from conditions |

The architecture achieves **Python as questioner, Prolog as reasoner** — the gold standard for KRR demonstration.
