# KRR Refactoring: Before & After Comparison

## Knowledge Representation and Reasoning (KRR) Transformation

### Schedule Assistant — Prolog Architecture

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background & Motivation](#2-background--motivation)
3. [Architecture Overview](#3-architecture-overview)
4. [File-by-File Comparison](#4-file-by-file-comparison)
   - [kb.pl — Knowledge Base](#41-kbpl--knowledge-base)
   - [rules.pl — Reasoning Rules](#42-rulespl--reasoning-rules)
   - [main.pl — API Layer](#43-mainpl--api-layer)
   - [scheduler.pl — Scheduling Engine](#44-schedulerpl--scheduling-engine)
   - [constraint_solver.pl — Constraint Solver](#45-constraint_solverpl--constraint-solver)
5. [KRR Concepts Applied](#5-krr-concepts-applied)
6. [Meta-Reasoning & Meta-Interpretation](#6-meta-reasoning--meta-interpretation)
7. [Integration Compatibility](#7-integration-compatibility)
8. [References](#8-references)

---

## 1. Executive Summary

This document describes the transformation of the Schedule Assistant's Prolog subsystem from a **procedural/algorithmic** style into a **Knowledge-Based Reasoning Engine** following Knowledge Representation and Reasoning (KRR) principles.

### What Changed

| Aspect | Before | After |
|--------|--------|-------|
| **Knowledge** | Embedded in predicate bodies | Declared as first-class facts |
| **Constraints** | Hard-coded `if-then` checks | Named constraint facts + inference rules |
| **Reasoning** | Procedural step-by-step execution | Declarative inference over knowledge |
| **Meta-level** | None | `demo/1` meta-interpreter, `explain/2` proof traces |
| **Queries** | "Run scheduler" | `conflict(E1, E2)`, `valid_schedule(E, T)`, `find_available_slot(E, T)` |
| **Priority** | Numeric parameter in calculations | Domain knowledge with classification rules |
| **Taxonomy** | None | `event_category/2`, `is_a/2` with transitive closure |

### What Did NOT Change

- All existing predicate signatures preserved
- Python ↔ Prolog communication unchanged
- `PrologService` (pyswip) and `PrologClient` (subprocess) untouched
- All legacy API predicates still work

---

## 2. Background & Motivation

### The Problem

The original Prolog code used Prolog as a **scripting language** — predicates simulated step-by-step algorithms rather than leveraging Prolog's natural strengths in knowledge representation, logical inference, and constraint satisfaction.

**Symptoms of procedural Prolog:**
- Constraints were embedded inside predicate bodies (not queryable)
- No separation between "what is known" and "how to reason"
- No ability to ask declarative queries like "is this schedule valid?"
- Priority was a number passed through calculations, not domain knowledge

### The Goal

Transform the system into one where:
- **Knowledge is declared** — facts represent domain expertise
- **Rules express relationships** — not procedures
- **Queries infer answers** — not compute them step-by-step
- **Constraints are first-class citizens** — named, queryable, extensible

This follows principles from agent-based reasoning systems (Oliveira & Bazzan, 2006) and meta-reasoning approaches for knowledge-based systems (Mei et al., 2014), where:
- Domain knowledge is **separated** from inference mechanisms
- A **meta-level** can reason about object-level rules
- Constraints are **declared** and **checked** by a generic engine

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────┐
│                   Python Layer                    │
│   (FastAPI, PrologService, PrologClient)          │
│   Role: Interface ONLY — no reasoning logic       │
└────────────┬───────────────────┬─────────────────┘
             │ pyswip            │ subprocess
             ▼                   ▼
┌────────────────────┐  ┌──────────────────────────┐
│  Prolog (pyswip)   │  │   Prolog (standalone)     │
│  scheduler.pl      │  │   kb.pl                   │
│  constraint_solver │  │   rules.pl                │
│  .pl               │  │   main.pl                 │
│                    │  │                            │
│  ┌──────────────┐  │  │  ┌──────────────────────┐ │
│  │ KNOWLEDGE    │  │  │  │ KNOWLEDGE             │ │
│  │ • facts      │  │  │  │ • facts + taxonomy    │ │
│  │ • constraints│  │  │  │ • constraint decls    │ │
│  │ • priorities │  │  │  │ • availability windows│ │
│  ├──────────────┤  │  │  ├──────────────────────┤ │
│  │ REASONING    │  │  │  │ REASONING             │ │
│  │ • inference  │  │  │  │ • conflict detection  │ │
│  │ • constraint │  │  │  │ • valid_schedule      │ │
│  │   checking   │  │  │  │ • find_available_slot │ │
│  ├──────────────┤  │  │  ├──────────────────────┤ │
│  │ META-LEVEL   │  │  │  │ META-LEVEL            │ │
│  │ • demo/1     │  │  │  │ • demo/1 + explain/2  │ │
│  │ • verdicts   │  │  │  │ • proof traces        │ │
│  └──────────────┘  │  │  └──────────────────────┘ │
└────────────────────┘  └──────────────────────────┘
```

---

## 4. File-by-File Comparison

### 4.1 `kb.pl` — Knowledge Base

#### BEFORE: Flat data store

```prolog
%% Only stored events as flat records
:- dynamic event/7.

%% Sample data — no classification, no taxonomy
event(1, 'Morning Meeting', 9, 0, 10, 0, 'work').
event(2, 'Lunch Break', 12, 0, 13, 0, 'personal').

%% CRUD operations — procedural add/remove/update
add_event(Id, Title, SH, SM, EH, EM, Type) :-
    assert(event(Id, Title, SH, SM, EH, EM, Type)).
```

**Problem:** Knowledge about events (what types exist, how they relate, what constraints apply) was nowhere in the knowledge base. The KB was just a data table.

#### AFTER: Rich knowledge representation

```prolog
%% === Taxonomic Knowledge ===
event_category(work, [meeting, presentation, review, standup]).
event_category(personal, [exercise, meal, errand, hobby]).
event_category(academic, [lecture, lab, study_group, exam]).

%% === Constraint Declarations as Facts ===
scheduling_constraint(no_overlap).
scheduling_constraint(within_hours).
scheduling_constraint(max_daily_events).

constraint_applies_to(no_overlap, all_events).
constraint_applies_to(within_hours, work).
constraint_applies_to(max_daily_events, all_events).

%% === Priority Knowledge ===
priority_level(critical, 5).
priority_level(high, 4).
priority_level(medium, 3).
priority_level(low, 2).
priority_level(optional, 1).

default_priority(work, high).
default_priority(personal, medium).
default_priority(academic, high).

%% === Availability Windows ===
user_available(default, weekday, 8, 22).
user_available(default, weekend, 10, 20).

%% === Day Type Knowledge ===
day_type(monday, weekday).
day_type(saturday, weekend).
...
```

**What changed:**
- Event types are organized into a **taxonomy** (`event_category/2`)
- Constraints are **declared as facts**, not embedded in code
- Priority is **domain knowledge**, not just a number
- Availability windows are **queryable facts**

---

### 4.2 `rules.pl` — Reasoning Rules

#### BEFORE: Placeholder logic

```prolog
%% check_conflicts — procedural iteration
check_conflicts(Id, Conflicts) :-
    event(Id, _, SH, SM, EH, EM, _),
    findall(CId, (
        event(CId, _, CSH, CSM, CEH, CEM, _),
        CId \= Id,
        time_to_minutes(SH, SM, Start),
        time_to_minutes(EH, EM, End),
        time_to_minutes(CSH, CSM, CStart),
        time_to_minutes(CEH, CEM, CEnd),
        CStart < End, Start < CEnd
    ), Conflicts).

%% find_free_slots — STUB (returned empty list!)
find_free_slots(_, _, _, []).
```

**Problem:**
- `check_conflicts` was a **procedure**: "iterate through events, compute overlaps, collect results"
- `find_free_slots` was a **placeholder** that returned nothing
- No concept of "is this schedule valid?" — only "run the conflict checker"

#### AFTER: Declarative reasoning with inference

```prolog
%% === Conflict as a Relationship (not a procedure) ===
conflict(EventId1, EventId2) :-
    event(EventId1, _, S1H, S1M, E1H, E1M, _),
    event(EventId2, _, S2H, S2M, E2H, E2M, _),
    EventId1 \= EventId2,
    time_overlap(S1H, S1M, E1H, E1M, S2H, S2M, E2H, E2M).

%% === Schedule Validity as an Inference ===
valid_schedule(EventId, Day, Reason) :-
    event(EventId, _, SH, SM, EH, EM, Type),
    %% Check all declared constraints
    all_constraints_hold(EventId, Day, Reason).

valid_schedule(EventId, Day, valid) :-
    event(EventId, _, _, _, _, _, _),
    \+ (scheduling_constraint(C),
        constraint_applies(C, EventId),
        \+ constraint_holds(C, EventId, Day)).

%% === Constraint Checking via Inference ===
constraint_holds(no_overlap, EventId, _Day) :-
    \+ (conflict(EventId, _OtherId)).

constraint_holds(within_hours, EventId, Day) :-
    event(EventId, _, SH, SM, EH, EM, _),
    available_at(Day, SH, SM),
    available_at(Day, EH, EM).

%% === Slot Finding via Reasoning (was placeholder!) ===
find_available_slot(Type, Day, Duration, slot(H, M, EH, EM)) :-
    user_available(default, DayType, AvailStart, AvailEnd),
    day_type(Day, DayType),
    between(AvailStart, AvailEnd, H),
    member(M, [0, 30]),
    time_to_minutes(H, M, StartMin),
    EndMin is StartMin + Duration,
    EndMin =< AvailEnd * 60,
    minutes_to_time(EndMin, EH, EM),
    \+ slot_conflicts(H, M, EH, EM).

%% === Priority Comparison via Knowledge ===
higher_priority(Event1, Event2) :-
    effective_priority(Event1, P1),
    effective_priority(Event2, P2),
    P1 > P2.

%% === Taxonomic Reasoning ===
is_a(SubType, SuperType) :-
    event_category(SuperType, SubTypes),
    member(SubType, SubTypes).
is_a(SubType, SuperType) :-
    event_category(MidType, SubTypes),
    member(SubType, SubTypes),
    is_a(MidType, SuperType).

%% === Meta-Interpreter ===
demo(true) :- !.
demo((A, B)) :- !, demo(A), demo(B).
demo(conflict(X, Y)) :- conflict(X, Y).
demo(valid_schedule(E, D, R)) :- valid_schedule(E, D, R).
demo(higher_priority(X, Y)) :- higher_priority(X, Y).
...

%% === Proof Explanation ===
explain(conflict(X, Y), 'Events X and Y have overlapping time windows') :-
    conflict(X, Y).
explain(valid_schedule(E, D, valid), Reason) :-
    valid_schedule(E, D, valid),
    format(atom(Reason), 'Event ~w satisfies all constraints for ~w', [E, D]).
```

**Key differences:**

| Before | After |
|--------|-------|
| `check_conflicts(Id, List)` — procedure | `conflict(E1, E2)` — relationship |
| `find_free_slots(_, _, _, [])` — stub | `find_available_slot(Type, Day, Dur, Slot)` — inference |
| No validity concept | `valid_schedule(E, Day, Reason)` — declarative query |
| No priority reasoning | `higher_priority(E1, E2)` — inferred from knowledge |
| No taxonomy | `is_a/2` with transitive closure |
| No meta-level | `demo/1` + `explain/2` |

---

### 4.3 `main.pl` — API Layer

#### BEFORE: Simple re-exports

```prolog
:- use_module(kb).
:- use_module(rules).
%% Only re-exported existing predicates
%% No reasoning-oriented API
```

#### AFTER: Reasoning API entry points

```prolog
%% === Reasoning API ===

%% Find all conflicts for an event
api_find_conflicts(EventId, Conflicts) :-
    findall(conflict(EventId, OtherId), conflict(EventId, OtherId), Conflicts).

%% Check if a schedule is valid
api_valid_schedule(EventId, Day, Result) :-
    valid_schedule(EventId, Day, Result).

%% Find available slots
api_available_slots(Type, Day, Duration, Slots) :-
    findall(Slot, find_available_slot(Type, Day, Duration, Slot), Slots).

%% Compare priorities
api_compare_priority(Event1, Event2, Result) :-
    (higher_priority(Event1, Event2) -> Result = higher
    ; higher_priority(Event2, Event1) -> Result = lower
    ; Result = equal).

%% Explain reasoning
api_explain(Query, Explanation) :-
    explain(Query, Explanation).

%% Meta-interpreter access
api_demo(Goal, Result) :-
    (demo(Goal) -> Result = proved ; Result = not_proved).
```

**Key difference:** The API now supports **reasoning queries** ("is this valid?", "why does this conflict?") rather than only CRUD operations.

---

### 4.4 `scheduler.pl` — Scheduling Engine (pyswip path)

#### BEFORE: Algorithmic time manipulation

```prolog
%% find_free_slots — procedural gap-finding algorithm
find_free_slots(Events, StartH, StartM, EndH, EndM, FreeSlots) :-
    %% Sort events, walk through timeline, collect gaps
    sort_events_by_start(Events, Sorted),
    find_gaps(Sorted, StartH, StartM, EndH, EndM, FreeSlots).
```

**Problem:** The scheduler was a **procedure** that walked a sorted list and computed gaps — pure algorithm, no knowledge representation.

#### AFTER: Knowledge-aware scheduling with reasoning

```prolog
%% === Scheduling Knowledge as Facts ===
scheduling_fact(working_hours(6, 0, 23, 0)).
scheduling_fact(min_event_duration(15)).
scheduling_fact(default_buffer(5)).
scheduling_fact(max_events_per_day(12)).

%% === Scheduling Rules as Declarations ===
scheduling_rule(no_overlap, 'Events must not overlap in time').
scheduling_rule(within_bounds, 'Events must be within working hours').
scheduling_rule(positive_duration, 'End time must be after start time').

%% === Declarative Placement Validity ===
valid_placement(event(ID, Title, SH, SM, EH, EM), OtherEvents, Status) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    (   End =< Start
    ->  Status = invalid(zero_duration)
    ;   scheduling_fact(working_hours(WS_H, WS_M, WE_H, WE_M)),
        time_to_minutes(WS_H, WS_M, WorkStart),
        time_to_minutes(WE_H, WE_M, WorkEnd),
        (   Start < WorkStart ; End > WorkEnd
        ->  Status = invalid(outside_hours)
        ;   (   slot_conflicts_with_events(SH-SM, EH-EM, OtherEvents)
            ->  Status = invalid(overlap)
            ;   Status = valid
            )
        )
    ).

%% === Constraint Satisfaction via Inference ===
satisfies_constraint(no_overlap, event(_, _, SH, SM, EH, EM), Events, Result) :-
    (slot_conflicts_with_events(SH-SM, EH-EM, Events)
    -> Result = violated ; Result = satisfied).

satisfies_constraint(within_bounds, event(_, _, SH, SM, EH, EM), _, Result) :-
    scheduling_fact(working_hours(WS_H, WS_M, WE_H, WE_M)),
    time_to_minutes(SH, SM, Start), time_to_minutes(EH, EM, End),
    time_to_minutes(WS_H, WS_M, WStart), time_to_minutes(WE_H, WE_M, WEnd),
    (Start >= WStart, End =< WEnd -> Result = satisfied ; Result = violated).

%% === Meta-Interpreter for Scheduling Reasoning ===
demo(true) :- !.
demo((A, B)) :- !, demo(A), demo(B).
demo(valid_placement(E, Evts, S)) :- valid_placement(E, Evts, S).
demo(satisfies_constraint(C, E, Evts, R)) :- satisfies_constraint(C, E, Evts, R).
...
```

**Key difference:** Scheduling decisions are now made by **querying the knowledge base** (scheduling_fact, scheduling_rule) and **inferring** validity, rather than executing a procedural algorithm.

---

### 4.5 `constraint_solver.pl` — Constraint Solver

#### BEFORE: Hard-coded constraint checks

```prolog
%% Constraints were EMBEDDED in predicate bodies
validate_hard_constraints(Event, AllEvents, Violations) :-
    %% Procedural: check overlap, check hours, check duration
    findall(Violation, (
        (overlap_check... ; hours_check... ; duration_check...),
    ), Violations).

%% Soft costs were COMPUTED, not inferred
calculate_soft_cost(Event, AllEvents, Prefs, Cost) :-
    preferred_time_cost(Type, Start, End, Prefs, C1),
    buffer_proximity_cost(Start, End, AllEvents, C2),
    daily_overload_cost(AllEvents, C3),
    priority_scheduling_cost(Priority, Start, C4),
    Cost is C1 + C2 + C3 + C4.

%% Strategy was a simple parameter, not knowledge
strategy_weight(minimize_moves, 0.5).
strategy_weight(maximize_quality, 2.0).
strategy_weight(balanced, 1.0).
```

**Problem:**
- Constraint names like `no_time_overlap` were not queryable — they were just comments
- Adding a new constraint required modifying predicate bodies
- No way to ask "which constraints are violated?" generically
- No meta-reasoning about constraint importance

#### AFTER: Constraints as first-class knowledge

```prolog
%% === Constraint Knowledge Base ===
:- dynamic hard_constraint/1.
:- dynamic soft_constraint/2.

%% Hard Constraints — declared as facts
hard_constraint(no_time_overlap).
hard_constraint(within_working_hours).
hard_constraint(positive_duration).

%% Soft Constraints — with penalty weights
soft_constraint(preferred_time_window, 5).
soft_constraint(buffer_proximity, 3).
soft_constraint(daily_overload, 4).
soft_constraint(priority_scheduling, 2).

%% === Priority Knowledge ===
priority_knowledge(critical, 10).
priority_knowledge(high, 8).
priority_knowledge(medium, 5).
priority_knowledge(low, 3).
priority_knowledge(optional, 1).

%% Classification rules (priority → class)
event_priority_class(P, critical, 'Must not be moved') :- P >= 9.
event_priority_class(P, high, 'Prefer not to move') :- P >= 7, P < 9.
event_priority_class(P, medium, 'Can be moved') :- P >= 4, P < 7.
...

%% === Constraint Reasoning via Inference ===

%% Generic inference: does a named constraint hold?
constraint_satisfied(no_time_overlap, Event, context(AllEvents)) :-
    %% Infers: no other event overlaps with this one
    \+ (member(Other, AllEvents), overlaps(Event, Other)).

constraint_satisfied(within_working_hours, Event, _Context) :-
    %% Infers: event is within 6:00–23:00
    event_start_end(Event, Start, End),
    Start >= 360, End =< 1380.

%% All hard constraints must hold (generic inference)
all_hard_constraints_met(Event, Context) :-
    forall(hard_constraint(C), constraint_satisfied(C, Event, Context)).

%% === Soft Cost Inference ===
%% Each soft constraint has an inference rule for its cost
soft_cost_for(preferred_time_window, Event, Context, Cost) :- ...
soft_cost_for(buffer_proximity, Event, Context, Cost) :- ...

%% Total soft cost: sum of weighted constraint costs (generic)
total_soft_cost(Event, Context, Prefs, Total) :-
    findall(WC, (
        soft_constraint(Name, Weight),
        soft_cost_for(Name, Event, Context, Raw),
        WC is Raw * Weight / 5
    ), Costs),
    sum_list(Costs, Total).

%% === Meta-Reasoning: Reason About Constraints ===
reason_about_constraint(Event, Context, verdict(Violations, Cost, Action)) :-
    findall(violated(C),
        (hard_constraint(C), \+ constraint_satisfied(C, Event, Context)),
        Violations),
    total_soft_cost(Event, Context, [], Cost),
    (Violations = [] ->
        (Cost < 5 -> Action = accept ; Action = accept_with_warning)
    ;   Action = reject).

%% === Meta-Interpreter ===
demo(true) :- !.
demo((A, B)) :- !, demo(A), demo(B).
demo(constraint_satisfied(C, E, Ctx)) :- constraint_satisfied(C, E, Ctx).
demo(all_hard_constraints_met(E, Ctx)) :- all_hard_constraints_met(E, Ctx).
demo(reason_about_constraint(E, Ctx, V)) :- reason_about_constraint(E, Ctx, V).
...
```

**Key differences:**

| Before | After |
|--------|-------|
| Constraints embedded in code | Constraints are named **facts** |
| Adding constraint = modify predicate | Adding constraint = add a fact + inference rule |
| `validate_hard_constraints` — procedure | `all_hard_constraints_met` — generic inference |
| `calculate_soft_cost` — fixed formula | `total_soft_cost` — sums over declared constraints |
| No meta-reasoning | `reason_about_constraint` produces verdicts |
| No meta-interpreter | `demo/1` proves goals against KB |
| Priority = number | Priority = knowledge with classification |

---

## 5. KRR Concepts Applied

### 5.1 Knowledge Representation

| Concept | Implementation |
|---------|---------------|
| **Facts** | `event/7`, `event_category/2`, `priority_level/2`, `hard_constraint/1`, `soft_constraint/2`, `user_available/4`, `scheduling_fact/1` |
| **Rules** | `conflict/2`, `valid_schedule/3`, `constraint_holds/3`, `constraint_satisfied/3`, `higher_priority/2` |
| **Constraints** | Named facts checked by generic inference engine |
| **Taxonomy** | `event_category/2` + `is_a/2` with transitive closure |
| **Domain Knowledge** | `priority_knowledge/2`, `event_priority_class/3`, `default_priority/2` |

### 5.2 Reasoning Patterns

| Pattern | Example |
|---------|---------|
| **Inference** | `conflict(E1, E2)` infers overlap from event facts |
| **Constraint Satisfaction** | `all_constraints_hold(Event, Day, Reason)` checks all declared constraints |
| **Classification** | `event_priority_class(8, high, 'Prefer not to move')` classifies by rules |
| **Transitive Closure** | `is_a(meeting, work)` via `is_a(meeting, work) :- event_category(work, [..., meeting, ...])` |
| **Negation as Failure** | `constraint_holds(no_overlap, E, D) :- \+ conflict(E, _)` |
| **Abductive Reasoning** | `find_available_slot/4` — "what slot would satisfy all constraints?" |

### 5.3 Declarative vs. Procedural

**Procedural (Before):**
```prolog
%% "Do step 1, then step 2, then step 3..."
schedule_event(Event) :-
    check_overlap(Event, Result1),
    check_hours(Event, Result2),
    check_duration(Event, Result3),
    combine_results([Result1, Result2, Result3], Final).
```

**Declarative (After):**
```prolog
%% "An event is valid if all constraints hold"
valid_schedule(EventId, Day, valid) :-
    \+ (scheduling_constraint(C),
        constraint_applies(C, EventId),
        \+ constraint_holds(C, EventId, Day)).
```

The declarative version:
- Doesn't prescribe an order
- Automatically adapts when new constraints are added
- Can be queried in both directions ("is this valid?" / "why is this invalid?")

---

## 6. Meta-Reasoning & Meta-Interpretation

### 6.1 Meta-Interpreter (`demo/1`)

Inspired by meta-reasoning approaches in knowledge-based systems (Mei et al., 2014), we introduced a lightweight meta-interpreter that can **prove goals** against the knowledge base.

```prolog
%% Object-level: prove goals
demo(true) :- !.
demo((A, B)) :- !, demo(A), demo(B).
demo(conflict(X, Y)) :- conflict(X, Y).
demo(valid_schedule(E, D, R)) :- valid_schedule(E, D, R).
```

**Why this matters:**
- Allows the system to **reason about its own reasoning**
- Enables proof tracing and explanation generation
- Follows the meta-reasoning pattern from the SWRL ontology paper, where a meta-level interprets object-level rules

### 6.2 Proof Explanation (`explain/2`)

```prolog
explain(conflict(X, Y), Explanation) :-
    conflict(X, Y),
    event(X, T1, _, _, _, _, _),
    event(Y, T2, _, _, _, _, _),
    format(atom(Explanation),
        'Events "~w" and "~w" have overlapping time windows', [T1, T2]).
```

This transforms the system from a black-box scheduler into an **explainable** reasoning system.

### 6.3 Meta-Reasoning for Constraints (`reason_about_constraint/3`)

In the constraint solver, the meta-reasoner examines all constraints and produces a **verdict**:

```prolog
reason_about_constraint(Event, Context, verdict(HardViolations, SoftCost, Recommendation)) :-
    findall(violated(C),
        (hard_constraint(C), \+ constraint_satisfied(C, Event, Context)),
        HardViolations),
    total_soft_cost(Event, Context, [], SoftCost),
    (HardViolations = [] ->
        (SoftCost < 5 -> Recommendation = accept ; Recommendation = accept_with_warning)
    ;   Recommendation = reject).
```

This is analogous to the agent approach in intelligent systems (Oliveira & Bazzan, 2006), where an agent evaluates the current state against a knowledge base to determine the best action.

---

## 7. Integration Compatibility

### Python ↔ Prolog Interface (Unchanged)

| Component | Role | Status |
|-----------|------|--------|
| `PrologService` (pyswip) | Calls `scheduler.pl` + `constraint_solver.pl` | ✅ Unchanged |
| `PrologClient` (subprocess) | Calls `main.pl` → `kb.pl` + `rules.pl` | ✅ Unchanged |
| All legacy predicates | Original signatures preserved | ✅ Backward compatible |
| New KRR predicates | Additional exports | ✅ Additive only |

### How Legacy Predicates Now Use KRR

Legacy predicates like `validate_hard_constraints/3` now **delegate** to the KRR layer internally:

```
validate_hard_constraints(Event, AllEvents, Violations)
   └── calls constraint_satisfied(no_time_overlap, Event, context(AllEvents))
   └── calls constraint_satisfied(within_working_hours, Event, context(AllEvents))
   └── calls constraint_satisfied(positive_duration, Event, context(AllEvents))
```

The external interface is identical, but internally the system now uses declarative constraint inference instead of procedural checks.

---

## 8. References

1. **Oliveira, D. & Bazzan, A.L.C.** (2006). "An Agent Approach for Intelligent Traffic-Light Control." — Demonstrates agent-based reasoning over domain knowledge, where agents evaluate environmental state against rules to make decisions. Applied here: scheduling agents query constraint knowledge to make placement decisions.

2. **Mei, J., Bontas, E.P., & Lin, Z.** (2014). "A Meta-reasoning Approach for Reasoning with SWRL Ontologies." — Proposes a meta-level interpreter that reasons over object-level rules in knowledge bases. Applied here: `demo/1` meta-interpreter proves scheduling goals, and `explain/2` traces the reasoning process.

3. **Bratko, I.** (2012). *Prolog Programming for Artificial Intelligence* (4th ed.). — Standard reference for KRR patterns in Prolog including meta-interpreters, constraint representation, and declarative programming.

4. **Sterling, L. & Shapiro, E.** (1994). *The Art of Prolog* (2nd ed.). — Foundation for meta-programming patterns, knowledge representation using facts and rules, and the separation of knowledge from control.

---

*Document generated as part of the KRR refactoring of the Schedule Assistant project.*
*All changes preserve backward compatibility with existing Python integration.*
