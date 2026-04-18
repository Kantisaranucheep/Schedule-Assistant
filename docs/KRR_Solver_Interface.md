# KRR Compliance: Schedule Solver Interface and Reasoning

## Overview
This document explains how the refactored Prolog constraint solver fits the knowledge representation and reasoning (KRR) concept for event scheduling in the Schedule Assistant project.

## Core Concept
- **When adding a new event,** the system passes the new event and relevant constraints as parameters to the solver.
- **The solver** reasons about the schedule, using explicit knowledge rules for penalties, priorities, and constraints, to find an optimal or feasible arrangement.

## How the Implementation Fits

### 1. Solver Interface
The main solver predicates (e.g., `reschedule_event/8`, `find_optimal_schedule/6`) are designed to:
- **Accept the new event as a parameter.**
- **Accept constraints** such as existing events, time bounds, and strategy as parameters.

**Example:**
```
reschedule_event(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
    ExistingEvents,
    Strategy,
    MinH, MinM, MaxH, MaxM,
    Result
).
```
- `event(...)` is the new event to add.
- `ExistingEvents` is the list of current events (constraints).
- `Strategy`, `MinH`, `MinM`, `MaxH`, `MaxM` are additional constraints.

### 2. Knowledge-Driven Reasoning
- **Penalties and weights** (e.g., move penalty, shift penalty, priority weight) are now represented as explicit facts/rules:
  - `move_penalty/1`, `shift_penalty/1`, `priority_penalty_weight/1`, `priority_loss/3`.
- **Cost and heuristic calculations** use these rules, not hardcoded numbers, making the knowledge explicit and modifiable.
- **All reasoning** (cost, heuristic, slot finding, conflict detection) is performed based on the parameters provided to the solver.

### 3. Example Flow
1. **User requests to add a new event.**
2. **Backend constructs the Prolog query:**
   - Passes the new event and constraints to the solver predicate.
3. **Solver applies logic:**
   - Uses explicit rules for penalties, priorities, and constraints.
   - Computes costs, checks conflicts, and proposes a schedule.
4. **Result returned** to the backend for user feedback or further action.

### 4. KRR Principles Satisfied
- **Separation of knowledge and computation:** Penalties and priorities are facts/rules, not just numbers in code.
- **Declarative reasoning:** Logic rules drive the scheduling, not procedural code.
- **Parameter-driven inference:** All reasoning is based on the new event and constraints passed as parameters.

## Summary
The refactored implementation ensures that the solver receives the new event and constraints as parameters, and all reasoning is performed using explicit, logic-based knowledge rules. This fully aligns with KRR principles and your project’s conceptual requirements.
