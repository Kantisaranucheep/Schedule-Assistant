# Chapter 6

# Knowledge Representation and Reasoning Techniques

**Schedule Assistant Project**

---

## 6.1 Overview and Guiding Principle

### 6.1.1 The Separation of Knowledge from Control

The central guiding principle of the Schedule Assistant's reasoning engine is:

> **"The system separates knowledge (facts, rules, constraints) from control (solver and optimization), ensuring that reasoning is driven by declarative knowledge rather than procedural logic."**

This principle means that the system's behaviour is determined by *what it knows* — its facts, rules, and constraints — not by *how it computes*. The solver and meta-interpreter provide control flow, but they do so by *consulting* knowledge, not by encoding domain decisions directly. When new scheduling rules are needed, only the knowledge base changes; the inference mechanism remains untouched.

In formal terms, let **KB** denote the knowledge base (facts, rules, constraints) and **Inference** denote the inference mechanism (solver, meta-interpreter). The system's answers are derived as:

> Answer(Query) = Inference(KB, Query)

The **Inference** component is generic — it knows how to chain rules, check constraints, and search state spaces. The **KB** component is domain-specific — it encodes what constitutes a valid schedule, what constitutes a conflict, and what the user's preferences are. This separation is the hallmark of knowledge-based systems and distinguishes the architecture from a conventional procedural scheduler.

### 6.1.2 The Six-Layer Architecture

The Prolog-based reasoning engine is composed of two modules, each following the same six-layer KRR architecture:

| Module | File | Role |
|---|---|---|
| Scheduler | `scheduler.pl` | Conflict detection, free-slot finding (CSP), free-range computation |
| Constraint Solver | `constraint_solver.pl` | Priority-based A* rescheduling with hard/soft constraints and heuristic cost evaluation |

| Layer | Name | Purpose |
|---|---|---|
| 0 | Custom Operators | Domain-specific syntax that makes knowledge read like natural-language propositions |
| 1 | Facts (Knowledge Base) | Pure ground knowledge — domain constants, metadata, preference windows, strategy weights |
| 2 | Rules (Inference Rules) | Declarative rules that derive new knowledge from existing facts |
| 3 | Constraints | Named, first-class constraint objects (hard and soft) that can be queried, combined, and reasoned about |
| 4 | Meta-Interpreter | `demo/1` — an explicit provability reasoning engine that makes inference traceable |
| 5 | Solver | `solve/2` — central reasoning dispatcher through which all queries flow |

The key insight is that **Layers 0–3 are pure knowledge** (they declare *what is true*), while **Layers 4–5 are pure control** (they determine *how to derive answers*). This separation ensures that reasoning is driven by declarative knowledge rather than procedural logic.

### 6.1.3 What Makes This KRR (Not Procedural)

A procedural scheduler would encode decisions directly: "if event A starts before event B ends, then flag a conflict by calling `reportConflict()`." In contrast, this system:

1. **Declares knowledge**: `intervals_overlap(S1, E1, S2, E2) :- S1 < E2, S2 < E1.`
2. **Asks questions**: `?- solve(check_conflict(9, 0, 10, 0, Events), Conflicts).`
3. **Derives answers**: The solver combines rules and constraints to produce an answer.

The system does not tell Prolog *how* to find a conflict — it tells Prolog *what a conflict is*, and the inference engine derives the answer from the knowledge base.

Python interfaces with Prolog through the `pyswip` library. If SWI-Prolog is unavailable at runtime, an equivalent Python fallback implementation is provided (`prolog_service.py`), ensuring the system operates identically regardless of the Prolog runtime's presence.

---

## 6.2 Knowledge Representation

### 6.2.1 Event Representation

Events are represented as Prolog structured terms (compound terms) following a typed schema.

**Basic event (Scheduler module):**

```prolog
event(Id, Title, StartHour, StartMinute, EndHour, EndMinute)
```

**Extended event (Constraint Solver module):**

```prolog
event(Id, Title, StartHour, StartMinute, EndHour, EndMinute, Priority, Type)
```

Where:

- **Id** — Unique identifier of the event (string/atom)
- **Title** — Human-readable event name
- **StartHour, StartMinute** — Event start time (24-hour format)
- **EndHour, EndMinute** — Event end time
- **Priority** — Integer weight from 1 (lowest) to 10 (highest), derived from user persona
- **Type** — Event category (e.g., `meeting`, `study`, `exercise`, `exam`)

**FOL Formalization.** An event can be formalized as a first-order logic predicate:

> event(id, title, sh, sm, eh, em, p, τ)

With the well-formedness axiom:

> ∀ e : event(e) → (0 ≤ sh(e) ≤ 23) ∧ (0 ≤ sm(e) ≤ 59) ∧ (0 ≤ eh(e) ≤ 23) ∧ (0 ≤ em(e) ≤ 59) ∧ (1 ≤ p(e) ≤ 10)

**Concrete examples:**

```prolog
%% "Team Meeting" from 9:00 to 10:00, priority 7, type meeting
event(e1, "Team Meeting", 9, 0, 10, 0, 7, meeting).

%% "Study Session" from 14:00 to 16:00, priority 8, type study
event(e2, "Study Session", 14, 0, 16, 0, 8, study).

%% "Morning Exercise" from 6:30 to 7:30, priority 5, type exercise
event(e3, "Morning Exercise", 6, 30, 7, 30, 5, exercise).
```

### 6.2.2 Time Domain Representation

Time is internally represented as minutes from midnight (domain: 0–1439), enabling efficient arithmetic comparisons:

```prolog
time_to_minutes(Hour, Minute, Total) :-
    integer(Hour), Hour >= 0, Hour =< 23,
    integer(Minute), Minute >= 0, Minute =< 59,
    Total is Hour * 60 + Minute.
```

**FOL reading:**

> ∀ h, m : (0 ≤ h ≤ 23) ∧ (0 ≤ m ≤ 59) → time_to_minutes(h, m, h × 60 + m)

**Example conversions:**

```prolog
?- time_to_minutes(9, 30, T).
T = 570.

?- time_to_minutes(14, 0, T).
T = 840.

?- minutes_to_time(570, H, M).
H = 9, M = 30.
```

### 6.2.3 Facts — The Knowledge Base (Layer 1)

A core KRR principle is that **knowledge must be separated from the inference mechanism**. All tunable domain parameters are declared as Prolog facts using a uniform `fact/2` predicate, rather than being hard-coded inside rule bodies. This is a direct manifestation of the guiding principle: facts are pure knowledge, independent of the solver that uses them.

**Scheduler facts:**

```prolog
fact(minutes_in_day, 1440).
fact(slot_granularity, 30).
fact(max_candidate_iterations, 1000).
```

**Constraint Solver facts:**

```prolog
fact(working_hours_start, 360).    %% 6:00 AM
fact(working_hours_end,   1380).   %% 11:00 PM
fact(min_buffer_minutes, 15).
fact(daily_soft_limit, 6).
fact(daily_hard_limit, 8).
fact(move_penalty,    3).
fact(shift_weight,    2).
fact(priority_factor, 0.5).
fact(slot_step, 30).
fact(max_slot_candidates, 100).
fact(max_reschedule_options, 3).
```

These facts are queryable — one can ask `fact(working_hours_start, X)` and receive the answer `X = 360`. This makes the system's assumptions **explicit and inspectable**, which is a fundamental requirement of knowledge-based systems.

```prolog
%% "What is the working hours start time?"
?- fact(working_hours_start, X).
X = 360.

%% "What is the slot granularity?"
?- fact(slot_granularity, X).
X = 30.

%% "List all domain facts"
?- fact(Name, Value).
Name = minutes_in_day, Value = 1440 ;
Name = slot_granularity, Value = 30 ;
Name = max_candidate_iterations, Value = 1000 ;
...
```

**Preferred time windows** are represented as multi-valued facts:

```prolog
preferred_window(meeting,  540, 1020).   %% 9:00–17:00
preferred_window(study,    480,  720).   %% 8:00–12:00 (primary)
preferred_window(study,    840, 1080).   %% 14:00–18:00 (secondary)
preferred_window(exercise, 360,  480).   %% 6:00–8:00 (morning)
preferred_window(exercise, 1020, 1380).  %% 17:00–23:00 (evening)
```

**Strategy weights** are also facts, enabling strategy-driven reasoning without hard-coded branches:

```prolog
strategy_weight(minimize_moves,  0.5).
strategy_weight(maximize_quality, 2.0).
strategy_weight(balanced,         1.0).
```

**Preference penalties** per event type:

```prolog
preference_penalty(meeting,  10).
preference_penalty(study,     5).
preference_penalty(exercise,  3).
```

### 6.2.4 Priority Knowledge Base

Event priorities are stored in a user profile model with a two-tier system:

| Event Type | Default Priority | Description |
|---|---|---|
| exam | 10 | Academic examinations — critical, immovable |
| deadline | 10 | Project/assignment deadlines — critical |
| study | 8 | Study sessions — high importance |
| class | 8 | Class lectures — high importance |
| work | 8 | Work commitments — high importance |
| meeting | 7 | Meetings — moderately high |
| appointment | 7 | Appointments — moderately high |
| travel | 6 | Travel — moderate |
| exercise | 5 | Physical activity — moderate |
| personal | 5 | Personal tasks — moderate |
| social | 4 | Social activities — lower |
| party | 3 | Entertainment — lowest |

**FOL representation of the priority relation:**

> ∀ e : event(e) ∧ type(e) = exam → priority(e) = 10
> ∀ e : event(e) ∧ type(e) = study → priority(e) = 8
> ∀ e : event(e) ∧ type(e) = party → priority(e) = 3

These defaults can be overridden by an LLM-based priority extraction system that analyses the user's natural language persona description and dynamically adjusts weights to match the user's lifestyle and values.

---

## 6.3 Metadata — Self-Describing Knowledge (Layer 1)

A distinctive feature of the KRR architecture is **metadata**: the knowledge base contains statements that describe its own contents. This enables the system to reason about *what it knows* — a capability known as **introspection** or **meta-knowledge**. This is a direct consequence of separating knowledge from control: because knowledge is stored as data, the system can query its own knowledge base just as it queries scheduling facts.

### 6.3.1 Statement Metadata (`statement/3`)

Each important knowledge entry is annotated with a `statement/3` fact that records its name, type, and a human-readable description:

**Scheduler module:**

```prolog
statement(minutes_in_day,   domain_constant, 'Total minutes in a day (0-1439)').
statement(slot_granularity,  domain_constant, 'Granularity for candidate slot generation').
statement(overlap_rule,      inference_rule,  'Two intervals overlap iff S1 < E2 and S2 < E1').
statement(free_slot_rule,    inference_rule,  'A slot is free iff it conflicts with no event').
statement(free_range_rule,   inference_rule,  'A free range is a maximal gap between events').
statement(free_day_rule,     inference_rule,  'A day is free iff at least one slot fits').
statement(no_overlap,        constraint,      'A new event must not overlap existing events').
statement(within_bounds,     constraint,      'A slot must lie within [MinStart, MaxEnd]').
statement(positive_duration, constraint,      'End time must be strictly after start time').
```

**Constraint Solver module:**

```prolog
statement(no_overlap,        hard_constraint, 'Event must not overlap other events').
statement(within_work_hours, hard_constraint, 'Event must be within working hours').
statement(positive_duration, hard_constraint, 'End time must be after start time').
statement(preferred_time,    soft_constraint, 'Events should be in their preferred window').
statement(buffer_proximity,  soft_constraint, 'Events should have buffer gaps between them').
statement(daily_overload,    soft_constraint, 'Avoid too many events in one day').
statement(priority_schedule, soft_constraint, 'High-priority events belong in peak hours').
```

**Introspection queries — asking the system about its own knowledge:**

```prolog
%% "What inference rules does the system know?"
?- statement(Name, inference_rule, Description).
Name = overlap_rule,    Description = 'Two intervals overlap iff S1 < E2 and S2 < E1' ;
Name = free_slot_rule,  Description = 'A slot is free iff it conflicts with no event' ;
Name = free_range_rule, Description = 'A free range is a maximal gap between events' ;
Name = free_day_rule,   Description = 'A day is free iff at least one slot fits'.

%% "What constraints exist in the system?"
?- statement(Name, constraint, Desc).
Name = no_overlap,        Desc = 'A new event must not overlap existing events' ;
Name = within_bounds,     Desc = 'A slot must lie within [MinStart, MaxEnd]' ;
Name = positive_duration, Desc = 'End time must be strictly after start time'.

%% "What hard constraints does the constraint solver enforce?"
?- statement(Name, hard_constraint, Desc).
Name = no_overlap,        Desc = 'Event must not overlap other events' ;
Name = within_work_hours, Desc = 'Event must be within working hours' ;
Name = positive_duration, Desc = 'End time must be after start time'.

%% "What soft constraints exist?"
?- statement(Name, soft_constraint, Desc).
Name = preferred_time,    Desc = 'Events should be in their preferred window' ;
Name = buffer_proximity,  Desc = 'Events should have buffer gaps between them' ;
Name = daily_overload,    Desc = 'Avoid too many events in one day' ;
Name = priority_schedule, Desc = 'High-priority events belong in peak hours'.

%% "How many knowledge entries of each type?"
?- findall(Type, statement(_, Type, _), Types), msort(Types, Sorted).
Sorted = [constraint, constraint, constraint, domain_constant, domain_constant,
           inference_rule, inference_rule, inference_rule, inference_rule].
```

### 6.3.2 Rule Metadata (`rule/3`)

Each inference rule is also annotated with metadata recording its name, the head pattern it proves, and a description:

```prolog
rule(overlap_rule,
     intervals_overlap(_S1, _E1, _S2, _E2),
     'True when two time intervals share at least one common point').

rule(free_slot_rule,
     slot_is_free(_Start, _End, _Events),
     'True when no event in Events overlaps [Start, End]').

rule(conflict_detection_rule,
     conflict(_NewInterval, _Event, _Reason),
     'True when NewInterval conflicts with Event for Reason').

rule(displacement_cost_rule,
     calculate_displacement_cost(_Orig, _Mod, _Cost),
     'g(n): actual cost of moving events from original positions').

rule(heuristic_rule,
     calculate_heuristic(_Orig, _Curr, _Rem, _Strat, _F),
     'f(n) = g(n) + h(n): A* evaluation function').
```

**Rule introspection queries:**

```prolog
%% "What rules does the system have?"
?- rule(Name, _, Desc).
Name = overlap_rule,             Desc = 'True when two time intervals share ...' ;
Name = free_slot_rule,           Desc = 'True when no event in Events overlaps ...' ;
Name = conflict_detection_rule,  Desc = 'True when NewInterval conflicts with ...' ;
Name = displacement_cost_rule,   Desc = 'g(n): actual cost of moving events ...' ;
Name = heuristic_rule,           Desc = 'f(n) = g(n) + h(n): A* evaluation function'.

%% "What does the overlap_rule prove?"
?- rule(overlap_rule, Head, Desc).
Head = intervals_overlap(_S1, _E1, _S2, _E2),
Desc = 'True when two time intervals share at least one common point'.

%% "Which rule is responsible for conflict detection?"
?- rule(Name, conflict(_, _, _), Desc).
Name = conflict_detection_rule,
Desc = 'True when NewInterval conflicts with Event for Reason'.
```

**Why metadata matters:** The metadata layer enables **explainability** — the system can answer questions about its own reasoning rules. This is a hallmark of knowledge-based systems: the knowledge is not hidden inside opaque functions but is itself queryable data.

---

## 6.4 Custom Operators — Domain-Specific Syntax (Layer 0)

KRR emphasises that knowledge should be **readable as propositions**. Prolog allows the definition of custom operators that transform standard predicate calls into natural-language-like infix expressions. By defining operators at Layer 0, the system's knowledge reads like declarative statements rather than function calls — reinforcing the principle that knowledge is expressed declaratively.

### 6.4.1 Scheduler Operators

```prolog
:- op(700, xfx, overlaps_with).
:- op(700, xfx, is_free_during).
:- op(700, xfx, conflicts_with).
:- op(600, xfx, to).               %% e.g., 9:00 to 17:00
```

These operators allow writing knowledge as propositions:

```prolog
%% "Does interval [480,540] overlap with interval [500,600]?"
?- interval(480, 540) overlaps_with interval(500, 600).
true.

%% "Is slot [600,660] free during the given events?"
?- slot(600, 660) is_free_during [event(e1, "Meeting", 9, 0, 10, 0)].
true.   %% 600 = 10:00, 660 = 11:00; meeting ends at 10:00, no overlap

%% "Does interval [540,600] conflict with any events?"
?- interval(540, 600) conflicts_with [event(e1, "Meeting", 9, 0, 10, 0)].
true.   %% 540 = 9:00, overlaps with 9:00-10:00

%% "Does interval [660,720] conflict with any events?"
?- interval(660, 720) conflicts_with [event(e1, "Meeting", 9, 0, 10, 0)].
false.  %% 660 = 11:00, no overlap
```

### 6.4.2 Constraint Solver Operators

```prolog
:- op(700, xfx, violates).
:- op(700, xfx, satisfies).
:- op(700, xfx, penalized_by).
```

These operators enable constraint-oriented proposition syntax:

```prolog
%% "Does this event satisfy the positive_duration constraint?"
?- event(e1, "Meeting", 9, 0, 10, 0, 7, meeting) satisfies positive_duration.
true.

%% "Does this event violate the positive_duration constraint?"
?- event(e1, "Bad", 10, 0, 9, 0, 5, meeting) violates positive_duration.
true.   %% End (9:00) <= Start (10:00)

%% "Is this event penalized by the preferred_time soft constraint?"
?- event(e1, "Late Meeting", 20, 0, 21, 0, 7, meeting) penalized_by soft(preferred_time, Cost).
Cost = 10.  %% Far outside preferred window 9:00-17:00
```

### 6.4.3 Operator Definitions

The operator definitions use Prolog's `op/3` directive:

```prolog
:- op(Priority, Type, Name).
```

- **Priority** (700 or 600): Determines operator binding precedence.
- **Type** (`xfx`): Indicates a non-associative infix operator, meaning `A op B` must have exactly two arguments.
- **Name**: The operator symbol.

The operator predicates are defined as thin wrappers around the underlying rules:

```prolog
interval(S1, E1) overlaps_with interval(S2, E2) :-
    intervals_overlap(S1, E1, S2, E2).

slot(S, E) is_free_during Events :-
    slot_is_free(S, E, Events).

interval(S, E) conflicts_with Events :-
    slot_conflicts_with_events(S, E, Events).

Event satisfies ConstraintName :-
    check_hard(ConstraintName, [Event, []]).

Event violates ConstraintName :-
    violation(ConstraintName, Event, [], _).

Event penalized_by soft(Name, Cost) :-
    evaluate_soft(Name, [Event, [], []], Cost),
    Cost > 0.
```

**Why custom operators matter:** They transform Prolog code from reading like function calls into reading like **logical propositions**, which is essential for KRR clarity. The statement `event(e1,...) satisfies no_overlap` reads as a proposition about the world, not as an instruction to execute.

---

## 6.5 Logical Reasoning and Inference Rules (Layer 2)

### 6.5.1 The Principle of Declarative Inference

Layer 2 contains the system's **inference rules** — declarative rules that state *what is true* given certain conditions. These rules embody the core of the KRR approach: they derive new knowledge from existing knowledge, rather than encoding step-by-step procedures. Each rule has a clear **logical reading** expressible in First-Order Logic (FOL), and a corresponding Prolog implementation that the meta-interpreter and solver can apply.

The separation of knowledge from control is most visible here: the rules declare logical relationships (e.g., "two intervals overlap if and only if ..."), while the meta-interpreter (Layer 4) and solver (Layer 5) decide *when and how* to apply them.

### 6.5.2 Conflict Detection — Full FOL Derivation

**Intuitive definition.** Two time intervals [S₁, E₁) and [S₂, E₂) overlap if and only if there exists a point in time that belongs to both intervals:

> ∃t : (S₁ ≤ t < E₁) ∧ (S₂ ≤ t < E₂)

**Deriving the efficient test.** Rather than searching for a witness *t*, we derive an equivalent condition. Two intervals do **not** overlap when one ends before the other begins:

> ¬overlap(S₁, E₁, S₂, E₂) ≡ (S₁ ≥ E₂) ∨ (S₂ ≥ E₁)

Overlap is the negation of non-overlap. Applying De Morgan's law:

> overlap(S₁, E₁, S₂, E₂)
> ≡ ¬((S₁ ≥ E₂) ∨ (S₂ ≥ E₁))
> ≡ ¬(S₁ ≥ E₂) ∧ ¬(S₂ ≥ E₁)
> ≡ (S₁ < E₂) ∧ (S₂ < E₁)

**Resolution derivation.** To verify this via resolution, we negate the non-overlap hypothesis and show it leads to the overlap condition:

1. **Hypothesis** (non-overlap): S₁ ≥ E₂ ∨ S₂ ≥ E₁
2. **Negate**: ¬(S₁ ≥ E₂ ∨ S₂ ≥ E₁)
3. **CNF conversion** (De Morgan): ¬(S₁ ≥ E₂) ∧ ¬(S₂ ≥ E₁)
4. **Simplify**: S₁ < E₂ ∧ S₂ < E₁
5. **Resolution step**: From clauses {S₁ < E₂} and {S₂ < E₁}, the conjunction is satisfiable iff both hold simultaneously.

**FOL axiom for interval overlap:**

> ∀ S₁, E₁, S₂, E₂ : overlap(S₁, E₁, S₂, E₂) ↔ (S₁ < E₂) ∧ (S₂ < E₁)

**Prolog implementation** — directly encodes the resolved condition:

```prolog
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.
```

**Logical reading:** "Intervals [Start1, End1) and [Start2, End2) overlap if and only if Start1 is less than End2 and Start2 is less than End1."

**Concrete example with numbers.** Consider two events:

```prolog
event(e1, "Team Meeting", 9, 0, 10, 0).    %% 9:00-10:00 -> [540, 600)
event(e2, "Study Group",  9, 30, 11, 0).    %% 9:30-11:00 -> [570, 660)
```

Converting to minutes: S₁ = 540, E₁ = 600, S₂ = 570, E₂ = 660.

Test: S₁ < E₂ → 540 < 660 ✓ and S₂ < E₁ → 570 < 600 ✓

```prolog
?- time_to_minutes(9, 0, S1), time_to_minutes(10, 0, E1),
   time_to_minutes(9, 30, S2), time_to_minutes(11, 0, E2),
   intervals_overlap(S1, E1, S2, E2).
S1 = 540, E1 = 600, S2 = 570, E2 = 660.
true.
```

**Non-overlapping example:**

```prolog
event(e3, "Lunch", 12, 0, 13, 0).          %% 12:00-13:00 -> [720, 780)
```

Test against e1: S₁ < E₃ → 540 < 780 ✓ but S₃ < E₁ → 720 < 600 ✗

```prolog
?- intervals_overlap(540, 600, 720, 780).
false.   %% 720 >= 600, second condition fails
```

### 6.5.3 Slot Freedom — Negation as Failure with FOL

A time slot is free if no existing event overlaps with it. This is expressed using the **Closed World Assumption (CWA)**: if an overlap cannot be proved, then no overlap exists.

**FOL formalization:**

> free(S, E, Events) ← ¬∃ e ∈ Events : overlap([S, E), interval(e))

Equivalently:

> ∀ S, E, Events : free(S, E, Events) ↔ (∀ e ∈ Events : ¬overlap(S, E, start(e), end(e)))

**Prolog implementation using Negation as Failure (NAF):**

```prolog
slot_is_free(Start, End, Events) :-
    \+ slot_conflicts_with_events(Start, End, Events).
```

Where `slot_conflicts_with_events` implements existential search — it succeeds if *at least one* event overlaps:

```prolog
slot_conflicts_with_events(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM), Events),
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(Start, End, ExStart, ExEnd),
    !.  %% One witness suffices (existential)
```

**Logical reading:** "A slot [Start, End) conflicts with Events if there exists an event e in Events such that [Start, End) overlaps with interval(e). The cut implements the existential — one witness suffices."

**Query examples:**

```prolog
%% Empty schedule — every slot is free
?- slot_is_free(480, 540, []).
true.

%% Slot 10:00-10:30 free when event is 9:00-10:00?
?- slot_is_free(600, 630, [event(e1, "M", 9, 0, 10, 0)]).
true.

%% Slot 9:00-9:30 free when event is 9:00-10:00?
?- slot_is_free(540, 570, [event(e1, "M", 9, 0, 10, 0)]).
false.   %% Overlap: 540 < 600 and 540 < 570
```

### 6.5.4 Hard Constraint Violation Rules — FOL Formalization

Each hard constraint violation is modelled as an independent inference rule using `violation/4`. Violations are **knowledge objects** — terms that can be collected, inspected, and explained.

**Rule 1: No Overlap Violation**

> ∀ e₁ ∈ E, ∀ e₂ ∈ E : e₁ ≠ e₂ ∧ overlap(e₁, e₂) → violation(no\_overlap, e₁, E, overlap(id(e₂), title(e₂)))

**Logical reading:** "For all events e₁ and e₂ in E, if e₁ and e₂ are different and their intervals overlap, then an overlap violation is inferred."

```prolog
violation(no_overlap, event(Id, _T, SH, SM, EH, EM, _P, _Ty), AllEvents,
          overlap(OtherId, OtherTitle)) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    member(event(OtherId, OtherTitle, OSH, OSM, OEH, OEM, _, _), AllEvents),
    OtherId \= Id,
    time_to_minutes(OSH, OSM, OStart),
    time_to_minutes(OEH, OEM, OEnd),
    OStart < End,
    Start < OEnd.
```

```prolog
?- violation(no_overlap,
     event(e1, "Meeting", 9, 0, 10, 0, 7, meeting),
     [event(e2, "Study", 9, 30, 11, 0, 8, study)],
     Reason).
Reason = overlap(e2, "Study").
```

**Rule 2: Before Working Hours Violation**

> ∀ e ∈ E : start(e) < WorkStart → violation(before\_working\_hours, e, \_, before\_working\_hours)

```prolog
violation(before_working_hours, event(_Id, _T, SH, SM, _EH, _EM, _P, _Ty), _AllEvents,
          before_working_hours) :-
    time_to_minutes(SH, SM, Start),
    fact(working_hours_start, WorkStart),
    Start < WorkStart.
```

```prolog
?- violation(before_working_hours,
     event(e1, "Early", 5, 0, 6, 0, 5, meeting), [], Reason).
Reason = before_working_hours.   %% 300 < 360

?- violation(before_working_hours,
     event(e1, "Normal", 9, 0, 10, 0, 5, meeting), [], Reason).
false.   %% 540 >= 360
```

**Rule 3: After Working Hours Violation**

> ∀ e ∈ E : end(e) > WorkEnd → violation(after\_working\_hours, e, \_, after\_working\_hours)

```prolog
violation(after_working_hours, event(_Id, _T, _SH, _SM, EH, EM, _P, _Ty), _AllEvents,
          after_working_hours) :-
    time_to_minutes(EH, EM, End),
    fact(working_hours_end, WorkEnd),
    End > WorkEnd.
```

```prolog
?- violation(after_working_hours,
     event(e1, "Late", 23, 0, 23, 30, 5, meeting), [], Reason).
Reason = after_working_hours.   %% 1410 > 1380
```

**Rule 4: Positive Duration Violation**

> ∀ e ∈ E : end(e) ≤ start(e) → violation(positive\_duration, e, \_, invalid\_duration)

```prolog
violation(positive_duration, event(_Id, _T, SH, SM, EH, EM, _P, _Ty), _AllEvents,
          invalid_duration) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    End =< Start.
```

```prolog
?- violation(positive_duration,
     event(e1, "Bad", 10, 0, 9, 0, 5, meeting), [], Reason).
Reason = invalid_duration.   %% 540 =< 600

?- violation(positive_duration,
     event(e1, "Good", 9, 0, 10, 0, 5, meeting), [], Reason).
false.   %% 600 > 540, valid duration
```

**Querying all violations for an event:**

```prolog
?- violation(ViolationType,
     event(e1, "Bad Event", 5, 0, 4, 0, 5, meeting), [], Reason).
ViolationType = before_working_hours, Reason = before_working_hours ;
ViolationType = positive_duration, Reason = invalid_duration.
```

### 6.5.5 Soft Cost Rules — Formal Reading

Soft constraints produce a **cost** that the solver minimizes. They express preferences as knowledge.

**Preferred time cost:**

> ∀ e : type(e) = τ ∧ preferred\_window(τ, WS, WE) ∧ start(e) ∈ [WS, WE] → cost(e) = 0
> ∀ e : type(e) = τ ∧ ¬(∃ w : preferred\_window(τ, w) ∧ start(e) ∈ w) → cost(e) = min(|start(e) − WS| / 30, MaxPenalty)

```prolog
soft_cost(preferred_time, event(_Id, _T, SH, SM, _EH, _EM, _P, Type),
          _AllEvents, _Prefs, Cost) :-
    time_to_minutes(SH, SM, Start),
    (   preferred_window(Type, WinStart, WinEnd),
        Start >= WinStart, Start =< WinEnd
    ->  Cost = 0
    ;   preference_penalty(Type, MaxPenalty)
    ->  (   preferred_window(Type, WinStart, _)
        ->  Diff is abs(Start - WinStart),
            Cost is min(Diff // 30, MaxPenalty)
        ;   Cost = 0
        )
    ;   Cost = 0
    ).
```

```prolog
%% Meeting at 9:00 — within preferred window (540-1020)
?- soft_cost(preferred_time, event(e1,"M",9,0,10,0,7,meeting), [], [], Cost).
Cost = 0.

%% Meeting at 20:00 — outside preferred window
?- soft_cost(preferred_time, event(e1,"M",20,0,21,0,7,meeting), [], [], Cost).
Cost = 10.  %% max penalty
```

**Buffer proximity cost:**

> ∀ e₁, e₂ ∈ E : e₁ ≠ e₂ ∧ |end(e₁) − start(e₂)| < Buffer → cost\_buffer(e₂) += 3

**Daily overload cost:**

> |E| > HardLimit → cost = (|E| − HardLimit) × 5
> |E| > SoftLimit → cost = (|E| − SoftLimit) × 2

**Priority scheduling cost:**

> ∀ e : priority(e) ≥ 8 ∧ start(e) ∉ [540, 1020] → cost(e) = (priority(e) − 7) × 3

### 6.5.6 Reified Conflicts — Deep Explanation

In the KRR architecture, conflicts are **reified** — they are first-class terms carrying a structured reason explaining *why* the conflict exists. Reification turns a relationship into a data object that can be stored, queried, and manipulated.

```prolog
conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), Reason) :-
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(NewStart, NewEnd, ExStart, ExEnd),
    Reason = overlap(ID, Title, SH, SM, EH, EM).
```

**FOL reading:**

> ∀ ns, ne, e : overlap([ns, ne), interval(e)) → conflict(interval(ns, ne), e, overlap(id(e), title(e), time(e)))

**Query: "Why does the new interval 9:30-11:00 conflict with existing events?"**

```prolog
?- conflict(interval(570, 660), event(e1, "Meeting", 9, 0, 10, 0), Reason).
Reason = overlap(e1, "Meeting", 9, 0, 10, 0).

%% The Reason term explains: "The conflict exists because event e1
%% ('Meeting', 9:00-10:00) overlaps with the proposed interval [570, 660)."
```

**Query: "Find ALL events that conflict with the proposed interval:"**

```prolog
?- findall(conflict(ID, Reason),
     conflict(interval(570, 660), event(ID, _, _, _, _, _), Reason),
     AllConflicts).
AllConflicts = [conflict(e1, overlap(e1, "Meeting", 9, 0, 10, 0))].
```

### 6.5.7 Displacement Cost and Priority Loss Rules

The A* search uses two cost rules with formal readings:

**Displacement cost g(n):**

> g(n) = Σ\_{e ∈ moved} \[MovePenalty + (|NewStart(e) − OldStart(e)| / 60) × ShiftWeight + Priority(e) × PriorityFactor\]

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

**Priority loss heuristic h(n):**

> h(n) = Σ\_{e ∈ conflicts} \[Priority(e)² × W\_strategy\]

```prolog
event_priority_loss(event(_Id, _T, _SH, _SM, _EH, _EM, Priority, _Ty), Strategy, Loss) :-
    strategy_weight(Strategy, W),
    Loss is Priority * Priority * W.
```

```prolog
?- event_priority_loss(event(e1,"M",9,0,10,0,8,meeting), balanced, Loss).
Loss = 64.0.   %% 8^2 x 1.0

?- event_priority_loss(event(e1,"M",9,0,10,0,3,party), maximize_quality, Loss).
Loss = 18.0.   %% 3^2 x 2.0
```

---

## 6.6 Constraints — First-Class Knowledge Objects (Layer 3)

### 6.6.1 What Are First-Class Constraints?

In many systems, constraints are merely procedural checks — boolean functions that return true or false and have no independent existence. In the Schedule Assistant's KRR architecture, constraints are fundamentally different: they are **first-class knowledge objects** that exist as data in the knowledge base.

First-class constraints can be:

- **Enumerated**: "What constraints does the system know?" → `constraint(Name, _, _).`
- **Queried**: "What is the condition for no_overlap?" → `constraint(no_overlap, Args, Condition).`
- **Combined**: Multiple constraints can be composed dynamically at runtime.
- **Inspected**: The condition of each constraint is a Prolog goal term that can be examined.
- **Reasoned about independently**: Constraint satisfaction can be tested without invoking the scheduler.

This is a direct consequence of the separation principle: constraints are **knowledge** (they declare what must be true), not **control** (they don't dictate how the solver works).

### 6.6.2 Constraint Declaration (`constraint/3`)

Each constraint in the scheduler module is declared using the `constraint/3` predicate:

```prolog
constraint(Name, Args, Condition).
```

- **Name**: Atom identifying the constraint (e.g., `no_overlap`, `within_bounds`)
- **Args**: List of arguments the constraint operates on
- **Condition**: A Prolog goal term (stored as data) that evaluates to true when the constraint is satisfied

**Scheduler constraints:**

```prolog
%% A slot must not overlap any existing event.
constraint(no_overlap, [Start, End, Events],
    \+ slot_conflicts_with_events(Start, End, Events)).

%% A slot must lie within the scheduling window.
constraint(within_bounds, [Start, End, MinStart, MaxEnd],
    (Start >= MinStart, End =< MaxEnd)).

%% End time must be strictly after start time.
constraint(positive_duration, [Start, End],
    End > Start).
```

**FOL readings:**

> no\_overlap(S, E, Events) ↔ ¬∃ e ∈ Events : overlap([S, E), interval(e))
> within\_bounds(S, E, Min, Max) ↔ S ≥ Min ∧ E ≤ Max
> positive\_duration(S, E) ↔ E > S

### 6.6.3 Generic Constraint Checker (`check_constraint/2` using `call/1`)

A generic `check_constraint/2` predicate evaluates any named constraint by retrieving its condition from the knowledge base and executing it via `call/1`:

```prolog
check_constraint(Name, Args) :-
    constraint(Name, Args, Condition),
    call(Condition).
```

This is a **higher-order** pattern: the constraint's condition is stored as data (a Prolog goal term) and executed via `call/1`. This separates constraint *declaration* from constraint *enforcement*. The checker does not know what the constraints are — it simply looks them up and evaluates them.

**Composed constraint validation:**

```prolog
check_all_slot_constraints(Start, End, MinStart, MaxEnd, Events) :-
    check_constraint(positive_duration, [Start, End]),
    check_constraint(within_bounds,     [Start, End, MinStart, MaxEnd]),
    check_constraint(no_overlap,        [Start, End, Events]).
```

### 6.6.4 Querying and Reasoning About Constraints

Because constraints are first-class knowledge objects, the system can answer questions *about* its constraints — not just apply them.

**Enumerating all constraints:**

```prolog
%% "What constraints does the system know?"
?- constraint(Name, _, _).
Name = no_overlap ;
Name = within_bounds ;
Name = positive_duration.
```

**Inspecting a constraint's structure:**

```prolog
%% "What arguments does the no_overlap constraint require?"
?- constraint(no_overlap, Args, _).
Args = [_Start, _End, _Events].

%% "What is the condition for within_bounds?"
?- constraint(within_bounds, Args, Condition).
Args = [_Start, _End, _MinStart, _MaxEnd],
Condition = (_Start >= _MinStart, _End =< _MaxEnd).
```

**Testing individual constraints on specific data:**

```prolog
%% "Does slot [480, 540] satisfy positive_duration?"
?- check_constraint(positive_duration, [480, 540]).
true.   %% 540 > 480

%% "Does slot [480, 540] satisfy within_bounds for 8:00-18:00?"
?- check_constraint(within_bounds, [480, 540, 480, 1080]).
true.   %% 480 >= 480 and 540 =< 1080

%% "Does slot [480, 540] satisfy no_overlap with empty schedule?"
?- check_constraint(no_overlap, [480, 540, []]).
true.

%% "Does slot [540, 600] pass all constraints?"
?- check_all_slot_constraints(540, 600, 480, 1080,
     [event(e1, "M", 9, 30, 10, 30)]).
false.   %% Violates no_overlap
```

**Composing constraints dynamically:**

```prolog
%% "Which constraints does this slot FAIL?"
?- constraint(Name, _, _),
   \+ (   Name = no_overlap,
          check_constraint(Name, [540, 600, [event(e1,"M",9,0,10,0)]])
      ;   Name = within_bounds,
          check_constraint(Name, [540, 600, 480, 1080])
      ;   Name = positive_duration,
          check_constraint(Name, [540, 600])
      ).
Name = no_overlap.   %% This is the failing constraint
```

### 6.6.5 Hard/Soft Constraint System

The constraint solver distinguishes between two categories of constraints, each with distinct semantics:

**Hard constraints — binary (pass/fail), checked via `check_hard/2`:**

```prolog
check_hard(no_overlap, [Event, AllEvents]) :-
    \+ violation(no_overlap, Event, AllEvents, _).

check_hard(before_working_hours, [Event]) :-
    \+ violation(before_working_hours, Event, [], _).

check_hard(after_working_hours, [Event]) :-
    \+ violation(after_working_hours, Event, [], _).

check_hard(positive_duration, [Event]) :-
    \+ violation(positive_duration, Event, [], _).
```

**FOL reading of hard constraint satisfaction:**

> satisfies(e, C) ↔ ¬∃ reason : violation(C, e, E, reason)

**Soft constraints — return a numeric penalty cost via `evaluate_soft/3`:**

```prolog
evaluate_soft(preferred_time,    [Event, AllEvents, Prefs], Cost) :-
    soft_cost(preferred_time, Event, AllEvents, Prefs, Cost).

evaluate_soft(buffer_proximity,  [Event, AllEvents, _Prefs], Cost) :-
    soft_cost(buffer_proximity, Event, AllEvents, _, Cost).

evaluate_soft(daily_overload,    [_Event, AllEvents, _Prefs], Cost) :-
    soft_cost(daily_overload, _, AllEvents, _, Cost).

evaluate_soft(priority_schedule, [Event, _AllEvents, _Prefs], Cost) :-
    soft_cost(priority_schedule, Event, _, _, Cost).
```

**Operator syntax for natural-language constraint reasoning:**

```prolog
?- event(e1, "M", 9, 0, 10, 0, 7, meeting) satisfies positive_duration.
true.

?- event(e1, "Bad", 10, 0, 9, 0, 5, meeting) violates positive_duration.
true.

?- event(e1, "Late", 20, 0, 21, 0, 7, meeting) penalized_by soft(preferred_time, Cost).
Cost = 10.
```

### 6.6.6 Constraint Classification Summary

| # | Constraint | Type | FOL Rule | Module |
|---|---|---|---|---|
| 1 | No time overlap | Hard | ∀ eᵢ, eⱼ ∈ E : eᵢ ≠ eⱼ → ¬overlap(eᵢ, eⱼ) | Both |
| 2 | Before working hours | Hard | ∀ e ∈ E : start(e) ≥ 360 | `constraint_solver.pl` |
| 3 | After working hours | Hard | ∀ e ∈ E : end(e) ≤ 1380 | `constraint_solver.pl` |
| 4 | Within bounds | Hard | ∀ slot : start ≥ MinStart ∧ end ≤ MaxEnd | `scheduler.pl` |
| 5 | Valid duration | Hard | ∀ e ∈ E : end(e) > start(e) | Both |
| 6 | Preferred time window | Soft | start(e) ∈ preferred(type(e)) → cost = 0 | `constraint_solver.pl` |
| 7 | Buffer proximity | Soft | |end(eᵢ) − start(eⱼ)| < 15 → cost += 3 | `constraint_solver.pl` |
| 8 | Daily overload | Soft | |E| > 6 → cost += (|E| − 6) × 2 | `constraint_solver.pl` |
| 9 | Priority scheduling | Soft | priority ≥ 8 ∧ start ∉ [540,1020] → cost += (p−7)×3 | `constraint_solver.pl` |

**Preferred time windows by event type:**

| Event Type | Preferred Window | Penalty If Outside |
|---|---|---|
| Meeting | 09:00–17:00 | min(distance\_from\_9am / 30, 10) |
| Study | 08:00–12:00 or 14:00–18:00 | 5 |
| Exercise | Before 08:00 or after 17:00 | 3 |
| Other | No preference | 0 |

---

## 6.7 Meta-Interpreter — Core Reasoning Mechanism (Layer 4)

### 6.7.1 What is a Meta-Interpreter and Why It Matters for KRR

A **meta-interpreter** is a program that interprets programs — in this case, a Prolog program that interprets Prolog programs. The classic meta-interpreter pattern `demo/1` succeeds if and only if a goal is **provable from the knowledge base**. When you write `demo(Goal)`, you are asking: "Is Goal provable given the current knowledge?"

This is fundamentally different from simply calling `Goal` directly. A direct call uses Prolog's built-in inference engine *implicitly*. A meta-interpreter call makes the reasoning process **explicit and controllable**. This enables:

1. **Introspection**: The system can reason about *what it can prove*, not just compute answers.
2. **Explanation**: By tracing `demo/1` calls, the system can explain *why* a conclusion was reached.
3. **Custom inference control**: The meta-interpreter can be extended with tracing, logging, or confidence scoring without modifying the underlying rules.
4. **Uniform interface**: Both scheduler rules and constraint rules are provable through the same `demo/1` mechanism.

The meta-interpreter embodies the separation principle: the rules (knowledge) declare what is true, while `demo/1` (control) determines how to derive proofs.

### 6.7.2 The Classic `demo/1` Pattern

The meta-interpreter is defined by structural induction on the form of the goal:

**Base case — truth:**

```prolog
demo(true).
```

*Logical reading:* "The proposition `true` is always provable." ⊢ true

**Conjunction — prove both subgoals:**

```prolog
demo((A, B)) :- demo(A), demo(B).
```

*Logical reading:* "A ∧ B is provable iff A is provable and B is provable."

> ⊢ A ∧ ⊢ B → ⊢ (A ∧ B)

**Disjunction — prove either subgoal:**

```prolog
demo((A ; _)) :- demo(A).
demo((_ ; B)) :- demo(B).
```

*Logical reading:* "A ∨ B is provable iff A is provable or B is provable."

> ⊢ A → ⊢ (A ∨ B)
> ⊢ B → ⊢ (A ∨ B)

**Negation as failure:**

```prolog
demo(\+ A) :- \+ demo(A).
```

*Logical reading:* "¬A is provable iff A is not provable (Closed World Assumption)."

**Arithmetic and comparison — delegate to Prolog:**

```prolog
demo(A is B)  :- A is B.
demo(A < B)   :- A < B.
demo(A > B)   :- A > B.
demo(A >= B)  :- A >= B.
demo(A =< B)  :- A =< B.
demo(A =:= B) :- A =:= B.
demo(A =\= B) :- A =\= B.
```

**List reasoning:**

```prolog
demo(member(X, L)) :- member(X, L).
```

**Constraint check — prove by verifying the named constraint:**

```prolog
demo(check_constraint(Name, Args)) :-
    check_constraint(Name, Args).
```

**Catch-all — prove by calling any defined predicate:**

```prolog
demo(Goal) :-
    Goal \= true,
    Goal \= (_ , _),
    Goal \= (_ ; _),
    Goal \= (\+ _),
    Goal \= (_ is _),
    ... %% guard checks for all special forms
    call(Goal).
```

### 6.7.3 How `demo/1` Proves a Goal — Step-by-Step Example

Consider the compound goal: "Is slot [480, 540] free AND does it satisfy the positive_duration constraint?"

```prolog
?- demo((slot_is_free(480, 540, []), check_constraint(positive_duration, [480, 540]))).
```

**Step-by-step decomposition:**

```
demo((slot_is_free(480, 540, []), check_constraint(positive_duration, [480, 540])))
|
+-- Matches: demo((A, B)) :- demo(A), demo(B).
|   where A = slot_is_free(480, 540, [])
|   and   B = check_constraint(positive_duration, [480, 540])
|
+-- Step 1: demo(slot_is_free(480, 540, []))
|   +-- Matches catch-all: demo(Goal) :- ... call(Goal).
|   +-- call(slot_is_free(480, 540, []))
|   +-- slot_is_free(480, 540, []) :- \+ slot_conflicts_with_events(480, 540, [])
|   +-- Events = [] -> no conflicts -> \+ fails to find conflict -> succeeds
|   +-- Result: true
|
+-- Step 2: demo(check_constraint(positive_duration, [480, 540]))
|   +-- Matches: demo(check_constraint(Name, Args)) :- check_constraint(Name, Args).
|   +-- check_constraint(positive_duration, [480, 540])
|   +-- constraint(positive_duration, [480, 540], 540 > 480)
|   +-- call(540 > 480) -> true
|   +-- Result: true
|
+-- Both subgoals proved -> Conjunction proved: true
```

**Example — a goal that fails:**

```prolog
?- demo((slot_is_free(540, 600, [event(e1, "M", 9, 0, 10, 0)]),
         check_constraint(positive_duration, [540, 600]))).
```

```
Step 1: demo(slot_is_free(540, 600, [event(e1, "M", 9, 0, 10, 0)]))
  -> slot_conflicts_with_events(540, 600, [event(e1, "M", 9, 0, 10, 0)])
  -> intervals_overlap(540, 600, 540, 600) -> 540 < 600 and 540 < 600 -> true
  -> \+ true -> false

Result: false (conjunction fails at first subgoal)
```

### 6.7.4 Constraint-Specific Meta-Reasoning (Constraint Solver Extension)

The constraint solver extends `demo/1` with constraint-specific reasoning clauses:

```prolog
%% "Does hard constraint Name hold for Event given AllEvents?"
demo(hard_constraint_holds(Name, Event, AllEvents)) :-
    check_hard(Name, [Event, AllEvents]).

%% "What is the cost of soft constraint Name?"
demo(soft_constraint_cost(Name, Event, AllEvents, Prefs, Cost)) :-
    evaluate_soft(Name, [Event, AllEvents, Prefs], Cost).

%% "Does Event have any violation given AllEvents?"
demo(event_has_violation(Event, AllEvents, Violation)) :-
    violation(_, Event, AllEvents, Violation).

%% "Is Event valid (no violations) given AllEvents?"
demo(event_is_valid(Event, AllEvents)) :-
    \+ violation(_, Event, AllEvents, _).
```

**Query examples:**

```prolog
?- demo(hard_constraint_holds(no_overlap,
     event(e1, "M", 9, 0, 10, 0, 7, meeting), [])).
true.

?- demo(event_is_valid(
     event(e1, "M", 9, 0, 10, 0, 5, meeting), [])).
true.

?- demo(event_has_violation(
     event(e1, "Early", 5, 0, 6, 0, 5, meeting), [], Violation)).
Violation = before_working_hours.

?- demo(soft_constraint_cost(preferred_time,
     event(e1, "Late", 20, 0, 21, 0, 7, meeting), [], [], Cost)).
Cost = 10.
```

### 6.7.5 The `holds/1` Semantic Layer

A semantic alias provides a natural-language-like interface:

```prolog
holds(Proposition) :- demo(Proposition).
```

**Logical reading:** "`Proposition` holds in the current knowledge base" is equivalent to "`Proposition` is provable by `demo/1`." The word "holds" connects the implementation to formal KRR semantics.

```prolog
?- holds(slot_is_free(480, 540, [])).
true.

?- holds(intervals_overlap(480, 540, 500, 600)).
true.

?- holds(check_constraint(no_overlap, [480, 540, []])).
true.
```

### 6.7.6 Comprehensive Query Examples

The meta-interpreter enables a rich set of queries:

```prolog
%% --- Slot reasoning ---
?- demo(slot_is_free(480, 540, [])).
true.

%% --- Overlap reasoning ---
?- demo(intervals_overlap(540, 600, 570, 660)).
true.   %% 540 < 660 and 570 < 600

%% --- Constraint reasoning ---
?- demo(check_constraint(positive_duration, [480, 540])).
true.   %% 540 > 480

%% --- Validity reasoning ---
?- demo(event_is_valid(event(e1, "M", 9, 0, 10, 0, 5, meeting), [])).
true.

%% --- Violation reasoning ---
?- demo(event_has_violation(
     event(e1, "Early", 5, 0, 6, 0, 5, meeting), [], V)).
V = before_working_hours.

%% --- Hard constraint reasoning ---
?- demo(hard_constraint_holds(no_overlap,
     event(e1, "M", 9, 0, 10, 0, 7, meeting), [])).
true.

%% --- Compound reasoning (conjunction) ---
?- demo((event_is_valid(event(e1, "M", 9, 0, 10, 0, 5, meeting), []),
         hard_constraint_holds(no_overlap,
           event(e1, "M", 9, 0, 10, 0, 5, meeting), []))).
true.

%% --- Negation reasoning ---
?- demo(\+ event_has_violation(
     event(e1, "M", 9, 0, 10, 0, 5, meeting), [], _)).
true.
```

---

## 6.8 Solver — Central Reasoning Dispatcher (Layer 5)

### 6.8.1 The `solve/2` Pattern

The solver is the **central entry point** for all reasoning queries. Instead of each predicate computing its result independently, all queries are dispatched through `solve/2`:

```prolog
solve(+Query, -Result)
```

The solver pattern matches on the `Query` term to select the appropriate reasoning strategy. The user is not "calling a function" — they are "asking the solver a question". The solver consults the knowledge base (facts, rules, constraints) to derive an answer. This architecture ensures that **knowledge drives reasoning**: the solver selects which rules and constraints to apply based on the query, but the domain logic lives entirely in the knowledge base.

### 6.8.2 Solver Clauses — Scheduler

```prolog
%% Solve: detect conflicts
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :-
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), _Reason),
        Conflicts
    ).

%% Solve: find free slots (CSP)
solve(find_free_slots(Duration, Events, MinSH, MinSM, MaxEH, MaxEM), FreeSlots) :-
    time_to_minutes(MinSH, MinSM, MinStart),
    time_to_minutes(MaxEH, MaxEM, MaxEnd),
    fact(slot_granularity, Step),
    fact(max_candidate_iterations, MaxIter),
    MaxSlotStart is MaxEnd - Duration,
    findall(
        slot(SH, SM, EH, EM),
        (   between(0, MaxIter, N),
            SlotStart is MinStart + N * Step,
            SlotStart =< MaxSlotStart,
            SlotEnd is SlotStart + Duration,
            check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events),
            minutes_to_time(SlotStart, SH, SM),
            minutes_to_time(SlotEnd, EH, EM)
        ),
        FreeSlots
    ).

%% Solve: find free ranges
solve(find_free_ranges(Events, MinSH, MinSM, MaxEH, MaxEM), FreeRanges) :- ...

%% Solve: find free days
solve(find_free_days(Duration, EventsByDay, SH, SM, EH, EM), FreeDays) :- ...

%% Solve: find an available slot
solve(find_available_slot(Duration, Events, Bounds, Slot), Slot) :-
    Bounds = bounds(MinSH, MinSM, MaxEH, MaxEM),
    solve(find_free_slots(Duration, Events, MinSH, MinSM, MaxEH, MaxEM), Slots),
    Slots = [Slot|_].

%% Solve: validate a proposed schedule
solve(valid_schedule(SlotStart, SlotEnd, Events, MinStart, MaxEnd), Result) :-
    (   check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events)
    ->  Result = valid
    ;   Result = invalid
    ).
```

### 6.8.3 Solver Clauses — Constraint Solver

```prolog
%% Solve: validate hard constraints
solve(validate_hard(Event, AllEvents), Violations) :-
    findall(V, violation(_, Event, AllEvents, V), Violations).

%% Solve: calculate total soft cost
solve(soft_cost(Event, AllEvents, Preferences), TotalCost) :-
    evaluate_soft(preferred_time,    [Event, AllEvents, Preferences], C1),
    evaluate_soft(buffer_proximity,  [Event, AllEvents, Preferences], C2),
    evaluate_soft(daily_overload,    [Event, AllEvents, Preferences], C3),
    evaluate_soft(priority_schedule, [Event, AllEvents, Preferences], C4),
    TotalCost is C1 + C2 + C3 + C4.

%% Solve: displacement cost g(n)
solve(displacement_cost(OriginalEvents, ModifiedEvents), GCost) :-
    findall(EC, (
        member(OrigEvent, OriginalEvents),
        OrigEvent = event(Id, _, _, _, _, _, _, _),
        member(ModEvent, ModifiedEvents),
        ModEvent = event(Id, _, _, _, _, _, _, _),
        event_displacement_cost(OrigEvent, ModEvent, EC)
    ), Costs),
    sum_list(Costs, GCost).

%% Solve: priority loss h(n)
solve(priority_loss(ConflictingEvents, Strategy), HCost) :-
    findall(Loss, (
        member(Event, ConflictingEvents),
        event_priority_loss(Event, Strategy, Loss)
    ), Losses),
    sum_list(Losses, HCost).

%% Solve: heuristic f(n) = g(n) + h(n)
solve(heuristic(OrigEvents, CurrState, RemConflicts, Strategy), FScore) :-
    solve(displacement_cost(OrigEvents, CurrState), G),
    solve(priority_loss(RemConflicts, Strategy), H),
    FScore is G + H.

%% Solve: find best slot for an event
solve(find_best_slot(Event, AllEvents, MinH, MinM, MaxH, MaxM), BestSlot) :- ...

%% Solve: reschedule
solve(reschedule(NewEvent, ExistingEvents, Strategy, MinH, MinM, MaxH, MaxM), Result) :- ...
```

### 6.8.4 Public API Delegation

All public API predicates are **thin wrappers** that delegate to `solve/2`, ensuring all reasoning flows through the central dispatcher:

```prolog
%% Scheduler
check_conflict(A, B, C, D, E, F) :-
    solve(check_conflict(A, B, C, D, E), F).

find_free_slots(Dur, Evts, MinSH, MinSM, MaxEH, MaxEM, FreeSlots) :-
    solve(find_free_slots(Dur, Evts, MinSH, MinSM, MaxEH, MaxEM), FreeSlots).

%% Constraint Solver
validate_hard_constraints(Event, AllEvents, Violations) :-
    solve(validate_hard(Event, AllEvents), Violations).

calculate_soft_cost(Event, AllEvents, Preferences, TotalCost) :-
    solve(soft_cost(Event, AllEvents, Preferences), TotalCost).

calculate_heuristic(Orig, Curr, Rem, Strat, F) :-
    solve(heuristic(Orig, Curr, Rem, Strat), F).

reschedule_event(NewEvent, ExistingEvents, Strategy, MinH, MinM, MaxH, MaxM, Result) :-
    solve(reschedule(NewEvent, ExistingEvents, Strategy, MinH, MinM, MaxH, MaxM), Result).
```

**Why the solver matters:** Adding new reasoning capabilities requires only adding new `solve/2` clauses — the control mechanism is constant, and only the knowledge changes.

---

## 6.9 Condition-to-Action: Knowledge-Driven Behaviour

### 6.9.1 The Principle

> **"Actions are triggered by logical conditions inferred from the knowledge base, rather than hardcoded control flow."**

In a procedural scheduler, the developer writes `if/else` chains that explicitly dictate behaviour. In the KRR approach, the system first **infers** conditions from the knowledge base (using rules, constraints, and the meta-interpreter), and then **triggers** appropriate actions based on what was inferred. This is a direct application of the **condition-action rule** paradigm from production systems.

### 6.9.2 Condition-Action Rules

**Rule 1: IF conflict detected THEN invoke rescheduling**

*Logical condition:*

> ∃ e ∈ Events : conflict(interval(NewStart, NewEnd), e, Reason)

*Action:* Invoke the constraint solver's rescheduling mechanism.

```prolog
%% Condition: detect conflicts
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :- ...

%% Action: IF Conflicts =/= [] THEN reschedule
%% (In Python orchestration layer:)
%%   if conflicts: result = solve(reschedule(NewEvent, Events, Strategy,...), Result)
```

**Rule 2: IF violation found THEN report specific violations**

*Logical condition:*

> ∃ V : violation(\_, Event, AllEvents, V)

*Action:* Collect all violations and report them.

```prolog
solve(validate_hard(Event, AllEvents), Violations) :-
    findall(V, violation(_, Event, AllEvents, V), Violations).
%% IF Violations = [] THEN event is valid
%% IF Violations =/= [] THEN report each violation
```

**Rule 3: IF all constraints satisfied THEN accept schedule**

*Logical condition:*

> ∀ C ∈ Constraints : satisfies(slot, C)

```prolog
solve(valid_schedule(SlotStart, SlotEnd, Events, MinStart, MaxEnd), Result) :-
    (   check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events)
    ->  Result = valid       %% Action: accept
    ;   Result = invalid     %% Action: reject
    ).
```

**Rule 4: IF no free slot exists THEN report no\_solution**

*Logical condition:*

> ¬∃ slot : free(slot) ∧ fits(slot, duration)

```prolog
%% In solve(reschedule(...), Result):
%%   IF no feasible move exists
%%   THEN Result = result(no_solution, [], 9999)
```

**Rule 5: IF strategy is maximize\_quality AND event is high-priority THEN protect it**

*Logical condition:*

> strategy = maximize\_quality ∧ priority(NewEvent) ≥ 8

*Action:* Adjust cost weights to favour keeping the high-priority event in place.

```prolog
pick_best_option(Strategy, NewPriority, option(move_new, Slot, Cost1),
                 option(place_new, MovedEvents, Cost2), Result) :-
    (   Strategy = maximize_quality
    ->  (   NewPriority >= 8
        ->  AdjCost1 is Cost1 * 2.0,     %% Moving new event = EXPENSIVE
            AdjCost2 is Cost2 * 0.5      %% Keeping it = CHEAP
        ;   AdjCost1 is Cost1 * 0.5,
            AdjCost2 is Cost2 * 1.5
        )
    ;   ...
    ),
    ...
```

### 6.9.3 Comparison with Procedural Approach

**Procedural approach (pseudo-code):**

```python
def schedule_event(new_event, events):
    for event in events:
        if new_event.start < event.end and event.start < new_event.end:
            if new_event.priority > event.priority:
                move_event(event)
            else:
                move_event(new_event)
            return
    events.append(new_event)
```

Conflict detection, priority comparison, and action selection are all interleaved in one function. Changing any rule requires modifying this function.

**KRR approach:**

```prolog
%% Knowledge: what a conflict IS (Layer 2)
conflict(interval(NS, NE), event(ID, T, SH, SM, EH, EM), overlap(ID, T, SH, SM, EH, EM)) :-
    time_to_minutes(SH, SM, ES), time_to_minutes(EH, EM, EE),
    intervals_overlap(NS, NE, ES, EE).

%% Knowledge: what a violation IS (Layer 2)
violation(no_overlap, Event, AllEvents, overlap(OId, OTitle)) :- ...

%% Knowledge: how much displacement costs (Layer 2)
event_displacement_cost(OrigEvent, ModEvent, Cost) :- ...

%% Knowledge: what the strategy prefers (Layer 1)
strategy_weight(maximize_quality, 2.0).

%% Control: solver asks questions and infers actions (Layer 5)
solve(reschedule(NewEvent, ExistingEvents, Strategy, ...), Result) :- ...
```

Each piece of knowledge is independent. Changing what a conflict is does not require changing the solver. Changing strategy weights does not require changing conflict detection. **Knowledge is separated from control.**

---

## 6.10 Free Slot Finding Using Constraint Satisfaction

### 6.10.1 CSP Formulation

The problem of finding available time slots is modelled as a Constraint Satisfaction Problem (CSP):

**Formal CSP definition:**

Let CSP = ⟨V, D, C⟩ where:

> **Variables** V = {SlotStart, SlotEnd}
> **Domain** D(SlotStart) = {MinStart, MinStart + Step, ...}, D(SlotEnd) = {SlotStart + Duration}
> **Constraints** C = {c₁, c₂, c₃} where:

| Constraint | FOL Definition |
|---|---|
| c₁ (fixed duration) | SlotEnd = SlotStart + Duration |
| c₂ (no overlap) | ∀ e ∈ Events : ¬overlap([SlotStart, SlotEnd), interval(e)) |
| c₃ (within bounds) | SlotStart ≥ MinStart ∧ SlotEnd ≤ MaxEnd |

**Solution:** An assignment σ : V → D such that σ satisfies all constraints in C.

### 6.10.2 Generate-and-Test with Named Constraints

The CSP is solved using generate-and-test, checking constraints through **named constraint objects** from Layer 3:

```prolog
solve(find_free_slots(Duration, Events, MinSH, MinSM, MaxEH, MaxEM), FreeSlots) :-
    time_to_minutes(MinSH, MinSM, MinStart),
    time_to_minutes(MaxEH, MaxEM, MaxEnd),
    fact(slot_granularity, Step),
    fact(max_candidate_iterations, MaxIter),
    MaxSlotStart is MaxEnd - Duration,
    findall(
        slot(SH, SM, EH, EM),
        (   between(0, MaxIter, N),
            SlotStart is MinStart + N * Step,
            SlotStart =< MaxSlotStart,
            SlotEnd is SlotStart + Duration,
            check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events),
            minutes_to_time(SlotStart, SH, SM),
            minutes_to_time(SlotEnd, EH, EM)
        ),
        FreeSlots
    ).
```

The constraint validation uses the first-class constraint system:

```prolog
check_all_slot_constraints(Start, End, MinStart, MaxEnd, Events) :-
    check_constraint(positive_duration, [Start, End]),
    check_constraint(within_bounds,     [Start, End, MinStart, MaxEnd]),
    check_constraint(no_overlap,        [Start, End, Events]).
```

**Query example:**

```prolog
?- solve(find_free_slots(60,
     [event(e1, "M", 9, 0, 10, 0)], 8, 0, 12, 0), Slots).
Slots = [slot(8, 0, 9, 0), slot(10, 0, 11, 0), slot(10, 30, 11, 30),
         slot(11, 0, 12, 0)].
```

### 6.10.3 Free Range and Free Day Inference

The system computes contiguous free time ranges (gaps between events):

```prolog
?- solve(find_free_ranges(
     [event(e1, "M", 9, 0, 10, 0), event(e2, "S", 14, 0, 16, 0)],
     8, 0, 18, 0), Ranges).
Ranges = [range(8, 0, 9, 0), range(10, 0, 14, 0), range(16, 0, 18, 0)].
```

**Free day inference rule:**

> free\_day(D) ← ∃ slot : fits(slot, D) ∧ ∀ e ∈ events(D) : ¬overlap(slot, e)

---

## 6.11 A* Rescheduling — Prolog Rules (Brief)

The A* rescheduling algorithm uses solver-dispatched inference rules. **The A* algorithm and its cost functions are described in detail in Chapter 5, Section 1.** Here, we list only the key Prolog rules/predicates that support A* search within the KRR architecture.

**Key predicates:**

| Predicate | Purpose |
|---|---|
| `event_displacement_cost/3` | Computes g(n) cost for moving an individual event |
| `event_priority_loss/3` | Computes h(n) heuristic loss for unresolved conflicts |
| `solve(heuristic(Orig, Curr, Rem, Strategy), FScore)` | Computes f(n) = g(n) + h(n) via the solver |
| `solve(displacement_cost(Orig, Mod), G)` | Aggregates displacement cost across all moved events |
| `solve(priority_loss(Conflicts, Strategy), H)` | Aggregates priority loss across remaining conflicts |
| `astar_search/6` | State-space search selecting minimum f(n) states |

**Composable reasoning:** The A* search calls `solve/2` internally (e.g., `solve(find_best_slot(...), Slot)` and `solve(heuristic(...), FScore)`), demonstrating that search strategies can invoke other reasoning sub-tasks through the same unified interface. The search logic (control) is separated from the cost computation rules (knowledge).

---

## 6.12 Practical Example: Query-Based Reasoning

This section demonstrates how the KRR system answers real-world scheduling questions using Prolog queries. Each scenario shows the user's question, the corresponding query, and the system's response.

### Scenario 1: "Is There a Conflict?"

**Given:** An existing event "Team Meeting" 09:00–10:00. A user wants to add "Study" 09:30–11:00.

```prolog
?- solve(check_conflict(9, 30, 11, 0,
     [event(e1, "Team Meeting", 9, 0, 10, 0)]), Conflicts).
Conflicts = [conflict(e1, "Team Meeting", 9, 0, 10, 0)].
```

**Logical derivation:**
- NewStart = 570, NewEnd = 660
- MeetingStart = 540, MeetingEnd = 600
- 570 < 600 ∧ 540 < 660 → overlap confirmed
- ∴ conflict(e1, "Team Meeting", 9, 0, 10, 0) ∈ Conflicts

### Scenario 2: "Why is This Event Invalid?"

**Given:** An event scheduled at 5:00 AM with end time before start time.

```prolog
?- solve(validate_hard(
     event(e1, "Bad Event", 5, 0, 4, 0, 5, meeting), []), Violations).
Violations = [before_working_hours, invalid_duration].
```

**Explanation:** The system found two violations:
1. `before_working_hours`: 300 (5:00 AM) < 360 (6:00 AM working hours start)
2. `invalid_duration`: End (240 = 4:00 AM) ≤ Start (300 = 5:00 AM)

Each violation is a **knowledge object** that can be further queried:

```prolog
?- violation(VType, event(e1, "Bad Event", 5, 0, 4, 0, 5, meeting), [], Reason).
VType = before_working_hours, Reason = before_working_hours ;
VType = positive_duration, Reason = invalid_duration.
```

### Scenario 3: "What Slots Are Free?"

**Given:** Events at 09:00–10:00 and 11:00–12:00. Find 30-minute free slots between 08:00–13:00.

```prolog
?- solve(find_free_slots(30,
     [event(e1, "M", 9, 0, 10, 0), event(e2, "S", 11, 0, 12, 0)],
     8, 0, 13, 0), Slots).
Slots = [slot(8, 0, 8, 30), slot(8, 30, 9, 0),
         slot(10, 0, 10, 30), slot(10, 30, 11, 0),
         slot(12, 0, 12, 30), slot(12, 30, 13, 0)].
```

### Scenario 4: "Does This Event Satisfy All Constraints?"

```prolog
%% Check hard constraints
?- demo(event_is_valid(
     event(e1, "Meeting", 9, 0, 10, 0, 7, meeting), [])).
true.

%% Check specific constraints using operator syntax
?- event(e1, "Meeting", 9, 0, 10, 0, 7, meeting) satisfies positive_duration.
true.

?- event(e1, "Meeting", 9, 0, 10, 0, 7, meeting) satisfies no_overlap.
true.

%% Check soft constraint cost
?- demo(soft_constraint_cost(preferred_time,
     event(e1, "Meeting", 9, 0, 10, 0, 7, meeting), [], [], Cost)).
Cost = 0.   %% Within preferred window
```

### Scenario 5: "What Does the System Know About Constraints?"

**Introspection queries:**

```prolog
%% "What constraints does the system define?"
?- constraint(Name, _, _).
Name = no_overlap ;
Name = within_bounds ;
Name = positive_duration.

%% "What metadata describes the overlap rule?"
?- statement(overlap_rule, Type, Description).
Type = inference_rule,
Description = 'Two intervals overlap iff S1 < E2 and S2 < E1'.

%% "List all inference rules the system knows:"
?- statement(Name, inference_rule, Desc).
Name = overlap_rule, Desc = 'Two intervals overlap iff S1 < E2 and S2 < E1' ;
Name = free_slot_rule, Desc = 'A slot is free if no event overlaps it' ;
...

%% "What is the current slot granularity?"
?- fact(slot_granularity, V).
V = 30.

%% "What preferred windows exist for meetings?"
?- preferred_window(meeting, Start, End).
Start = 540, End = 1020.   %% 9:00 to 17:00
```

### Scenario 6: "What is the Total Cost of This Schedule?"

```prolog
?- solve(soft_cost(
     event(e1, "Late Meeting", 20, 0, 21, 0, 7, meeting),
     [event(e2, "Study", 19, 0, 20, 0, 8, study)],
     []), TotalCost).
TotalCost = 13.   %% preferred_time(10) + buffer_proximity(3)
```

---

## 6.13 System Architecture

```
┌──────────────────────────────────────────────┐
│            User Interface (Frontend)          │
└─────────────────┬────────────────────────────┘
                  │ REST API
┌─────────────────▼────────────────────────────┐
│      Scheduling Service (Python)              │
│    - Request handling & orchestration         │
│    - User profile & priority management       │
└─────────────────┬────────────────────────────┘
                  │ pyswip interface
┌─────────────────▼────────────────────────────┐
│          PrologService (Python)               │
│    - Prolog engine initialisation             │
│    - Query construction & result parsing      │
│    - Python fallback implementations          │
└─────────────────┬────────────────────────────┘
                  │ consult / solve/2
┌─────────────────▼────────────────────────────┐
│   SWI-Prolog KRR Engine (6-Layer Architecture)│
│  ┌────────────────┐  ┌─────────────────────┐ │
│  │ scheduler.pl    │  │ constraint_solver.pl│ │
│  │                 │  │                     │ │
│  │ Layer 0: Ops    │  │ Layer 0: Ops        │ │
│  │ Layer 1: Facts  │  │ Layer 1: Facts      │ │
│  │ Layer 2: Rules  │  │ Layer 2: Rules      │ │
│  │ Layer 3: Constr │  │ Layer 3: Constr     │ │
│  │ Layer 4: Meta   │  │ Layer 4: Meta       │ │
│  │ Layer 5: Solver │  │ Layer 5: Solver     │ │
│  └────────────────┘  └─────────────────────┘ │
└──────────────────────────────────────────────┘
```

**Data flow:** Python orchestration → pyswip → solve/2 → rules/constraints/meta-interpreter → results back to Python. The Python layer never directly encodes scheduling logic — it only asks questions. All domain reasoning lives in Prolog.

---

## 6.14 Summary of KRR Techniques Used

| Technique | Application in Project | Module |
|---|---|---|
| **Facts (Knowledge Base)** | Domain constants (`fact/2`), preference windows, strategy weights — all knowledge separated from inference | Both |
| **Inference Rules** | Declarative rules for conflict detection, violation checking, cost computation (`conflict/3`, `violation/4`, `soft_cost/5`) | Both |
| **First-Order Logic** | Event representation as structured terms; universal/existential quantification over events, slots, and constraints | Both |
| **Resolution** | Interval overlap detection via negation of non-overlap condition with De Morgan's law derivation | `scheduler.pl` |
| **Reification** | Conflicts and violations represented as first-class terms carrying structured reasons | Both |
| **Named Constraints** | First-class constraint objects (`constraint/3`, `check_hard/2`, `evaluate_soft/3`) that can be enumerated, queried, and composed | Both |
| **Hard/Soft Constraint Separation** | Hard constraints (must satisfy) vs. soft constraints (penalised preferences) with distinct semantics | `constraint_solver.pl` |
| **CSP (Constraint Satisfaction)** | Free slot finding with domain constraints and conflict-free filtering via generate-and-test | `scheduler.pl` |
| **Custom Operators** | Domain-specific syntax (`overlaps_with`, `satisfies`, `violates`, `penalized_by`) for readable propositions | Both |
| **Meta-Interpreter (`demo/1`)** | Explicit provability reasoning; step-by-step goal decomposition; custom inference control | Both |
| **`holds/1` Semantic Layer** | Natural-language-like interface for provability queries | Both |
| **Metadata (`statement/3`, `rule/3`)** | Self-describing knowledge entries for introspection and explainability | Both |
| **Central Solver (`solve/2`)** | Unified reasoning entry point; all queries dispatched through solver pattern matching | Both |
| **Condition-to-Action** | Logical conditions inferred from knowledge base trigger actions (rescheduling, validation, acceptance) | Both |
| **A* Search Algorithm** | Optimal rescheduling with f(n) = g(n) + h(n) via composable solver calls | `constraint_solver.pl` |
| **Negation as Failure** | `\+` operator for proving non-overlap and implementing closed-world reasoning | Both |
| **Closed-World Assumption** | If overlap/violation cannot be proved, it is assumed to not exist | Both |

---

## 6.15 References

1. Russell, S., & Norvig, P. (2021). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson. Chapter 3: Solving Problems by Searching — A* Search Algorithm, admissible heuristics, and optimality proofs. Chapter 6: Constraint Satisfaction Problems. Chapter 8: First-Order Logic.

2. Bratko, I. (2012). *Prolog Programming for Artificial Intelligence* (4th ed.). Addison-Wesley. Chapter 4: First-Order Logic in Prolog. Chapter 14: Constraint Logic Programming. Chapter 15: Meta-Interpreters.

3. Sterling, L., & Shapiro, E. (1994). *The Art of Prolog* (2nd ed.). MIT Press. Chapter 11: Searching — Prolog-based search strategies including best-first and A* search implementations. Chapter 17: Meta-Interpreters.

4. Rossi, F., van Beek, P., & Walsh, T. (2006). *Handbook of Constraint Programming*. Elsevier. Chapter 1: Introduction to Constraint Satisfaction — Formal CSP definition used to model the free-slot finding problem.

5. Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Transactions on Systems Science and Cybernetics*, 4(2), 100–107.

6. Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM*, 26(11), 832–843.

7. Brachman, R., & Levesque, H. (2004). *Knowledge Representation and Reasoning*. Morgan Kaufmann. Chapter 2: Representing Knowledge. Chapter 5: First-Order Logic. Chapter 10: Meta-Reasoning.

8. SWI-Prolog Documentation (2024). *SWI-Prolog Reference Manual*. Retrieved from https://www.swi-prolog.org/pldoc/doc_for?object=manual

9. pyswip Documentation (2024). *pyswip — Python-SWI-Prolog Bridge*. Retrieved from https://github.com/yuce/pyswip
