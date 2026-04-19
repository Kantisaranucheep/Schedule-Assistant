# KRR Refactoring — Before & After Comparison

## Overview

This document describes the transformation of the Prolog reasoning engine
(`scheduler.pl` and `constraint_solver.pl` in `apps/backend/app/chat/prolog/`)
from a **procedural/algorithmic** style to a **Knowledge Representation &
Reasoning (KRR)** architecture.

**Goal:** Make Prolog behave as a *knowledge-based reasoning engine* — not a
scripting tool — without changing the Python ↔ Prolog interface or the overall
system architecture.

---

## Architecture: The 6-Layer KRR Stack

Both files now follow the same layered design:

| Layer | Name | Purpose |
|-------|------|---------|
| 0 | **Custom Operators** | Domain-specific syntax (`overlaps_with`, `is_free_during`, `conflicts_with`, `satisfies`, `violates`, `penalized_by`) |
| 1 | **Facts (Knowledge Base)** | Pure ground knowledge — domain constants, preference windows, strategy weights, metadata (`fact/2`, `statement/3`, `rule/3`) |
| 2 | **Rules (Inference)** | Declarative rules that derive new knowledge from facts (`intervals_overlap/4`, `conflict/3`, `slot_is_free/3`, `violation/4`, `soft_cost/5`) |
| 3 | **Constraints** | Named, first-class constraint objects (`constraint/3`, `check_constraint/2`, `check_hard/2`, `evaluate_soft/3`) |
| 4 | **Meta-interpreter** | `demo/1` / `holds/1` — a lightweight prove-engine that makes reasoning explicit and traceable |
| 5 | **Solver** | `solve/2` — central entry point; every query dispatches through the solver, which selects applicable rules and drives reasoning |

All **public API predicates** (the ones Python calls) are thin wrappers that
delegate to `solve/2`.

---

## Before vs. After — `scheduler.pl`

### 1. Facts (Knowledge Base)

**BEFORE — Magic numbers buried in code:**
```prolog
Step = 30,               % hard-coded in find_free_slots
between(0, 1000, N),     % hard-coded iteration limit
```

**AFTER — Explicit, inspectable facts:**
```prolog
fact(slot_granularity, 30).
fact(max_candidate_iterations, 1000).
fact(minutes_in_day, 1440).

%% Self-describing metadata
statement(slot_granularity, domain_constant, 'Granularity for candidate slot generation').
statement(overlap_rule,     inference_rule,  'Two intervals overlap iff S1 < E2 and S2 < E1').
```

**Why it matters:** Knowledge is now *separate from the inference mechanism*.
You can query `fact(slot_granularity, X)` or `statement(Name, Type, Desc)` to
inspect what the system knows — which is a core KRR principle.

---

### 2. Rules (Inference)

**BEFORE — Procedural predicate with inline computation:**
```prolog
check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents, Conflicts) :-
    time_to_minutes(NewStartH, NewStartM, NewStart),
    time_to_minutes(NewEndH, NewEndM, NewEnd),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        (
            member(event(ID, Title, SH, SM, EH, EM), ExistingEvents),
            time_to_minutes(SH, SM, ExStart),
            time_to_minutes(EH, EM, ExEnd),
            events_overlap(NewStart, NewEnd, ExStart, ExEnd)
        ),
        Conflicts
    ).
```

**AFTER — Reified conflict rule + solver dispatch:**
```prolog
%% Layer 2: Inference rule — WHY does a conflict exist?
conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), Reason) :-
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(NewStart, NewEnd, ExStart, ExEnd),
    Reason = overlap(ID, Title, SH, SM, EH, EM).

%% Layer 5: Solver dispatches the query
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :-
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), _Reason),
        Conflicts
    ).

%% Public API (unchanged signature):
check_conflict(A, B, C, D, E, F) :- solve(check_conflict(A, B, C, D, E, F), F).
```

**Why it matters:** The *conflict* is now a first-class term with a *reason*.
Instead of "compute overlaps procedurally", the system *infers* conflicts by
applying the `conflict/3` rule — and can explain *why* the conflict exists.

---

### 3. Constraints

**BEFORE — Constraints were implicit in procedural code:**
```prolog
slot_is_free(Start, End, Events) :-
    \+ slot_conflicts_with_events(Start, End, Events).
%% No notion of "what constraint was checked"
```

**AFTER — Named, first-class constraint objects:**
```prolog
%% Constraint declarations
constraint(no_overlap, [Start, End, Events],
    \+ slot_conflicts_with_events(Start, End, Events)).
constraint(within_bounds, [Start, End, MinStart, MaxEnd],
    (Start >= MinStart, End =< MaxEnd)).
constraint(positive_duration, [Start, End],
    End > Start).

%% Generic constraint checker
check_constraint(Name, Args) :-
    constraint(Name, Args, Condition),
    call(Condition).

%% Composed constraint validation
check_all_slot_constraints(Start, End, MinStart, MaxEnd, Events) :-
    check_constraint(positive_duration, [Start, End]),
    check_constraint(within_bounds,     [Start, End, MinStart, MaxEnd]),
    check_constraint(no_overlap,        [Start, End, Events]).
```

**Why it matters:** Constraints are now *objects* — you can enumerate them
(`constraint(Name, _, _)`), compose them, and reason about them. This is
Constraint Satisfaction Problem (CSP) representation in its proper KRR form.

---

### 4. Custom Operators

**BEFORE — No domain-specific syntax:**
```prolog
intervals_overlap(Start1, End1, Start2, End2).
%% Reads as "call a procedure"
```

**AFTER — Natural-language-like propositions:**
```prolog
:- op(700, xfx, overlaps_with).
:- op(700, xfx, is_free_during).
:- op(700, xfx, conflicts_with).

%% Now you can write:
?- interval(480, 540) overlaps_with interval(500, 600).
?- slot(600, 660) is_free_during [event(e1, "M", 9, 0, 10, 0)].
?- interval(540, 600) conflicts_with Events.
```

**Why it matters:** KRR emphasizes that knowledge should be *readable as
propositions*. Custom operators let Prolog code read like logical statements
rather than function calls.

---

### 5. Meta-Interpreter (`demo/1`)

**BEFORE — No meta-level reasoning:**
```prolog
%% You could only call predicates directly.
%% No way to "reason about reasoning".
```

**AFTER — Lightweight meta-interpreter:**
```prolog
demo(true).
demo((A, B))  :- demo(A), demo(B).
demo((A ; _)) :- demo(A).
demo((_ ; B)) :- demo(B).
demo(\+ A)    :- \+ demo(A).
demo(A is B)  :- A is B.
demo(A < B)   :- A < B.
%% ... arithmetic built-ins ...
demo(check_constraint(Name, Args)) :- check_constraint(Name, Args).
demo(Goal)    :- call(Goal).  %% catch-all

%% Semantic alias:
holds(Proposition) :- demo(Proposition).
```

**Usage:**
```prolog
?- demo(slot_is_free(480, 540, [])).
true.

?- holds(intervals_overlap(480, 540, 500, 600)).
true.

?- demo(check_constraint(no_overlap, [480, 540, []])).
true.
```

**Why it matters:** The meta-interpreter makes the reasoning process *explicit*.
`demo/1` is the classic KRR pattern — it says "this goal is *provable* from the
knowledge base". It also enables future extensions like tracing, explanation
generation, or confidence scoring.

---

### 6. Solver (`solve/2`)

**BEFORE — Each predicate was standalone:**
```prolog
check_conflict(...).    %% directly computes
find_free_slots(...).   %% directly computes
find_free_ranges(...).  %% directly computes
%% No central reasoning entry point
```

**AFTER — Central solver dispatches all queries:**
```prolog
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :- ...
solve(find_free_slots(Duration, Events, ...), FreeSlots) :- ...
solve(find_free_ranges(Events, ...), FreeRanges) :- ...
solve(find_free_days(Duration, EventsByDay, ...), FreeDays) :- ...
solve(find_available_slot(Duration, Events, Bounds, Slot), Slot) :- ...
solve(valid_schedule(Start, End, Events, Min, Max), Result) :- ...

%% Public API delegates to solver:
check_conflict(A, B, C, D, E, F) :- solve(check_conflict(A, B, C, D, E, F), F).
find_free_slots(A, B, C, D, E, F, G) :- solve(find_free_slots(A, B, C, D, E, F), G).
```

**Why it matters:** The solver is the *reasoning entry point*. Instead of
"calling a function", the user is "asking the solver a question". This is the
fundamental KRR paradigm shift: from *computation* to *query resolution*.

---

## Before vs. After — `constraint_solver.pl`

### 1. Facts (Knowledge Base)

**BEFORE — Magic numbers in predicate bodies:**
```prolog
StartMin < 360,   % Before 6:00 AM (360 = magic number)
EndMin > 1380,    % After 23:00
%% Preferred times: hard-coded in each predicate clause
preferred_time_cost(meeting, StartMin, ...) :- StartMin >= 540, StartMin =< 1020 ...
```

**AFTER — All parameters as inspectable facts:**
```prolog
fact(working_hours_start, 360).
fact(working_hours_end,   1380).
fact(min_buffer_minutes,  15).
fact(daily_soft_limit,    6).
fact(daily_hard_limit,    8).
fact(move_penalty,        3).
fact(shift_weight,        2).
fact(priority_factor,     0.5).

preferred_window(meeting,  540, 1020).
preferred_window(study,    480,  720).
preferred_window(exercise, 360,  480).

preference_penalty(meeting, 10).
preference_penalty(study,    5).
preference_penalty(exercise, 3).
```

---

### 2. Rules — Hard Constraint Violations

**BEFORE — One monolithic `findall` with inline checks:**
```prolog
validate_hard_constraints(event(Id, _, SH, SM, EH, EM, _, _), AllEvents, Violations) :-
    time_to_minutes(SH, SM, StartMin),
    time_to_minutes(EH, EM, EndMin),
    findall(Violation, (
        (  member(event(OtherId,...), AllEvents),
           OtherId \= Id, ..., Violation = overlap(OtherId, OtherTitle))
        ;  (StartMin < 360, Violation = before_working_hours)
        ;  (EndMin > 1380, Violation = after_working_hours)
        ;  (EndMin =< StartMin, Violation = invalid_duration)
    ), Violations).
```

**AFTER — Each violation is an independent inference rule:**
```prolog
violation(no_overlap, Event, AllEvents, overlap(OtherId, OtherTitle)) :-
    ... %% one clear rule

violation(before_working_hours, Event, _, before_working_hours) :-
    time_to_minutes(SH, SM, Start),
    fact(working_hours_start, WorkStart),
    Start < WorkStart.

violation(after_working_hours, Event, _, after_working_hours) :- ...
violation(positive_duration, Event, _, invalid_duration) :- ...

%% Solver collects all violations:
solve(validate_hard(Event, AllEvents), Violations) :-
    findall(V, violation(_, Event, AllEvents, V), Violations).

%% Public API (unchanged):
validate_hard_constraints(Event, AllEvents, Violations) :-
    solve(validate_hard(Event, AllEvents), Violations).
```

**Why it matters:** Each constraint violation is now a *separate inference
rule*. You can query a specific constraint (`violation(no_overlap, E, Es, R)`)
or ask "what violations exist?" (`violation(_, E, Es, R)`). This is pure KRR:
knowledge + inference, not a big procedural blob.

---

### 3. Constraints — Hard & Soft as First-Class Objects

**BEFORE — Constraints existed only as code paths:**
```prolog
%% "Hard constraint" was just a branch in findall
%% "Soft constraint" was a separate cost function
preferred_time_cost(meeting, StartMin, _, _, Cost) :- ...
buffer_proximity_cost(StartMin, EndMin, AllEvents, Cost) :- ...
```

**AFTER — Named constraint objects with generic checkers:**
```prolog
%% Hard constraints: binary (pass/fail)
check_hard(no_overlap, [Event, AllEvents]) :- \+ violation(no_overlap, Event, AllEvents, _).
check_hard(positive_duration, [Event]) :- \+ violation(positive_duration, Event, [], _).

%% Soft constraints: return penalty cost
evaluate_soft(preferred_time,    [Event, AllEvents, Prefs], Cost) :- soft_cost(preferred_time, ...).
evaluate_soft(buffer_proximity,  [...], Cost) :- ...
evaluate_soft(daily_overload,    [...], Cost) :- ...
evaluate_soft(priority_schedule, [...], Cost) :- ...

%% Operator syntax:
?- Event satisfies no_overlap.
?- Event violates positive_duration.
?- Event penalized_by soft(preferred_time, Cost).
```

---

### 4. Meta-Interpreter — Constraint Reasoning

**BEFORE — No meta-level reasoning available.**

**AFTER:**
```prolog
demo(hard_constraint_holds(Name, Event, AllEvents)) :-
    check_hard(Name, [Event, AllEvents]).

demo(soft_constraint_cost(Name, Event, AllEvents, Prefs, Cost)) :-
    evaluate_soft(Name, [Event, AllEvents, Prefs], Cost).

demo(event_is_valid(Event, AllEvents)) :-
    \+ violation(_, Event, AllEvents, _).

demo(event_has_violation(Event, AllEvents, Violation)) :-
    violation(_, Event, AllEvents, Violation).
```

**Usage:**
```prolog
?- demo(event_is_valid(event(e1,"Meeting",9,0,10,0,5,meeting), [])).
true.

?- demo(event_has_violation(event(e1,"M",5,0,6,0,5,meeting), [], V)).
V = before_working_hours.
```

---

### 5. Solver — Everything Routes Through `solve/2`

**BEFORE:** Each public predicate computed its result directly (e.g.,
`calculate_soft_cost` called `preferred_time_cost`, `buffer_proximity_cost`,
etc. inline).

**AFTER:** All public predicates delegate to `solve/2`:
```prolog
solve(validate_hard(Event, AllEvents), Violations) :- ...
solve(soft_cost(Event, AllEvents, Prefs), TotalCost) :- ...
solve(displacement_cost(Orig, Mod), GCost) :- ...
solve(priority_loss(Conflicts, Strategy), HCost) :- ...
solve(heuristic(Orig, Curr, Rem, Strat), FScore) :- ...
solve(find_best_slot(Event, All, MinH, MinM, MaxH, MaxM), BestSlot) :- ...
solve(reschedule(NewEvent, Existing, Strategy, MinH, MinM, MaxH, MaxM), Result) :- ...

%% Public API (same signatures, all delegate):
validate_hard_constraints(E, A, V) :- solve(validate_hard(E, A), V).
calculate_soft_cost(E, A, P, C)    :- solve(soft_cost(E, A, P), C).
calculate_heuristic(O, C, R, S, F) :- solve(heuristic(O, C, R, S), F).
```

---

## Summary: Paradigm Shift

| Aspect | Before | After |
|--------|--------|-------|
| **Knowledge** | Magic numbers in code | `fact/2`, `preferred_window/3`, `strategy_weight/2` |
| **Rules** | Procedural if-then-else | Declarative inference rules (`conflict/3`, `violation/4`) |
| **Constraints** | Implicit code paths | Named first-class objects (`constraint/3`, `check_hard/2`, `evaluate_soft/3`) |
| **Operators** | Standard Prolog syntax | Domain-specific: `overlaps_with`, `is_free_during`, `satisfies`, `violates` |
| **Meta-reasoning** | None | `demo/1`, `holds/1` — provability reasoning |
| **Metadata** | None | `statement/3`, `rule/3` — self-describing knowledge |
| **Entry point** | Direct predicate calls | `solve/2` — central reasoning dispatcher |
| **Query style** | "Run scheduler" | "Is there an available slot?", "Why do these conflict?" |
| **Python API** | Same signatures | Same signatures (backward-compatible) |

The system has been transformed from **"Prolog used as a scripting/algorithm
tool"** into **"Prolog used as a knowledge-based reasoning engine"** — while
preserving full backward compatibility with the existing Python integration.
