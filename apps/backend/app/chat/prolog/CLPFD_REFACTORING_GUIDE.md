# CLP(FD) Refactoring Guide: Pure Declarative Meta-Interpreters

## Overview

This document explains the refactoring of `constraint_solver_krr.pl` and `scheduler.pl` to implement **pure declarative meta-interpreters** using **Constraint Logic Programming over Finite Domains (CLP(FD))**.

## What Changed: From Procedural to Declarative

### Before: Procedural Arithmetic
```prolog
% OLD: Procedural calculation
generate_candidate_slot(MinStart, MaxEnd, Duration, SH, SM, EH, EM) :-
    MaxSlotStart is MaxEnd - Duration,        % Arithmetic evaluation
    between_step(MinStart, MaxSlotStart, 30, SlotStart),  % Iterative generation
    SlotEnd is SlotStart + Duration,          % More arithmetic
    SlotEnd =< MaxEnd,                        % Comparison
    ...
```

### After: Declarative Constraints
```prolog
% NEW: Declarative constraint specification
generate_candidate_slot(MinStart, MaxEnd, Duration, SH, SM, EH, EM) :-
    SlotStart in MinStart..MaxEnd,            % Constraint: domain declaration
    SlotEnd in MinStart..MaxEnd,              % Constraint: domain declaration
    SlotEnd #= SlotStart + Duration,          % Constraint: relationship
    SlotEnd #=< MaxEnd,                       % Constraint: boundary
    SlotStart #>= MinStart,                   % Constraint: boundary
    SlotStart mod 30 #= 0,                    % Constraint: grid alignment
    label([SlotStart, SlotEnd]),              % Search: find solution
    ...
```

## Key Differences: Declarative vs Procedural

| Aspect | Procedural (OLD) | Declarative (NEW) |
|--------|------------------|-------------------|
| **Philosophy** | "How to compute" | "What must be true" |
| **Operators** | `is`, `<`, `>`, `=<`, `>=` | `#=`, `#<`, `#>`, `#=<`, `#>=`, `in` |
| **Control** | Explicit iteration (`between`, loops) | Implicit search (`label/1`) |
| **Reasoning** | Arithmetic evaluation | Constraint satisfaction |
| **Proof** | Computational steps | Logical derivation |

## Meta-Interpreter Architecture

Both files implement **meta-interpreters** that:

1. **Build proof trees** showing reasoning chains
2. **Use declarative knowledge** (facts and rules)
3. **Perform logical inference** (backward chaining)
4. **Generate explanations** (proof traces)

### Meta-Interpreter Core (`prove/3`)

```prolog
% The meta-interpreter performs logical inference
prove(Goal, KB, Proof) :-
    % Base cases: facts and axioms
    % Recursive cases: rules and constraints
    % Builds proof tree showing HOW conclusion was reached
```

## CLP(FD) Refactorings

### 1. Temporal Constraints

**Before:**
```prolog
temporal_relation(before(T1, T2)) :- T1 < T2.
temporal_relation(overlaps(interval(S1, E1), interval(S2, E2))) :-
    S1 < E2, S2 < E1.
```

**After:**
```prolog
temporal_relation(before(T1, T2)) :- T1 #< T2.
temporal_relation(overlaps(interval(S1, E1), interval(S2, E2))) :-
    S1 #< E2, S2 #< E1.  % Declarative constraints!
```

### 2. Working Hours Constraint

**Before:**
```prolog
satisfies_constraint_logic(..., within_working_hours, ...) :-
    StartMin >= MinMinutes,  % Arithmetic comparison
    EndMin =< MaxMinutes.
```

**After:**
```prolog
satisfies_constraint_logic(..., within_working_hours, ...) :-
    StartMin #>= MinMinutes,  % Declarative constraint
    EndMin #=< MaxMinutes.    % Constraint satisfaction proof
```

### 3. Slot Generation

**Before:**
```prolog
generate_candidate_slots(MinStart, MaxEnd, Duration, Step, Slots) :-
    MaxStart is MaxEnd - Duration,
    findall(Start,
        (between(0, 1000, N),        % Procedural iteration
         Start is MinStart + N * Step,  % Arithmetic
         Start =< MaxStart),
        Slots).
```

**After:**
```prolog
generate_candidate_slots(MinStart, MaxEnd, Duration, Step, Slots) :-
    MaxStart #= MaxEnd - Duration,    % Constraint relationship
    findall(Start,
        (Start in MinStart..MaxStart,  % Domain constraint
         (Start - MinStart) mod Step #= 0,  % Alignment constraint
         label([Start])),             % Search for solution
        Slots).
```

### 4. Quality Assessment

**Before:**
```prolog
assess_slot_quality(..., Quality, ...) :-
    ...,
    length(Reasons, NumSatisfied),
    Quality is 100 - NumSatisfied * 10.  % Arithmetic calculation
```

**After:**
```prolog
assess_slot_quality(..., Quality, ...) :-
    PeakHourScore in 0..10,          % Constraint variable
    TypePrefScore in 0..10,
    ...,
    Quality #= 100 - (PeakHourScore + TypePrefScore),  % Constraint relation
    ...
```

## Why CLP(FD)?

### 1. **True Constraint Satisfaction**
- Declares relationships, not calculations
- Solver finds solutions automatically
- Can reason forward and backward

### 2. **Logical Reasoning**
- Constraints are logical statements
- Proofs show constraint satisfaction
- Meta-interpreter builds reasoning chains

### 3. **Knowledge Representation**
```prolog
% Knowledge: What must be true
SlotEnd #= SlotStart + Duration.   % Constraint: duration relationship
SlotStart mod 30 #= 0.             % Constraint: scheduling grid
SlotStart in MinStart..MaxStart.   % Constraint: valid domain

% vs. Procedural: How to compute
SlotEnd is SlotStart + Duration.   % Calculation
```

### 4. **Search as Inference**
```prolog
label([SlotStart, SlotEnd])  % Find values satisfying ALL constraints
% vs.
between(0, 1000, N)          % Iterate through values
```

## Meta-Interpreter Features Preserved

### ✅ Proof Tree Construction
```prolog
prove(Goal, KB, proof(Goal, SubProof))
% Builds tree showing HOW Goal was proven
```

### ✅ Explanation Generation
```prolog
prove_with_trace(Goal, KB, Trace, Result)
% Human-readable reasoning steps
```

### ✅ Logical Inference
```prolog
% Conjunction, disjunction, negation
% Universal/existential quantification
% Backward chaining with knowledge base
```

### ✅ Constraint Satisfaction
```prolog
satisfies_constraint(Event, Constraint, Proof)
% Proves Event satisfies Constraint via logical derivation
```

## Usage Examples

### Example 1: Finding Free Slots

**Declarative Specification:**
```prolog
find_free_slots(Duration, Events, MinH, MinM, MaxH, MaxM, Slots) :-
    % Declare what we're looking for:
    % Slots of given Duration within [MinH:MinM, MaxH:MaxM]
    % That satisfy: ∀e ∈ Events: ¬overlaps(Slot, e)
    
    % The solver finds all solutions satisfying these constraints
```

**Proof Generated:**
```
proof(slot_free(9, 0, 10, 0), [
    step(slot_interval(540, 600), 'candidate slot interval'),
    step(verified_against_all(5), 'checked against all events'),
    step(all_disjoint, 'all event intervals are disjoint from slot'),
    step(conclusion(free_slot), 'slot is free by constraint satisfaction')
])
```

### Example 2: Conflict Detection

**Declarative Specification:**
```prolog
prove_conflict(NewEvent, Events, Conflict, Proof) :-
    % Prove: ∃e ∈ Events : overlaps(NewEvent, e)
    % Using constraint: NewStart #< ExEnd ∧ NewEnd #> ExStart
```

**Proof Generated:**
```
proof(conflict_detected(e1, e2), [
    step(constraint_1(540 #< 660), 'constraint satisfied'),
    step(constraint_2(600 #> 540), 'constraint satisfied'),
    step(conclusion(overlap), 'by constraint satisfaction: intervals overlap'),
    step(therefore(conflict(e1, e2)), 'conflict exists via logical derivation')
])
```

## Implementation Guidelines

### Rule 1: Use CLP(FD) Operators
- Replace `is` with `#=`
- Replace `<, >, =<, >=` with `#<, #>, #=<, #>=`
- Declare domains with `Var in Min..Max`

### Rule 2: Declare Constraints, Don't Calculate
```prolog
% GOOD: Declarative
EndTime #= StartTime + Duration.

% BAD: Procedural
EndTime is StartTime + Duration.
```

### Rule 3: Use `label/1` for Search
```prolog
% After declaring all constraints:
label([Var1, Var2, ...])  % Find values satisfying constraints
```

### Rule 4: Build Proof Trees
```prolog
prove(Goal, KB, proof(Goal, constraint_satisfaction(Constraints)))
% Show WHICH constraints were satisfied
```

## Verification

### Test CLP(FD) Constraints
```prolog
?- SlotStart in 360..1080, SlotEnd in 360..1080,
   SlotEnd #= SlotStart + 60,
   SlotStart mod 30 #= 0,
   label([SlotStart]).
   
% Finds: SlotStart = 360, 390, 420, 450, ...
% All satisfying the constraints!
```

### Verify Meta-Interpreter
```prolog
?- prove(satisfies(event(...), no_overlap), KB, Proof).
% Returns: proof(satisfies(...), [reasoning_steps])
```

## Benefits of This Approach

1. **True Meta-Interpretation**: Reasoning about scheduling, not computing
2. **Declarative Constraints**: State what must be true, not how to compute
3. **Logical Proofs**: Show WHY decisions are made
4. **Knowledge Representation**: Facts and rules, not algorithms
5. **Constraint Satisfaction**: Solver finds solutions automatically
6. **Explainability**: Proof trees show reasoning chains

## Conclusion

The refactored code is now a **pure meta-interpreter** that:
- ✅ Uses declarative CLP(FD) constraints instead of procedural arithmetic
- ✅ Performs logical inference with proof construction
- ✅ Implements constraint satisfaction through logical derivation
- ✅ Provides explainable reasoning via proof traces
- ✅ Separates knowledge (constraints) from search (labeling)

This is **Knowledge Representation and Reasoning**, not algorithmic programming!
