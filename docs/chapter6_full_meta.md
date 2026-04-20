# Chapter 6

# Knowledge Representation and Reasoning Techniques

**Schedule Assistant Project — Full Meta-Interpreter Edition**

---

## 6.1 Overview and Guiding Principle

### 6.1.1 Separation of Knowledge from Control

The Prolog subsystem of the Schedule Assistant is built on the fundamental KRR principle of **separating knowledge from control**:

- **Knowledge** — what the system knows — is encoded as Prolog **facts**, **rules**, **constraints**, and **metadata**. These are *purely declarative*: they state what is true, not how to prove it.
- **Control** — how the system reasons — is centralised in two mechanisms:
  - The **full meta-interpreter** (`demo/1` with `clause/2`), which makes every resolution step explicit and controllable.
  - The **solver** (`solve/2`), which orchestrates multi-step reasoning and routes domain sub-goals through `demo/1`.

This separation means the knowledge base can be understood, modified, and audited without touching the reasoning engine, and the reasoning engine can be upgraded or instrumented without changing any domain knowledge.

### 6.1.2 Six-Layer Architecture

The system organises all KRR capabilities into a layered architecture, used consistently in both `schedule.pl` (scheduling logic) and `constraint_solve.pl` (constraint and A* optimisation):

| Layer | Name | Content |
|-------|------|---------|
| Layer 0 | Custom Operators | Domain-specific syntax: `overlaps_with`, `is_free_during`, `conflicts_with`, `violates`, `satisfies`, `penalized_by` |
| Layer 1 | Facts (KB) | Ground terms: domain constants, preferred windows, strategy weights, metadata (statement/3, rule/3) |
| Layer 2 | Rules (Inference) | Clauses that derive new knowledge from Layer 1 facts (all declared `:- dynamic`) |
| Layer 3 | Constraints | First-class constraint objects (hard + soft), checked through `demo/1` |
| Layer 4 | **Full Meta-Interpreter** | `demo/1` with `clause/2` core — transparent, traceable resolution of all domain predicates |
| Layer 5 | Solver | `solve/2` — central entry point; all domain goals go through `demo/1` |

### 6.1.3 What Makes This KRR

The Prolog subsystem qualifies as a Knowledge Representation and Reasoning system because:

1. **Explicit Knowledge** — Every piece of scheduling domain knowledge (overlap rules, constraint definitions, cost formulas) is a named, self-describing Prolog clause.
2. **Inference** — The system derives conclusions (conflicts, valid slots, costs) from knowledge using logical inference rules, not hardcoded if/else chains.
3. **Separation** — Knowledge (Layers 1–3) is cleanly separated from reasoning (Layers 4–5).
4. **Transparency** — The full meta-interpreter makes every resolution step visible to the program itself, enabling proof tracing, depth limiting, and explanation generation.
5. **Constraints as First-Class Objects** — Constraints are named, parameterised objects that the meta-interpreter reasons over — not opaque procedure calls.
6. **Self-Description** — `statement/3` and `rule/3` metadata terms allow the system to reason about its own knowledge.

---

## 6.2 Knowledge Representation — How Facts Are Encoded

### 6.2.1 Event Representation

Each calendar event is represented as an eight-argument Prolog compound term:

```prolog
event(Id, Title, StartHour, StartMinute, EndHour, EndMinute, Priority, Type)
```

| Field | Type | Range | Example |
|-------|------|-------|---------|
| Id | atom/string | unique | `"evt_abc123"` |
| Title | atom/string | any | `"Team Meeting"` |
| StartHour | integer | 0–23 | 9 |
| StartMinute | integer | 0–59 | 30 |
| EndHour | integer | 0–23 | 11 |
| EndMinute | integer | 0–59 | 0 |
| Priority | integer | 1–10 | 7 |
| Type | atom | predefined set | meeting, study, exercise, exam, personal |

### 6.2.2 Time Domain

Times are represented in two coordinate systems:

| Representation | Format | Range | Use |
|---------------|--------|-------|-----|
| Hour:Minute | (H, M) two integers | 0:00 – 23:59 | Human-facing API parameters |
| Minutes from midnight | single integer | 0 – 1439 | All internal arithmetic |

Conversion rules (Layer 2, declared `:- dynamic` for clause/2 access):

```prolog
time_to_minutes(Hour, Minute, Total) :-
    integer(Hour), Hour >= 0, Hour =< 23,
    integer(Minute), Minute >= 0, Minute =< 59,
    Total is Hour * 60 + Minute.

minutes_to_time(Total, Hour, Minute) :-
    integer(Total), Total >= 0, Total =< 1439,
    Hour is Total // 60,
    Minute is Total mod 60.
```

### 6.2.3 Layer 1 Facts

Ground knowledge constants stored as `fact/2` terms:

**schedule.pl facts:**

```prolog
fact(minutes_in_day, 1440).
fact(slot_granularity, 30).
fact(max_candidate_iterations, 1000).
```

**constraint_solve.pl facts:**

```prolog
fact(working_hours_start, 360).    %% 6:00 AM
fact(working_hours_end,   1380).   %% 11:00 PM
fact(min_buffer_minutes, 15).
fact(daily_soft_limit, 6).
fact(daily_hard_limit, 8).
fact(slot_step, 30).
fact(max_slot_candidates, 100).
fact(move_penalty, 3).
fact(shift_weight, 2).
fact(priority_factor, 0.5).
```

### 6.2.4 Priority Knowledge Base

```prolog
strategy_weight(minimize_moves,   0.5).
strategy_weight(maximize_quality, 2.0).
strategy_weight(balanced,         1.0).

preferred_window(meeting,  540, 1020).
preferred_window(study,    480,  720).
preferred_window(study,    840, 1080).
preferred_window(exercise, 360,  480).
preferred_window(exercise, 1020, 1380).

preference_penalty(meeting,  10).
preference_penalty(study,     5).
preference_penalty(exercise,  3).
```

---

## 6.3 Metadata — Self-Describing Knowledge

Every fact, rule, and constraint has metadata describing its name, category, and purpose:

### 6.3.1 statement/3

```prolog
statement(Name, Category, Description).
```

| Name | Category | Description |
|------|----------|-------------|
| minutes_in_day | domain_constant | 'Total minutes in a day (0–1439)' |
| slot_granularity | domain_constant | 'Granularity for candidate slot generation' |
| overlap_rule | inference_rule | 'Two intervals overlap iff S1 < E2 and S2 < E1' |
| free_slot_rule | inference_rule | 'A slot is free iff it conflicts with no event' |
| no_overlap | constraint / hard_constraint | 'A new event must not overlap existing events' |
| within_bounds | constraint | 'A slot must lie within [MinStart, MaxEnd]' |
| positive_duration | constraint / hard_constraint | 'End time must be strictly after start time' |
| preferred_time | soft_constraint | 'Events should be in their preferred window' |
| buffer_proximity | soft_constraint | 'Events should have buffer gaps between them' |

### 6.3.2 rule/3

Links rule names to their head predicate and a human-readable explanation:

```prolog
rule(overlap_rule,
     intervals_overlap(_S1, _E1, _S2, _E2),
     'True when two time intervals share at least one common point').

rule(displacement_cost_rule,
     calculate_displacement_cost(_Orig, _Mod, _Cost),
     'g(n): actual cost of moving events from original positions').

rule(heuristic_rule,
     calculate_heuristic(_Orig, _Curr, _Rem, _Strat, _F),
     'f(n) = g(n) + h(n): A* evaluation function').
```

This metadata enables introspection — the system can enumerate all its own rules and constraints dynamically.

---

## 6.4 Custom Operators

Domain-specific operators improve readability:

**schedule.pl operators:**

```prolog
:- op(700, xfx, overlaps_with).
:- op(700, xfx, is_free_during).
:- op(700, xfx, conflicts_with).
:- op(600, xfx, to).
```

**constraint_solve.pl operators:**

```prolog
:- op(700, xfx, violates).
:- op(700, xfx, satisfies).
:- op(700, xfx, penalized_by).
```

These operators allow writing scheduling logic in near-English syntax:

```prolog
interval(480, 540) overlaps_with interval(510, 600).    %% true
slot(480, 540) is_free_during [].                       %% true (no events)
Event satisfies no_overlap.                             %% hard constraint check
Event penalized_by soft(preferred_time, Cost).          %% soft cost query
```

---

## 6.5 Logical Reasoning and Inference Rules

### 6.5.1 Conflict Detection (FOL)

The core scheduling inference: two time intervals conflict iff they overlap:

```prolog
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.
```

**First-Order Logic:** ∀ s₁, e₁, s₂, e₂: overlap(s₁,e₁,s₂,e₂) ⟺ s₁ < e₂ ∧ s₂ < e₁

The **reified conflict** rule wraps overlap detection with event identity and a reason term:

```prolog
conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), Reason) :-
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(NewStart, NewEnd, ExStart, ExEnd),
    Reason = overlap(ID, Title, SH, SM, EH, EM).
```

### 6.5.2 Slot Freedom

A time slot is free iff no existing event conflicts with it:

```prolog
slot_is_free(Start, End, Events) :-
    \+ slot_conflicts_with_events(Start, End, Events).

slot_conflicts_with_events(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM), Events),
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(Start, End, ExStart, ExEnd).
```

**FOL:** free(s, e, E) ⟺ ¬∃ ev ∈ E: overlap(s, e, start(ev), end(ev))

### 6.5.3 Hard Constraint Violations

Four violation rules model infeasible conditions:

```prolog
violation(no_overlap, Event, AllEvents, overlap(OtherId, OtherTitle)) :- ...
violation(before_working_hours, Event, _, before_working_hours) :- ...
violation(after_working_hours, Event, _, after_working_hours) :- ...
violation(positive_duration, Event, _, invalid_duration) :- ...
```

Each violation rule has its body declared `:- dynamic`, so `demo/1` can open it with `clause/2`.

### 6.5.4 Soft Cost Rules

Four soft cost rules compute penalties for sub-optimal scheduling:

```prolog
soft_cost(preferred_time, Event, AllEvents, Prefs, Cost) :- ...
soft_cost(buffer_proximity, Event, AllEvents, _, Cost) :- ...
soft_cost(daily_overload, _, AllEvents, _, Cost) :- ...
soft_cost(priority_schedule, Event, _, _, Cost) :- ...
```

### 6.5.5 Reified Conflicts and Displacement

The A* search uses reified terms for tracking:

```prolog
%% g(n) — displacement cost
event_displacement_cost(OrigEvent, ModEvent, EventCost) :-
    ...
    EventCost is MovePen + ShiftHours * ShiftW + Priority * PriFactor.

%% h(n) — priority loss heuristic
event_priority_loss(Event, Strategy, Loss) :-
    strategy_weight(Strategy, W),
    Loss is Priority * Priority * W.
```

---

## 6.6 Constraints — First-Class Objects

### 6.6.1 constraint/3 (schedule.pl)

Constraints in `schedule.pl` are named, parameterised, first-class Prolog objects:

```prolog
constraint(no_overlap, [Start, End, Events],
    \+ slot_conflicts_with_events(Start, End, Events)).

constraint(within_bounds, [Start, End, MinStart, MaxEnd],
    (Start >= MinStart, End =< MaxEnd)).

constraint(positive_duration, [Start, End], End > Start).
```

Each `constraint/3` fact stores a **name**, a **parameter list**, and a **condition** — a Prolog goal that can be passed to `demo/1`.

### 6.6.2 check_constraint/2 — Now via demo/1 (FULL Meta-Interpreter)

This is a **key architectural change** from the original:

```prolog
%% OLD (scheduler.pl — wrapper meta-interpreter):
check_constraint(Name, Args) :-
    constraint(Name, Args, Condition),
    call(Condition).           %% ← opaque: Prolog resolves internally

%% NEW (schedule.pl — full meta-interpreter):
check_constraint(Name, Args) :-
    constraint(Name, Args, Condition),
    demo(Condition).           %% ← transparent: every sub-goal passes through demo/1
```

When `demo(Condition)` is called:
1. If `Condition` is a conjunction `(A, B)`, `demo/1` proves `A` then `B` recursively.
2. If `Condition` is a negation `\+ G`, `demo/1` attempts `demo(G)` and negates.
3. If `Condition` is a user-defined predicate like `slot_conflicts_with_events(...)`, `clause/2` retrieves its body and `demo/1` proves that body.
4. If `Condition` is a built-in like `Start >= MinStart`, the `is_builtin/1` guard delegates to Prolog directly.

### 6.6.3 check_hard/2 and evaluate_soft/3 (constraint_solve.pl)

Hard constraints use `demo(\+ violation(...))`:

```prolog
check_hard(no_overlap, [Event, AllEvents]) :-
    \+ demo(violation(no_overlap, Event, AllEvents, _)).

check_hard(before_working_hours, [Event]) :-
    \+ demo(violation(before_working_hours, Event, [], _)).
```

Soft constraints use `demo(soft_cost(...))`:

```prolog
evaluate_soft(preferred_time, [Event, AllEvents, Prefs], Cost) :-
    demo(soft_cost(preferred_time, Event, AllEvents, Prefs, Cost)).

evaluate_soft(buffer_proximity, [Event, AllEvents, _Prefs], Cost) :-
    demo(soft_cost(buffer_proximity, Event, AllEvents, _, Cost)).
```

### 6.6.4 Operator-Based Constraint Syntax

```prolog
Event satisfies ConstraintName :-
    check_hard(ConstraintName, [Event, []]).

Event violates ConstraintName :-
    demo(violation(ConstraintName, Event, [], _)).

Event penalized_by soft(Name, Cost) :-
    evaluate_soft(Name, [Event, [], []], Cost),
    Cost > 0.
```

### 6.6.5 Hard vs. Soft Constraint System

| Aspect | Hard Constraints | Soft Constraints |
|--------|-----------------|-----------------|
| Purpose | Binary feasibility check | Penalty-based quality optimisation |
| Checking | `check_hard(Name, Args)` → `\+ demo(violation(...))` | `evaluate_soft(Name, Args, Cost)` → `demo(soft_cost(...))` |
| Failure semantics | Violating any → infeasible (discarded) | Violating any → higher cost (penalised) |
| Used by | Slot CSP filtering, hard constraint validation | A* cost function (soft component) |
| Meta-interpretation | `demo(\+ violation(...))` → clause/2 opens violation rules | `demo(soft_cost(...))` → clause/2 opens cost rules |

---

## 6.7 The Full Meta-Interpreter — demo/1 with clause/2

### 6.7.1 Overview

The meta-interpreter is the **heart of the KRR architecture**. It reimplements Prolog's own proof process inside Prolog itself, making every resolution step **transparent, traceable, and controllable**.

**The critical difference from the original:**

```prolog
%% WRAPPER meta-interpreter (scheduler.pl / constraint_solver.pl):
demo(Goal) :- call(Goal).
%%   → Hands execution back to Prolog's internal engine.
%%   → The resolution of Goal is completely opaque.
%%   → No tracing, no depth control, no explanation.

%% FULL meta-interpreter (schedule.pl / constraint_solve.pl):
demo(Goal) :-
    \+ is_builtin(Goal),
    clause(Goal, Body),
    demo(Body).
%%   → Retrieves the clause body using clause/2.
%%   → Recursively proves every sub-goal through demo/1.
%%   → Every step is visible. Nothing is hidden.
```

### 6.7.2 Complete demo/1 Clause Catalogue

The full meta-interpreter handles every Prolog construct:

#### Base case
```prolog
demo(true).
```

#### Conjunction (A, B)
```prolog
demo((A, B)) :- demo(A), demo(B).
```

#### If-Then-Else (must precede general disjunction)
```prolog
demo((Cond -> Then ; Else)) :-
    ( demo(Cond) -> demo(Then) ; demo(Else) ).
```

#### If-Then (no else)
```prolog
demo((Cond -> Then)) :- demo(Cond), demo(Then).
```

#### Disjunction
```prolog
demo((A ; _B)) :- demo(A).
demo((_A ; B)) :- demo(B).
```

#### Negation as Failure
```prolog
demo(\+ A) :- \+ demo(A).
```

#### Arithmetic and Comparison Built-ins
```prolog
demo(X is E) :- X is E.
demo(X < Y)  :- X < Y.
demo(X > Y)  :- X > Y.
demo(X >= Y) :- X >= Y.
demo(X =< Y) :- X =< Y.
```

#### Type-Checking Built-ins
```prolog
demo(integer(X)) :- integer(X).
demo(number(X))  :- number(X).
demo(atom(X))    :- atom(X).
```

#### List Built-ins
```prolog
demo(member(X, L))       :- member(X, L).
demo(append(A, B, C))    :- append(A, B, C).
demo(length(L, N))       :- length(L, N).
demo(between(Lo, Hi, X)) :- between(Lo, Hi, X).
```

#### Meta-findall (wraps inner goal in demo/1)
```prolog
demo(findall(T, G, L)) :- findall(T, demo(G), L).
```

#### **THE CORE — Clause-Based Resolution**
```prolog
demo(Goal) :-
    \+ is_builtin(Goal),
    clause(Goal, Body),
    demo(Body).
```

This is the defining clause: for any goal that is **not** a built-in, `clause/2` retrieves the clause's body, and `demo/1` recursively proves it. This is what makes it a *full* meta-interpreter rather than a wrapper.

### 6.7.3 The is_builtin/1 Guard

The `is_builtin/1` predicate prevents `clause/2` from being called on Prolog's built-in predicates (which have no accessible clauses). It covers:

- Logical connectives: `true`, `(,)`, `(;)`, `(\+)`, `(->)`
- Arithmetic: `is`, `<`, `>`, `>=`, `=<`, `=:=`, `=\=`
- Unification: `=`, `\=`
- Type checks: `integer/1`, `number/1`, `atom/1`, `is_list/1`
- List operations: `member/2`, `append/3`, `length/2`, `between/3`, `msort/2`, `sort/2`, `exclude/3`
- Aggregation: `findall/3`, `sum_list/2`
- I/O: `write/1`, `writeln/1`, `nl`, `format/2,3`
- Meta: `copy_term/2`, `ground/1`, `var/1`, `nonvar/1`

### 6.7.4 Cross-Module Resolution (constraint_solve.pl)

`constraint_solve.pl` imports predicates from `schedule.pl` (e.g., `time_to_minutes/3`, `events_overlap/4`). Its core clause adds a **cross-module fallback**:

```prolog
%% constraint_solve.pl core:
demo(Goal) :-
    \+ is_builtin(Goal),
    \+ is_constraint_query(Goal),
    (   clause(Goal, Body)
    ->  demo(Body)
    ;   schedule:demo(Goal)     %% ← fallback to schedule module
    ).
```

If `clause/2` cannot find a local clause (because the predicate is defined in `schedule.pl`), execution falls back to `schedule:demo(Goal)`, which will resolve it in the schedule module's meta-interpreter. This keeps all domain resolution transparent across module boundaries.

The `is_constraint_query/1` guard prevents infinite recursion on convenience predicates:

```prolog
is_constraint_query(hard_constraint_holds(_, _, _)).
is_constraint_query(soft_constraint_cost(_, _, _, _, _)).
is_constraint_query(event_has_violation(_, _, _)).
is_constraint_query(event_is_valid(_, _)).
```

### 6.7.5 holds/1 — Semantic Alias

```prolog
holds(Proposition) :- demo(Proposition).
```

`holds/1` provides a more natural reading for KRR queries: `holds(slot_is_free(480, 540, []))` reads as "it holds that the slot 480–540 is free given no events."

### 6.7.6 Step-by-Step Proof Trace — check_constraint(no_overlap, ...)

Consider checking the no_overlap constraint for slot 480–540 with an empty event list:

```
Call: demo(check_all_slot_constraints(480, 540, 360, 1380, []))
  → clause/2 retrieves body of check_all_slot_constraints(480, 540, 360, 1380, []):
      Body = (check_constraint(positive_duration, [480, 540]),
              check_constraint(within_bounds, [480, 540, 360, 1380]),
              check_constraint(no_overlap, [480, 540, []]))
  
  → demo(check_constraint(positive_duration, [480, 540]))
      → clause/2 retrieves body of check_constraint(positive_duration, [480, 540]):
          constraint(positive_duration, [480, 540], Condition)
          → Condition = (540 > 480)
          demo(540 > 480)
          → is_builtin → 540 > 480 → true ✓
  
  → demo(check_constraint(within_bounds, [480, 540, 360, 1380]))
      → clause/2 retrieves body:
          constraint(within_bounds, [480, 540, 360, 1380], Condition)
          → Condition = (480 >= 360, 540 =< 1380)
          demo((480 >= 360, 540 =< 1380))
          → demo(480 >= 360) → builtin → true ✓
          → demo(540 =< 1380) → builtin → true ✓
  
  → demo(check_constraint(no_overlap, [480, 540, []]))
      → clause/2 retrieves body:
          constraint(no_overlap, [480, 540, []], Condition)
          → Condition = \+ slot_conflicts_with_events(480, 540, [])
          demo(\+ slot_conflicts_with_events(480, 540, []))
          → \+ demo(slot_conflicts_with_events(480, 540, []))
          → clause/2 retrieves body of slot_conflicts_with_events(480, 540, []):
              → member(event(...), []) → fails (empty list)
          → demo fails → \+ succeeds → true ✓
  
Result: All three constraints passed ✓
```

### 6.7.7 Step-by-Step Proof Trace — Conflict Detection

Consider `check_conflict(9, 30, 11, 0, [event("E1","Meeting",9,0,10,0)])`:

```
Python → check_conflict/6 → solve(check_conflict(9, 30, 11, 0, Events), Conflicts)

  → demo(time_to_minutes(9, 30, NewStart))
      → \+ is_builtin(time_to_minutes(9, 30, NewStart)) → true (not built-in)
      → clause(time_to_minutes(9, 30, NewStart), Body)
          Body = (integer(9), 9 >= 0, 9 =< 23,
                  integer(30), 30 >= 0, 30 =< 59,
                  NewStart is 9*60+30)
      → demo(Body)
          → demo(integer(9)) → builtin → true ✓
          → demo(9 >= 0) → builtin → true ✓
          → demo(9 =< 23) → builtin → true ✓
          → demo(integer(30)) → builtin → true ✓
          → demo(30 >= 0) → builtin → true ✓
          → demo(30 =< 59) → builtin → true ✓
          → demo(NewStart is 9*60+30) → builtin → NewStart = 570 ✓
      
  → demo(time_to_minutes(11, 0, NewEnd))
      → clause/2 → demo body → NewEnd = 660 ✓

  → findall(conflict(ID, Title, SH, SM, EH, EM),
            demo(conflict(interval(570, 660), event(ID, Title, SH, SM, EH, EM), _Reason)),
            Conflicts)

      For event("E1", "Meeting", 9, 0, 10, 0):
      → demo(conflict(interval(570, 660), event("E1","Meeting",9,0,10,0), _Reason))
          → clause/2 retrieves body of conflict/3:
              Body = (time_to_minutes(9, 0, ExStart),
                      time_to_minutes(10, 0, ExEnd),
                      intervals_overlap(570, 660, ExStart, ExEnd),
                      Reason = overlap("E1","Meeting",9,0,10,0))
          → demo(time_to_minutes(9, 0, ExStart))
              → clause/2 → ExStart = 540 ✓
          → demo(time_to_minutes(10, 0, ExEnd))
              → clause/2 → ExEnd = 600 ✓
          → demo(intervals_overlap(570, 660, 540, 600))
              → clause/2 retrieves body:
                  Body = (570 < 600, 540 < 660)
              → demo(570 < 600) → builtin → true ✓
              → demo(540 < 660) → builtin → true ✓
          → demo(Reason = overlap("E1","Meeting",9,0,10,0))
              → builtin → unification succeeds ✓
      
  Result: Conflicts = [conflict("E1","Meeting",9,0,10,0)]
```

**Every single step** — time conversion, overlap arithmetic, unification — was resolved by `demo/1` through `clause/2`. In the wrapper version, the last five `demo(...)` calls would have been invisible `call(...)` invocations inside Prolog's engine.

---

## 6.8 The Solver — solve/2

### 6.8.1 Design Principle

`solve/2` is the central entry point for all high-level scheduling queries. It takes a **query term** describing what to solve and returns a **result**. All domain sub-goals within `solve/2` are wrapped in `demo/1`, ensuring transparent resolution.

```prolog
solve(QueryTerm, Result).
```

### 6.8.2 schedule.pl Solver Clauses

| Query | Purpose | Meta-interpreter usage |
|-------|---------|----------------------|
| `solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts)` | Find all events that overlap with a proposed new time | `demo(time_to_minutes(...))`, `demo(conflict(...))` inside findall |
| `solve(find_free_slots(Dur, Evts, MinSH, MinSM, MaxEH, MaxEM), Slots)` | CSP: find all valid time slots | `demo(check_all_slot_constraints(...))`, `demo(minutes_to_time(...))` |
| `solve(find_free_ranges(Events, MinSH, MinSM, MaxEH, MaxEM), Ranges)` | Find maximal gap intervals between events | `demo(time_to_minutes(...))` for bounds |
| `solve(find_free_days(Dur, EventsByDay, SH, SM, EH, EM), FreeDays)` | Find days with at least one available slot | Recursive `solve(find_free_slots(...))` |
| `solve(find_available_slot(Dur, Events, Bounds, Slot), Slot)` | KRR-style: find first available slot | Delegates to `solve(find_free_slots(...))` |
| `solve(valid_schedule(Start, End, Events, Min, Max), Result)` | Validate a proposed schedule placement | `demo(check_all_slot_constraints(...))` |

**Example — check_conflict solver clause:**

```prolog
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :-
    demo(time_to_minutes(NSH, NSM, NewStart)),
    demo(time_to_minutes(NEH, NEM, NewEnd)),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        demo(conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), _Reason)),
        Conflicts
    ).
```

### 6.8.3 constraint_solve.pl Solver Clauses

| Query | Purpose | Meta-interpreter usage |
|-------|---------|----------------------|
| `solve(validate_hard(Event, AllEvents), Violations)` | Collect all hard constraint violations | `demo(violation(...))` inside findall |
| `solve(soft_cost(Event, AllEvents, Prefs), Total)` | Sum of all soft constraint costs | `evaluate_soft/3` → `demo(soft_cost(...))` |
| `solve(displacement_cost(Orig, Mod), G)` | g(n): accumulated move cost | `demo(event_displacement_cost(...))` |
| `solve(priority_loss(Conflicts, Strategy), H)` | h(n): estimated conflict resolution cost | `demo(event_priority_loss(...))` |
| `solve(heuristic(Orig, Curr, Rem, Strat), F)` | f(n) = g(n) + h(n) | Composes displacement + priority loss |
| `solve(find_best_slot(Event, All, MinH, MinM, MaxH, MaxM), Slot)` | Find best alternative time slot | `demo(fact(...))` for parameters |
| `solve(reschedule(New, Existing, Strategy, ...), Result)` | Full reschedule with option comparison | Calls `solve(find_best_slot(...))`, `solve(priority_loss(...))` |

### 6.8.4 Public API

Python-callable predicates are thin wrappers that delegate to the solver:

```prolog
%% schedule.pl:
check_conflict(NSH, NSM, NEH, NEM, Events, Conflicts) :-
    solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts).

find_free_slots(Dur, Events, MinSH, MinSM, MaxEH, MaxEM, Slots) :-
    solve(find_free_slots(Dur, Events, MinSH, MinSM, MaxEH, MaxEM), Slots).

%% constraint_solve.pl:
validate_hard_constraints(Event, AllEvents, Violations) :-
    solve(validate_hard(Event, AllEvents), Violations).

calculate_soft_cost(Event, AllEvents, Prefs, Cost) :-
    solve(soft_cost(Event, AllEvents, Prefs), Cost).
```

---

## 6.9 Condition-to-Action Mapping

The solver implements a condition-to-action pattern where the query term determines which reasoning path to follow:

| Condition (Query Pattern) | Action |
|---------------------------|--------|
| `solve(check_conflict(...), _)` | Conflict detection via `demo(conflict(...))` |
| `solve(find_free_slots(...), _)` | CSP slot generation via `demo(check_all_slot_constraints(...))` |
| `solve(validate_hard(...), _)` | Hard constraint validation via `demo(violation(...))` |
| `solve(soft_cost(...), _)` | Soft cost summation via `evaluate_soft/3` → `demo(soft_cost(...))` |
| `solve(heuristic(...), _)` | A* evaluation via composed sub-solvers |
| `solve(reschedule(...), _)` | Full rescheduling with option comparison |

This pattern is implemented through Prolog's first-argument indexing — each `solve/2` clause matches on a different first-argument functor, providing efficient clause selection without explicit dispatch logic.

---

## 6.10 Free Slot CSP

The free slot finder implements a Constraint Satisfaction Problem:

**Variables:** Candidate start times at 30-minute intervals  
**Domain:** [MinStart, MaxEnd − Duration]  
**Constraints:**

1. `positive_duration`: End > Start
2. `within_bounds`: Start ≥ MinStart, End ≤ MaxEnd
3. `no_overlap`: ¬∃ event ∈ Events: overlap(Start, End, event_start, event_end)

**Full meta-interpreter integration:**

```prolog
solve(find_free_slots(Duration, Events, MinSH, MinSM, MaxEH, MaxEM), FreeSlots) :-
    demo(time_to_minutes(MinSH, MinSM, MinStart)),
    demo(time_to_minutes(MaxEH, MaxEM, MaxEnd)),
    demo(fact(slot_granularity, Step)),
    demo(fact(max_candidate_iterations, MaxIter)),
    MaxSlotStart is MaxEnd - Duration,
    findall(
        slot(SH, SM, EH, EM),
        (
            between(0, MaxIter, N),
            SlotStart is MinStart + N * Step,
            SlotStart =< MaxSlotStart,
            SlotEnd is SlotStart + Duration,
            demo(check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events)),
            demo(minutes_to_time(SlotStart, SH, SM)),
            demo(minutes_to_time(SlotEnd, EH, EM))
        ),
        FreeSlots
    ).
```

---

## 6.11 A* Rescheduling

When conflicts cannot be resolved by simple option comparison, the full A* search explores the state space:

**State representation:**
```prolog
state(Events, OrigEvents, Cost, Moves, Conflicts)
```

**Search algorithm:** Classic A* with open/closed lists, state-key deduplication, and configurable depth limit.

**Integration with meta-interpreter:**
- `solve(heuristic(...), F)` computes f(n) = g(n) + h(n)
- `solve(displacement_cost(...), G)` computes g(n) via `demo(event_displacement_cost(...))`
- `solve(priority_loss(...), H)` computes h(n) via `demo(event_priority_loss(...))`
- `solve(find_best_slot(...), Slot)` finds relocation targets via `demo(fact(...))` for parameters

---

## 6.12 Practical Examples

### Example 1: Conflict Detection

**Scenario:** New event 14:00–15:30, existing event "Study" 14:00–16:00.

```prolog
?- check_conflict(14, 0, 15, 30, [event("S1","Study",14,0,16,0)], Conflicts).
```

**Flow:** `check_conflict/6` → `solve(check_conflict(...))` → `demo(time_to_minutes(14,0,840))` → `demo(time_to_minutes(15,30,930))` → `findall(... demo(conflict(interval(840,930), ...)))` → `clause/2` opens `conflict/3` body → `demo(time_to_minutes(14,0,840))` → `demo(time_to_minutes(16,0,960))` → `demo(intervals_overlap(840,930,840,960))` → `clause/2` opens body → `demo(840 < 960)` ✓ → `demo(840 < 930)` ✓ → overlap found.

**Result:** `Conflicts = [conflict("S1","Study",14,0,16,0)]`

### Example 2: Free Slot Finding (CSP)

**Scenario:** Find 60-minute slots between 08:00 and 18:00 with one existing event.

```prolog
?- find_free_slots(60, [event("E1","Meeting",10,0,11,0)], 8, 0, 18, 0, Slots).
```

**Flow:** For each candidate at 30-min intervals → `demo(check_all_slot_constraints(...))` → opens three constraints via `clause/2` → tests positive_duration, within_bounds, no_overlap → collects passing slots.

**Result:** Slots at 08:00–09:00, 08:30–09:30, 09:00–10:00, 11:00–12:00, ...

### Example 3: Hard Constraint Validation

**Scenario:** Event from 05:00–06:00 (before working hours).

```prolog
?- validate_hard_constraints(
       event("X","Early",5,0,6,0,3,meeting),
       [], Violations).
```

**Flow:** `solve(validate_hard(...))` → `findall(V, demo(violation(_, Event, [], V)), Violations)` → `clause/2` opens each violation rule → `demo(time_to_minutes(5,0,300))` → `demo(300 < 360)` → before_working_hours violation found.

**Result:** `Violations = [before_working_hours]`

### Example 4: Soft Cost Computation

**Scenario:** Meeting at 20:00 (outside preferred window 09:00–17:00).

```prolog
?- calculate_soft_cost(
       event("M1","Late Meeting",20,0,21,0,5,meeting),
       [], [], Cost).
```

**Flow:** `solve(soft_cost(...))` → `evaluate_soft(preferred_time, ...)` → `demo(soft_cost(preferred_time, ...))` → `clause/2` opens rule body → computes penalty.

### Example 5: A* Rescheduling

**Scenario:** New priority-10 event conflicts with existing priority-5 event; balanced strategy.

```prolog
?- reschedule_event(
       event("New","Exam",9,30,11,0,10,exam),
       ExistingEvents, balanced, 8, 0, 18, 0, Result).
```

**Flow:** `solve(reschedule(...))` → detect conflicts → `solve(find_best_slot(NewEvent,...))` for Option A → `try_move_conflicts(...)` for Option B → `solve(priority_loss(Conflicts, balanced), PLoss)` → `demo(event_priority_loss(...))` → `strategy_weight(balanced, 1.0)` → `pick_best_option(...)`.

### Example 6: Proof Tracing

```prolog
?- demo_trace(slot_is_free(480, 540, []), Trace).

Trace = step(slot_is_free(480,540,[]),
             negation(slot_conflicts_with_events(480,540,[])))
```

The trace shows: `slot_is_free` was proved by opening its clause (step), which contained a negation of `slot_conflicts_with_events`, which failed (empty list), so the negation succeeded.

---

## 6.13 System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Python Backend                         │
│  (Agent, PrologService, FastAPI)                         │
└────────────────────────┬─────────────────────────────────┘
                         │ pyswip / subprocess
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Prolog KRR Engine                            │
│                                                          │
│  ┌─────────────────────┐   ┌──────────────────────────┐ │
│  │   schedule.pl        │   │  constraint_solve.pl      │ │
│  │                      │   │                           │ │
│  │  L0: Operators       │   │  L0: Operators            │ │
│  │  L1: Facts           │   │  L1: Facts/Weights        │ │
│  │  L2: Rules           │◄──│  L2: Violation/Cost Rules │ │
│  │  L3: Constraints     │   │  L3: Hard/Soft Checks     │ │
│  │  L4: demo/1 (FULL)   │◄──│  L4: demo/1 (FULL+xmod)  │ │
│  │  L5: solve/2         │   │  L5: solve/2 + A*         │ │
│  └─────────────────────┘   └──────────────────────────┘ │
│                                                          │
│  Arrow direction: constraint_solve.pl imports from       │
│  schedule.pl and falls back to schedule:demo(Goal)       │
│  for cross-module predicates.                            │
└──────────────────────────────────────────────────────────┘
```

---

## 6.14 Summary Table

| KRR Technique | Implementation | Location |
|--------------|----------------|----------|
| **Full Meta-Interpreter (clause/2 + recursive demo/1)** | `demo(Goal) :- clause(Goal, Body), demo(Body)` | schedule.pl L4, constraint_solve.pl L4 |
| is_builtin/1 Guard | Prevents clause/2 on built-in predicates | schedule.pl L4, constraint_solve.pl L4 |
| Cross-Module Fallback | `schedule:demo(Goal)` for shared predicates | constraint_solve.pl L4 |
| Proof Tracing (demo_trace/2) | Builds explanation trees: `step(Goal, BodyTrace)` | schedule.pl L4b, constraint_solve.pl L4b |
| Depth-Limited Resolution (demo_depth/2) | Prevents infinite recursion | schedule.pl L4b, constraint_solve.pl L4b |
| Solution Collection (demo_all/2) | `findall(Goal, demo(Goal), Solutions)` | Both modules L4b |
| Semantic holds/1 | KRR alias: `holds(P) :- demo(P)` | Both modules |
| Declarative Facts (Layer 1) | `fact/2`, `strategy_weight/2`, `preferred_window/3` | Both modules L1 |
| Self-Describing Metadata | `statement/3`, `rule/3` | Both modules L1 |
| Custom Operators | `overlaps_with`, `is_free_during`, `conflicts_with`, `violates`, `satisfies`, `penalized_by` | L0 |
| Dynamic Declarations | All domain predicates `:- dynamic` for clause/2 introspection | Both modules |
| Inference Rules (Layer 2) | `intervals_overlap/4`, `conflict/3`, `violation/4`, `soft_cost/5` | Both modules L2 |
| First-Class Constraints | `constraint/3`, `check_constraint/2` via demo/1 | schedule.pl L3 |
| Hard/Soft Constraint System | `check_hard/2` via `demo(\+ violation(...))`, `evaluate_soft/3` via `demo(soft_cost(...))` | constraint_solve.pl L3 |
| Central Solver (solve/2) | All queries route through solve/2; domain goals wrapped in demo/1 | Both modules L5 |
| Free Slot CSP | Constraint-based slot generation via `demo(check_all_slot_constraints(...))` | schedule.pl L5 |
| A* State-Space Search | `astar_search/6` with f(n) = g(n) + h(n) | constraint_solve.pl L5 |
| Strategy-Based Optimisation | `strategy_weight/2` tunes heuristic: minimize_moves, balanced, maximize_quality | constraint_solve.pl L1, L5 |
| Reified Conflicts | `conflict/3` and `violation/4` — conflicts and violations as data objects | Both modules L2 |
| Displacement Cost g(n) | `event_displacement_cost/3` proved via demo/1 | constraint_solve.pl L2 |
| Priority Loss Heuristic h(n) | `event_priority_loss/3` with quadratic scaling | constraint_solve.pl L2 |
| Python–Prolog Bridge | pyswip in-process + subprocess fallback + pure Python fallback | PrologService (Python) |

---

## 6.15 References

1. Sterling, L. & Shapiro, E. (1994). *The Art of Prolog: Advanced Programming Techniques*. MIT Press. — Classic reference for meta-interpreters in Prolog.
2. Bratko, I. (2012). *Prolog Programming for Artificial Intelligence* (4th ed.). Pearson. — Meta-interpreter patterns and KRR design.
3. Russell, S. & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson. — A* search algorithm, constraint satisfaction, knowledge representation.
4. Clocksin, W.F. & Mellish, C.S. (2003). *Programming in Prolog* (5th ed.). Springer. — Prolog programming fundamentals.
5. SWI-Prolog Documentation. `clause/2`. https://www.swi-prolog.org/pldoc/doc_for?object=clause/2 — The built-in used by the full meta-interpreter.
6. SWI-Prolog Documentation. Module system. https://www.swi-prolog.org/pldoc/man?section=modules — Cross-module predicate resolution.
