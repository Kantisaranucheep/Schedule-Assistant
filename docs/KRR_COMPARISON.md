# KRR Transformation: Procedural to Reasoning Engine

This document explains the refactoring of the Schedule Assistant's Prolog subsystem, focusing on the shift from procedural algorithms to a declarative Knowledge Representation and Reasoning (KRR) engine.

## 1. Executive Summary

The scheduling system has been transformed from a "scripting tool" into an autonomous "reasoning agent." Instead of simulating step-by-step procedures, the system now uses logical inference over facts, rules, and constraints.

### Comparison Table

| Feature | Before (Procedural) | After (KRR Reasoning) |
|---------|---------------------|----------------------|
| **Approach** | Step-by-step algorithms | Declarative logical inference |
| **Knowledge** | Hardcoded in predicate bodies | Declared as symbolic facts |
| **Slot Finding** | Algorithmic gap-finding (procedural list walking) | Constraint satisfaction over the time domain |
| **Costs/Weights** | Calculated in Python | Inferred from Prolog knowledge base |
| **Logic Location** | Mixed between Python and Prolog | Centered in Prolog (Python as interface) |
| **Meta-Level** | Minimal | Full support for `demo/1` and `explain/2` proof traces |

---

## 2. Code Comparisons

### 2.1 Slot Finding (Inference vs. Algorithm)

**Before (Procedural Gap-Finding):**
The scheduler walked through a sorted list of events and manually calculated the "gaps" between them.

```prolog
find_gap_in_schedule([event(_, _, _, _, End1, _, _), event(_, _, _, Start2, _, _, _)|_], _, _, GapStart, GapEnd) :-
    extract_time(End1, GapStartHM),
    extract_time(Start2, GapEndHM),
    GapStartHM @< GapEndHM,
    GapStart = GapStartHM, GapEnd = GapEndHM.
```

**After (Declarative Constraint Satisfaction):**
The scheduler now defines what a "valid slot" is (within hours, no overlap) and lets Prolog infer the answer by searching the time domain.

```prolog
find_available_slot(CalendarId, DurationMinutes, StartHM, EndHM) :-
    time_coordinate(H, M),
    StartHM @>= WorkStart,
    duration_offset(StartHM, DurationMinutes, EndHM),
    all_constraints_hold(CalendarId, StartHM, EndHM).
```

### 2.2 Cost Calculation (Knowledge vs. Parameter)

**Before (Python Calculation):**
Python hard-coded the rules for buffer proximity and overload penalties.

```python
# In Python
def _calc_soft_cost(self, start_min: int, end_min: int, busy_intervals: List[tuple]) -> float:
    for bs, be in busy_intervals:
        if 0 < start_min - be < 15:
            cost += 3.0
```

**After (Prolog Inference):**
Python now queries Prolog to "infer" the cost based on declared soft constraints and weights.

```python
# In Python
soft_cost = self._get_prolog_soft_cost(event_id, title, slot_start, slot_end, ...)

# In Prolog
total_soft_cost(Event, Context, Prefs, Total) :-
    findall(WC, (
        soft_constraint(Name, Weight),
        soft_cost_for(Name, Event, Context, Raw),
        WC is Raw * Weight / 5
    ), Costs),
    sum_list(Costs, Total).
```

---

## 3. Meta-Reasoning and Explainability

We have introduced the `explain/2` predicate which allows the system to not just provide an answer, but a "proof trace" of why that answer holds.

**Query:** `?- explain(valid_schedule('cal-001', '10:00', '11:00'), Trace).`
**Result:** `Trace = [step(valid_schedule, 'cal-001', '10:00-11:00', 'All scheduling constraints satisfied')]`

This enables the Chat UI to eventually tell the user: *"I suggested moving this meeting because it violates the 'sufficient_buffer' constraint but has a lower priority than your class."*

## 4. Architectural Integrity

- **Python** remains the high-level orchestrator (Interface Layer) and handles the A* search loop.
- **Prolog** remains the reasoning core (Logic Layer) where all "intelligence" regarding the domain is stored.
- **Integration** is maintained via `pyswip` using symbolic terms that reflect the KRR state.
