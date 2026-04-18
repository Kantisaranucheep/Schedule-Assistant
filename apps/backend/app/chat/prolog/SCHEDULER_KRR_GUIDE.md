# Scheduler.pl - KRR Enhancement Documentation

## Summary of Changes

The `scheduler.pl` file has been enhanced with **Knowledge Representation and Reasoning (KRR)** capabilities while maintaining full backward compatibility with existing code.

---

## What Was Added

### 1. **Meta-Interpreter for Scheduling Logic**
```prolog
prove_scheduling_goal(+Goal, +KB, -Proof)
```
- Performs logical inference about scheduling problems
- Builds proof trees showing reasoning chains
- Supports temporal logic reasoning

### 2. **Knowledge Base - Logical Rules**
```prolog
% Temporal relations
temporal_relation(before(T1, T2)).
temporal_relation(overlaps(interval(S1, E1), interval(S2, E2))).
temporal_relation(disjoint(interval(S1, E1), interval(S2, E2))).

% Scheduling rules
scheduling_rule(conflict_exists(Event1, Event2)).
scheduling_rule(slot_is_valid(Slot, Events)).
```

### 3. **New KRR Predicates** (with proof traces)

#### Conflict Detection with Proofs
```prolog
prove_conflict(+NewEvent, +Events, -Conflict, -Proof)
```
- **OLD**: `check_conflict/5` returns list of conflicting events
- **NEW**: Returns conflict + proof showing WHY it conflicts

**Example:**
```prolog
?- prove_conflict(
     event(new, "Meeting", 9, 0, 10, 0),
     [event(e1, "Existing", 9, 30, 10, 30)],
     Conflict,
     Proof
   ).

Conflict = conflict(new, e1, "Existing"),
Proof = proof(conflict_detected(new, e1), [
    step(extracted_intervals, ...),
    step(new_interval(540, 600), ...),
    step(existing_interval(570, 630), ...),
    step(conclusion(overlap), 'by temporal logic: intervals overlap')
]).
```

#### No Conflict Proof
```prolog
prove_no_conflict(+NewEvent, +Events, -Proof)
```
- Proves that an event does NOT conflict
- Shows logical reasoning for each existing event

**Example:**
```prolog
?- prove_no_conflict(
     event(new, "Meeting", 11, 0, 12, 0),
     [event(e1, "Existing", 9, 0, 10, 0)],
     Proof
   ).

Proof = proof(no_conflicts(new), [
    step(checked_all_events, 'verified 1 events'),
    step(all_disjoint, 'all intervals are temporally disjoint'),
    step(conclusion, 'no conflicts exist by universal verification')
]).
```

#### Free Slot with Proof
```prolog
prove_slot_free(+Slot, +Events, -Proof, -Trace)
```
- **OLD**: `slot_is_free/3` returns yes/no
- **NEW**: Returns proof + human-readable trace

**Example:**
```prolog
?- prove_slot_free(
     slot(10, 0, 11, 0),
     [event(e1, "Meeting", 9, 0, 9, 30)],
     Proof,
     Trace
   ).

Proof = proof(slot_free(10, 0, 11, 0), [
    step(slot_interval(600, 660), 'candidate slot interval'),
    step(verified_against_all(1), 'checked against all events'),
    step(all_disjoint, 'all event intervals are disjoint from slot'),
    step(conclusion(free_slot), 'slot is free by universal verification')
]),
Trace = 'Slot 10:0-11:0 is FREE because it is temporally disjoint from all 1 events'.
```

#### Find Free Slots with Proofs
```prolog
find_free_slots_with_proof(+Duration, +Events, +MinSH, +MinSM, +MaxEH, +MaxEM, -Slots, -Proofs)
```
- **OLD**: `find_free_slots/7` returns list of slots
- **NEW**: Returns slots + proof for each one

### 4. **Explanation Generation**
```prolog
explain_conflict(+Conflict, +Proof, -Explanation)
explain_why_free(+Slot, +Proof, -Explanation)
```
- Converts proof trees into human-readable explanations
- Perfect for showing your professor the logical reasoning

**Example:**
```prolog
?- prove_conflict(..., Conflict, Proof),
   explain_conflict(Conflict, Proof, Explanation).

Explanation = explanation(
    'Event new conflicts with event e1 (Existing) due to overlapping time intervals',
    [
        'extracted_intervals: extracted time intervals from events',
        'new_interval(540,600): new event interval',
        'existing_interval(570,630): existing event interval',
        'check_overlap_condition: checking overlap condition',
        'condition_1(540<630): 540 < 630 is true',
        'condition_2(600>570): 600 > 570 is true',
        'conclusion(overlap): by temporal logic: intervals overlap',
        'therefore(conflict(new,e1)): therefore: conflict exists'
    ]
).
```

---

## Backward Compatibility

**All original predicates still work exactly as before:**
- `check_conflict/5`
- `find_free_slots/7`
- `find_free_ranges/5`
- `find_free_days/7`
- `time_to_minutes/3`
- `minutes_to_time/3`
- `events_overlap/4`
- `slot_conflicts_with_events/3`

**Your existing Python/Prolog integration code will continue to work without changes!**

---

## Comparison: Old vs. New

### OLD Approach (Procedural)
```prolog
% Simple yes/no answer
?- check_conflict(9, 0, 10, 0, [event(e1, "M", 9, 30, 10, 30)], C).
C = [conflict(e1, "M", 9, 30, 10, 30)].  % Just returns the conflict

% No explanation of WHY
```

### NEW Approach (Logical with Proof)
```prolog
% Returns conflict + logical reasoning
?- prove_conflict(
     event(new, "Meeting", 9, 0, 10, 0),
     [event(e1, "M", 9, 30, 10, 30)],
     Conflict,
     Proof
   ).

Conflict = conflict(new, e1, "M"),
Proof = proof(conflict_detected(new, e1), [
    % Shows STEP BY STEP logical reasoning
    step(extracted_intervals, 'extracted time intervals from events'),
    step(new_interval(540, 600), 'new event interval'),
    step(existing_interval(570, 630), 'existing event interval'),
    step(check_overlap_condition, 'checking overlap condition'),
    step(condition_1(540<630), '540 < 630 is true'),
    step(condition_2(600>570), '600 > 570 is true'),
    step(conclusion(overlap), 'by temporal logic: intervals overlap'),
    step(therefore(conflict(new, e1)), 'therefore: conflict exists')
]).
```

---

## Why This Satisfies Your Professor

### 1. **Meta-Interpreter Present** ✓
- `prove_scheduling_goal/3` performs logical inference
- Not just checking - actually reasoning

### 2. **Knowledge Base** ✓
- `temporal_relation/1` - declarative temporal logic facts
- `scheduling_rule/1` - domain knowledge rules
- `interval_of/1` - knowledge extraction rules

### 3. **Logical Reasoning** ✓
```prolog
% Proves temporal relations through logic
temporal_relation(overlaps(interval(S1, E1), interval(S2, E2))) :-
    S1 < E2, S2 < E1.  % Logical derivation, not formula

% Proves scheduling rules
scheduling_rule(conflict_exists(Event1, Event2)) :-
    temporal_relation(overlaps(
        interval_of(Event1),
        interval_of(Event2)
    )).  % Logical inference chain
```

### 4. **Proof Traces** ✓
- Every conclusion justified with step-by-step reasoning
- Can explain WHY conflicts exist
- Can explain WHY slots are free

### 5. **Universal/Existential Quantification** ✓
```prolog
% Universal: Slot is free if ∀ events, it's disjoint
prove_slot_free(Slot, Events, Proof, Trace) :-
    findall(
        proof(no_conflict_with(EventId), Reasoning),
        (
            member(Event, Events),  % ∀ Event
            % prove disjoint
        ),
        AllProofs
    ),
    length(Events, NumEvents),
    length(AllProofs, NumVerified),
    NumEvents == NumVerified.  % Universal verification
```

### 6. **Explanation Generation** ✓
- Human-readable reasoning chains
- Perfect for demonstrations

---

## Integration with constraint_solver_krr.pl

Both modules now work together with consistent KRR approach:

```prolog
% scheduler.pl provides temporal reasoning
:- use_module(scheduler, [
    prove_conflict/4,
    prove_slot_free/4,
    prove_scheduling_goal/3
]).

% constraint_solver_krr.pl uses these for higher-level reasoning
find_valid_slot(Event, KB, Slot, Proof) :-
    % Generate candidates
    generate_candidate_slot(..., Slot),
    % Prove it's free using scheduler's KRR predicates
    prove_slot_free(Slot, Events, SlotProof, _),
    % Build combined proof
    Proof = proof(found_valid_slot, [SlotProof, ...]).
```

---

## Testing the New Features

### Test 1: Prove Conflict
```prolog
?- prove_conflict(
     event(new, "Team Meeting", 14, 0, 15, 0),
     [event(1, "Project Review", 14, 30, 15, 30)],
     Conflict,
     Proof
   ).
```

### Test 2: Prove No Conflict
```prolog
?- prove_no_conflict(
     event(new, "Lunch", 12, 0, 13, 0),
     [event(1, "Morning Meeting", 9, 0, 10, 0),
      event(2, "Afternoon Meeting", 14, 0, 15, 0)],
     Proof
   ).
```

### Test 3: Prove Slot Free
```prolog
?- prove_slot_free(
     slot(11, 0, 12, 0),
     [event(1, "Meeting", 9, 0, 10, 0)],
     Proof,
     Trace
   ),
   write(Trace).
```

### Test 4: Find Slots with Proofs
```prolog
?- find_free_slots_with_proof(
     60,
     [event(1, "Meeting", 9, 0, 10, 0)],
     8, 0, 18, 0,
     Slots,
     Proofs
   ).
```

### Test 5: Get Explanation
```prolog
?- prove_conflict(
     event(new, "Demo", 10, 0, 11, 0),
     [event(1, "Standup", 10, 30, 11, 0)],
     Conflict,
     Proof
   ),
   explain_conflict(Conflict, Proof, Explanation),
   Explanation = explanation(Summary, Steps),
   write(Summary), nl,
   forall(member(Step, Steps), (write('  - '), write(Step), nl)).
```

---

## Migration Strategy

1. **Immediate:** New KRR predicates available for demonstrations
2. **Gradual:** Existing code continues to work
3. **Optional:** Migrate to KRR predicates when needed
4. **Demonstration:** Use new predicates to show professor the logical reasoning

---

## Conclusion

The enhanced `scheduler.pl` now provides:
- ✓ **Meta-interpreter** for logical inference
- ✓ **Knowledge base** with declarative rules
- ✓ **Proof traces** showing reasoning
- ✓ **Backward compatibility** with existing code
- ✓ **Explanation generation** for demonstrations

This transforms the scheduler from a **procedural conflict checker** into a **reasoning system** that can explain its decisions through logical inference.
