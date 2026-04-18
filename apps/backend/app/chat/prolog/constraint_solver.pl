%% ============================================================================
%% META-INTERPRETER FOR KRR DEMONSTRATION
%% ============================================================================

%% rule(Head, Body): Knowledge rules for reasoning
rule(conflict(Event1, Event2), (overlaps(Event1, Event2))).
rule(overlaps(event(_,_,SH1,SM1,EH1,EM1,_), event(_,_,SH2,SM2,EH2,EM2,_)),
    (time_to_minutes(SH1,SM1,S1), time_to_minutes(EH1,EM1,E1),
     time_to_minutes(SH2,SM2,S2), time_to_minutes(EH2,EM2,E2),
     S1 < E2, S2 < E1)).
rule(priority_loss(Priority, Weight, Loss), (Loss is Priority * Priority * Weight)).

%% Meta-interpreter: solve/1
solve(true) :- !.
solve((A,B)) :- !, solve(A), solve(B).
solve(Goal) :-
    rule(Goal, Body),
    solve(Body).
solve(Goal) :-
    % Fallback to built-in predicates (arithmetic, etc.)
    call(Goal).

%% Example usage:
%% ?- solve(conflict(E1, E2)).
%% ?- solve(priority_loss(5, 2.0, Loss)).
%% apps/backend/app/chat/prolog/constraint_solver.pl
%% ============================================================================
%% Meta-Interpreter Based Constraint Solver
%% Knowledge Representation and Reasoning Approach
%% ============================================================================
%%
%% This implements a meta-interpreter that performs logical reasoning about
%% scheduling constraints, producing proof traces that explain WHY decisions
%% are made through logical inference rather than mathematical computation.
%%
%% Key KR&R Concepts:
%%   - Meta-interpreter: prove/3 that builds proof trees
%%   - Knowledge base: Declarative constraint rules
%%   - Logical inference: Forward and backward chaining
%%   - Explanation generation: Proof traces showing reasoning
%%   - Constraint satisfaction: Logical derivation, not arithmetic
%% ============================================================================

:- module(constraint_solver, [
    % Meta-interpreter interface
    prove/3,                    % prove(Goal, Knowledge, Proof)
    prove_with_trace/4,         % prove_with_trace(Goal, KB, Trace, Result)
    
    % Logical constraint checking
    satisfies_constraint/3,     % satisfies_constraint(Event, Constraint, Proof)
    violates_constraint/3,      % violates_constraint(Event, Constraint, Proof)
    
    % Schedule validation through logical inference
    valid_schedule/3,           % valid_schedule(Schedule, KB, Proof)
    find_violations/3,          % find_violations(Schedule, KB, Violations)
    
    % Constraint-based reasoning
    resolve_conflict/4,         % resolve_conflict(Conflict, KB, Action, Proof)
    find_valid_slot/4,          % find_valid_slot(Event, KB, Slot, Proof)
    
    % Query interface
    query_schedule/4,           % query_schedule(Query, Schedule, KB, Answer)
    explain_decision/3          % explain_decision(Decision, Proof, Explanation)
]).

:- use_module(scheduler, [
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3
]).

%% ============================================================================
%% KNOWLEDGE BASE: Declarative Constraint Rules
%% ============================================================================
%% These are logical facts and rules that define what makes a valid schedule.
%% They are NOT procedures or calculations - they are knowledge.

% Constraint type hierarchy (logical taxonomy)
constraint_type(no_overlap, hard).
constraint_type(within_working_hours, hard).
constraint_type(positive_duration, hard).
constraint_type(respects_priority, soft).
constraint_type(respects_preferences, soft).
constraint_type(adequate_buffer, soft).
constraint_type(balanced_load, soft).

% Working hours definition (knowledge fact)
working_hours(6, 0, 23, 0).

% Buffer time requirements (knowledge rule)
requires_buffer(meeting, 15).
requires_buffer(study, 10).
requires_buffer(exercise, 5).
requires_buffer(_, 5).  % default

% Priority-based scheduling preferences (logical rules)
priority_time_preference(Priority, StartHour, EndHour) :-
    Priority >= 8,
    StartHour >= 9,
    EndHour =< 17.  % High priority → peak hours

priority_time_preference(Priority, _, _) :-
    Priority < 8.  % Low priority → flexible

% Event type preferences (knowledge about event types)
event_type_preference(meeting, 9, 0, 17, 0).
event_type_preference(study, 8, 0, 18, 0).
event_type_preference(exercise, 6, 0, 8, 0).
event_type_preference(exercise, 17, 0, 21, 0).

%% ============================================================================
%% META-INTERPRETER: Core Reasoning Engine
%% ============================================================================
%% This is the heart of the KR&R approach - it performs logical inference
%% and builds proof trees showing HOW conclusions are reached.

%% prove(+Goal, +KnowledgeBase, -Proof)
%% Meta-interpreter that proves goals through logical inference.
%% Produces a proof tree showing the reasoning chain.

% Base case: proven fact
prove(true, _KB, proof(true, axiom)) :- !.

% Conjunction: prove both goals
prove((Goal1, Goal2), KB, proof(and(Goal1, Goal2), [Proof1, Proof2])) :-
    !,
    prove(Goal1, KB, Proof1),
    prove(Goal2, KB, Proof2).

% Disjunction: prove either goal
prove((Goal1 ; Goal2), KB, proof(or(Goal1, Goal2), Proof)) :-
    !,
    (   prove(Goal1, KB, Proof1),
        Proof = left(Proof1)
    ;   prove(Goal2, KB, Proof2),
        Proof = right(Proof2)
    ).

% Negation by failure (closed world assumption)
prove(not(Goal), KB, proof(not(Goal), failed(SubProof))) :-
    !,
    (   prove(Goal, KB, SubProof)
    ->  fail
    ;   SubProof = none
    ).

% Query the knowledge base
prove(constraint_type(Type, Category), _KB, proof(constraint_type(Type, Category), fact)) :-
    constraint_type(Type, Category), !.

prove(working_hours(SH, SM, EH, EM), _KB, proof(working_hours(SH, SM, EH, EM), fact)) :-
    working_hours(SH, SM, EH, EM), !.

% Logical inference for constraint satisfaction
prove(satisfies(Event, Constraint), KB, proof(satisfies(Event, Constraint), SubProof)) :-
    satisfies_constraint_logic(Event, Constraint, KB, SubProof), !.

prove(violates(Event, Constraint), KB, proof(violates(Event, Constraint), SubProof)) :-
    violates_constraint_logic(Event, Constraint, KB, SubProof), !.

% Derived rules (logical implication)
prove(valid_event(Event), KB, proof(valid_event(Event), SubProof)) :-
    prove(forall_constraints(Event, satisfies), KB, SubProof), !.

% Forall quantification
prove(forall_constraints(Event, Relation), KB, 
      proof(forall_constraints(Event, Relation), Proofs)) :-
    findall(
        proof(Relation(Event, C), P),
        (
            constraint_type(C, _),
            (   Relation = satisfies
            ->  prove(satisfies(Event, C), KB, P)
            ;   prove(violates(Event, C), KB, P)
            )
        ),
        Proofs
    ), !.

% Default: try to prove as a Prolog goal (with proof recording)
prove(Goal, _KB, proof(Goal, prolog_derivation)) :-
    call(Goal).

%% prove_with_trace(+Goal, +KB, -Trace, -Result)
%% Extended meta-interpreter that generates human-readable trace
prove_with_trace(Goal, KB, Trace, Result) :-
    prove(Goal, KB, Proof),
    !,
    Result = success,
    proof_to_trace(Proof, Trace).
prove_with_trace(Goal, _KB, trace([failed(Goal)]), failure).

proof_to_trace(proof(Goal, axiom), [step(Goal, 'axiom (known fact)')]) :- !.
proof_to_trace(proof(Goal, fact), [step(Goal, 'fact from knowledge base')]) :- !.
proof_to_trace(proof(Goal, prolog_derivation), [step(Goal, 'derived by Prolog inference')]) :- !.
proof_to_trace(proof(and(G1, G2), [P1, P2]), Trace) :-
    !,
    proof_to_trace(P1, T1),
    proof_to_trace(P2, T2),
    append([[step(and(G1, G2), 'proving conjunction')], T1, T2], Trace).
proof_to_trace(proof(or(G1, G2), left(P)), Trace) :-
    !,
    proof_to_trace(P, T),
    append([[step(or(G1, G2), 'proving left disjunct')], T], Trace).
proof_to_trace(proof(or(G1, G2), right(P)), Trace) :-
    !,
    proof_to_trace(P, T),
    append([[step(or(G1, G2), 'proving right disjunct')], T], Trace).
proof_to_trace(proof(Goal, SubProof), Trace) :-
    is_list(SubProof),
    !,
    maplist(proof_to_trace, SubProof, SubTraces),
    append([[step(Goal, 'derived from')], SubTraces], Trace).
proof_to_trace(proof(Goal, _), [step(Goal, 'proven')]).

%% ============================================================================
%% LOGICAL CONSTRAINT SATISFACTION
%% ============================================================================
%% Each constraint is represented as a logical predicate with inference rules.

%% satisfies_constraint(+Event, +Constraint, -Proof)
%% Proves that an event satisfies a constraint through logical inference
satisfies_constraint(Event, Constraint, Proof) :-
    prove(satisfies(Event, Constraint), [], Proof).

%% violates_constraint(+Event, +Constraint, -Proof)
%% Proves that an event violates a constraint
violates_constraint(Event, Constraint, Proof) :-
    prove(violates(Event, Constraint), [], Proof).

%% satisfies_constraint_logic(+Event, +Constraint, +KB, -Proof)
%% Logical rules defining when constraints are satisfied

% NO OVERLAP constraint (logical definition)
satisfies_constraint_logic(
    event(Id, _, S1H, S1M, E1H, E1M, _, _),
    no_overlap,
    KB,
    proof(no_overlap_with_all, AllProofs)
) :-
    member(kb(schedule(Events)), KB),
    findall(
        proof(no_overlap_with(Id2), SubProof),
        (
            member(event(Id2, _, S2H, S2M, E2H, E2M, _, _), Events),
            Id \= Id2,
            prove(events_do_not_overlap(
                time(S1H, S1M, E1H, E1M),
                time(S2H, S2M, E2H, E2M)
            ), KB, SubProof)
        ),
        AllProofs
    ).

% WITHIN WORKING HOURS constraint (logical definition)
satisfies_constraint_logic(
    event(_, _, StartH, StartM, EndH, EndM, _, _),
    within_working_hours,
    _KB,
    proof(within_hours, [StartProof, EndProof])
) :-
    working_hours(MinH, MinM, MaxH, MaxM),
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    time_to_minutes(MinH, MinM, MinMinutes),
    time_to_minutes(MaxH, MaxM, MaxMinutes),
    StartMin >= MinMinutes,
    EndMin =< MaxMinutes,
    StartProof = proof(start_after(MinH, MinM), logical_comparison),
    EndProof = proof(end_before(MaxH, MaxM), logical_comparison).

% POSITIVE DURATION constraint (logical definition)
satisfies_constraint_logic(
    event(_, _, StartH, StartM, EndH, EndM, _, _),
    positive_duration,
    _KB,
    proof(positive_duration, derived)
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    EndMin > StartMin.

% RESPECTS PRIORITY constraint (logical inference)
satisfies_constraint_logic(
    event(_, _, StartH, _, _, _, Priority, _),
    respects_priority,
    _KB,
    proof(priority_satisfied, PreferenceProof)
) :-
    prove(priority_time_preference(Priority, PreferredStart, PreferredEnd), [], PreferenceProof),
    StartH >= PreferredStart,
    StartH =< PreferredEnd.

% Default: constraint satisfied if not violated
satisfies_constraint_logic(Event, Constraint, KB, proof(not_violated, NegProof)) :-
    \+ violates_constraint_logic(Event, Constraint, KB, _),
    NegProof = proof(no_violation_found, closed_world_assumption).

%% violates_constraint_logic(+Event, +Constraint, +KB, -Proof)
%% Logical rules defining constraint violations

% NO OVERLAP violation (logical definition)
violates_constraint_logic(
    event(Id, _, S1H, S1M, E1H, E1M, _, _),
    no_overlap,
    KB,
    proof(overlaps_with(Id2, Title2), overlap_derivation)
) :-
    member(kb(schedule(Events)), KB),
    member(event(Id2, Title2, S2H, S2M, E2H, E2M, _, _), Events),
    Id \= Id2,
    time_to_minutes(S1H, S1M, S1),
    time_to_minutes(E1H, E1M, E1),
    time_to_minutes(S2H, S2M, S2),
    time_to_minutes(E2H, E2M, E2),
    % Logical overlap condition
    S1 < E2,
    S2 < E1.

% WORKING HOURS violation
violates_constraint_logic(
    event(_, _, StartH, StartM, EndH, EndM, _, _),
    within_working_hours,
    _KB,
    proof(Violation, logical_check)
) :-
    working_hours(MinH, MinM, MaxH, MaxM),
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    time_to_minutes(MinH, MinM, MinMinutes),
    time_to_minutes(MaxH, MaxM, MaxMinutes),
    (   StartMin < MinMinutes, Violation = starts_too_early(StartH, StartM)
    ;   EndMin > MaxMinutes, Violation = ends_too_late(EndH, EndM)
    ).

% POSITIVE DURATION violation
violates_constraint_logic(
    event(_, _, StartH, StartM, EndH, EndM, _, _),
    positive_duration,
    _KB,
    proof(invalid_duration, logical_comparison)
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    EndMin =< StartMin.

%% ============================================================================
%% SCHEDULE VALIDATION THROUGH LOGICAL INFERENCE
%% ============================================================================

%% valid_schedule(+Schedule, +KB, -Proof)
%% Proves a schedule is valid by showing all events satisfy all hard constraints
valid_schedule(schedule(Events), KB, proof(valid_schedule, EventProofs)) :-
    findall(
        proof(valid_event(Id), SubProof),
        (
            member(Event, Events),
            Event = event(Id, _, _, _, _, _, _, _),
            prove(valid_event(Event), [kb(schedule(Events))|KB], SubProof)
        ),
        EventProofs
    ),
    EventProofs \= [].

%% find_violations(+Schedule, +KB, -Violations)
%% Finds all constraint violations with logical proofs
find_violations(schedule(Events), KB, Violations) :-
    findall(
        violation(EventId, Constraint, Proof),
        (
            member(Event, Events),
            Event = event(EventId, _, _, _, _, _, _, _),
            constraint_type(Constraint, hard),
            violates_constraint_logic(Event, Constraint, [kb(schedule(Events))|KB], Proof)
        ),
        Violations
    ).

%% ============================================================================
%% HARD CONSTRAINTS — Must be satisfied, no exceptions
%% ============================================================================


%% --- KRR: Hard constraint rules ---
% No time overlap with other events
rule(hard_violation(Event, AllEvents, overlap(OtherId, OtherTitle)),
    ( member(event(OtherId, OtherTitle, OSH, OSM, OEH, OEM, _, _), AllEvents),
      event_id(Event, Id),
      OtherId \= Id,
      event_time(Event, StartMin, EndMin),
      time_to_minutes(OSH, OSM, OStart),
      time_to_minutes(OEH, OEM, OEnd),
      OStart < EndMin, StartMin < OEnd )).

% Before working hours
rule(hard_violation(Event, _, before_working_hours),
    ( event_time(Event, StartMin, _), StartMin < 360 )).

% After working hours
rule(hard_violation(Event, _, after_working_hours),
    ( event_time(Event, _, EndMin), EndMin > 1380 )).

% Invalid duration
rule(hard_violation(Event, _, invalid_duration),
    ( event_time(Event, StartMin, EndMin), EndMin =< StartMin )).

% Helper to extract event id
event_id(event(Id, _, _, _, _, _, _, _), Id).
% Helper to extract event start/end in minutes
event_time(event(_, _, SH, SM, EH, EM, _, _), StartMin, EndMin) :-
    time_to_minutes(SH, SM, StartMin),
    time_to_minutes(EH, EM, EndMin).

%% KRR-driven validate_hard_constraints/3 using meta-interpreter
validate_hard_constraints(Event, AllEvents, Violations) :-
    findall(Violation, solve(hard_violation(Event, AllEvents, Violation)), Violations).

%% ============================================================================
%% SOFT CONSTRAINTS — Preferences with penalty costs
%% ============================================================================

%% calculate_soft_cost(+Event, +AllEvents, +Preferences, -TotalCost)
%% Calculates total soft constraint violation cost.
%%
%% Soft constraint types with costs:
%%   - Preferred time violation: penalty based on distance from preferred slot
%%   - Priority displacement: cost of moving a high-priority event
%%   - Proximity penalty: events too close together (no buffer)
%%   - Daily overload: too many events on one day
calculate_soft_cost(
    event(_Id, _Title, StartH, StartM, EndH, EndM, Priority, Type),
    AllEvents,
    Preferences,
    TotalCost
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),

    % Cost 1: Preferred time penalty
    preferred_time_cost(Type, StartMin, EndMin, Preferences, TimeCost),

    % Cost 2: Buffer proximity penalty
    buffer_proximity_cost(StartMin, EndMin, AllEvents, BufferCost),

    % Cost 3: Daily overload penalty
    daily_overload_cost(AllEvents, OverloadCost),

    % Cost 4: Priority-appropriate scheduling
    priority_scheduling_cost(Priority, StartMin, PriorityCost),

    TotalCost is TimeCost + BufferCost + OverloadCost + PriorityCost.

%% preferred_time_cost(+Type, +StartMin, +EndMin, +Preferences, -Cost)
%% Penalty for scheduling events outside their preferred time windows
preferred_time_cost(meeting, StartMin, _EndMin, _Prefs, Cost) :-
    % Meetings preferred 9:00-17:00
    (   StartMin >= 540, StartMin =< 1020
    ->  Cost = 0
    ;   Diff is abs(StartMin - 540),
        Cost is min(Diff // 30, 10)
    ).
preferred_time_cost(study, StartMin, _EndMin, _Prefs, Cost) :-
    % Study preferred 8:00-12:00 or 14:00-18:00
    (   (StartMin >= 480, StartMin =< 720)
    ;   (StartMin >= 840, StartMin =< 1080)
    ->  Cost = 0
    ;   Cost = 5
    ).
preferred_time_cost(exercise, StartMin, _EndMin, _Prefs, Cost) :-
    % Exercise preferred early morning or evening
    (   StartMin =< 480   % Before 8am
    ;   StartMin >= 1020  % After 5pm
    ->  Cost = 0
    ;   Cost = 3
    ).
preferred_time_cost(_, _, _, _, 0).  % Default: no preference penalty

%% buffer_proximity_cost(+StartMin, +EndMin, +AllEvents, -Cost)
%% Penalty if events are too close together (< 15 min buffer)
buffer_proximity_cost(StartMin, EndMin, AllEvents, Cost) :-
    findall(1, (
        member(event(_, _, OSH, OSM, OEH, OEM, _, _), AllEvents),
        time_to_minutes(OSH, OSM, OStart),
        time_to_minutes(OEH, OEM, OEnd),
        (   (OEnd > StartMin - 15, OEnd =< StartMin) % Event ends < 15min before
        ;   (OStart >= EndMin, OStart < EndMin + 15)  % Event starts < 15min after
        )
    ), CloseEvents),
    length(CloseEvents, NumClose),
    Cost is NumClose * 3.

%% daily_overload_cost(+AllEvents, -Cost)
%% Penalty for having too many events in one day (more than 6)
daily_overload_cost(AllEvents, Cost) :-
    length(AllEvents, NumEvents),
    (   NumEvents > 8
    ->  Cost is (NumEvents - 8) * 5
    ;   NumEvents > 6
    ->  Cost is (NumEvents - 6) * 2
    ;   Cost = 0
    ).

%% priority_scheduling_cost(+Priority, +StartMin, -Cost)
%% High-priority events scheduled at suboptimal times get penalized
priority_scheduling_cost(Priority, StartMin, Cost) :-
    Priority >= 8,
    % Critical events should be in peak hours (9am-5pm)
    (   StartMin >= 540, StartMin =< 1020
    ->  Cost = 0
    ;   Cost is (Priority - 7) * 3
    ),
    !.
priority_scheduling_cost(_, _, 0).

%% ============================================================================
%% g(n) — DISPLACEMENT COST (Actual cost of moves made)
%% ============================================================================

%% calculate_displacement_cost(+OriginalEvents, +ModifiedEvents, -GCost)
%% Measures how much events have been moved from their original positions.
%%
%% g(n) = Σ for each moved event:
%%   move_penalty(3) + hours_shifted × shift_weight(2) + priority × priority_factor

% Declarative penalty rules
move_penalty(3).
shift_penalty(2).
priority_penalty_weight(0.5).

% Declarative cost calculation for a single event
event_displacement_cost(event(Id, _, OSH, OSM, OEH, OEM, Priority, _), ModifiedEvents, Cost) :-
    member(event(Id, _, NSH, NSM, NEH, NEM, _, _), ModifiedEvents),
    time_to_minutes(OSH, OSM, OldStart),
    time_to_minutes(OEH, OEM, OldEnd),
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    (   (OldStart =\= NewStart ; OldEnd =\= NewEnd)
    ->  move_penalty(MovePenalty),
        shift_penalty(ShiftWeight),
        priority_penalty_weight(PriWeight),
        Shift is abs(NewStart - OldStart),
        ShiftHours is Shift / 60.0,
        ShiftCost is ShiftHours * ShiftWeight,
        PriorityPenalty is Priority * PriWeight,
        Cost is MovePenalty + ShiftCost + PriorityPenalty
    ;   Cost = 0
    ).

calculate_displacement_cost(OriginalEvents, ModifiedEvents, GCost) :-
    findall(EventCost, (
        member(E, OriginalEvents),
        event_displacement_cost(E, ModifiedEvents, EventCost)
    ), Costs),
    sum_list(Costs, GCost).

%% ============================================================================
%% h(n) — PRIORITY LOSS HEURISTIC (Estimated future cost)
%% ============================================================================

%% calculate_priority_loss(+ConflictingEvents, +Strategy, +Priorities, -HCost)
%% Estimates the cost of remaining conflicts that need resolution.
%%
%% h(n) = Σ for each remaining conflict:
%%   priority_weight × conflict_severity
%%
%% Strategy affects weights:
%%   minimize_moves: lower h(n) weight, prefer fewer moves
%%   maximize_quality: higher h(n) weight, protect high-priority
%%   balanced: equal weights

% Declarative priority loss rule
priority_loss(Priority, Weight, Loss) :-
    Loss is Priority * Priority * Weight.

calculate_priority_loss(ConflictingEvents, Strategy, _Priorities, HCost) :-
    strategy_weight(Strategy, StratWeight),
    findall(EventHCost, (
        member(event(_, _, _, _, _, _, Priority, _), ConflictingEvents),
        priority_loss(Priority, StratWeight, EventHCost)
    ), HCosts),
    sum_list(HCosts, HCost).

%% strategy_weight(+Strategy, -Weight)
%% How much to weigh priority loss based on users strategy
strategy_weight(minimize_moves, 0.5).     % Prefer fewer moves
strategy_weight(maximize_quality, 2.0).   % Protect high-priority events
strategy_weight(balanced, 1.0).           % Equal balance

%% ============================================================================
%% f(n) = g(n) + h(n) — COMBINED HEURISTIC
%% ============================================================================

%% calculate_heuristic(+OriginalEvents, +CurrentState, +RemainingConflicts, +Strategy, -FScore)
%% The A* evaluation function.
calculate_heuristic(OriginalEvents, CurrentState, RemainingConflicts, Strategy, FScore) :-
    calculate_displacement_cost(OriginalEvents, CurrentState, GCost),
    calculate_priority_loss(RemainingConflicts, Strategy, [], HCost),
    FScore is GCost + HCost.

%% ============================================================================
%% SLOT FINDING with Priority Awareness
%% ============================================================================

%% find_best_slot(+EventToMove, +AllEvents, +MinStartH, +MinStartM, +MaxEndH, +MaxEndM, -BestSlot)
%% Find the best available slot for an event, considering priority.
%% Returns slot(StartH, StartM, EndH, EndM, Cost)
find_best_slot(
    event(Id, Title, _SH, _SM, _EH, _EM, Priority, Type),
    AllEvents,
    MinStartH, MinStartM, MaxEndH, MaxEndM,
    BestSlot
) :-
    time_to_minutes(_SH, _SM, OrigStart),
    time_to_minutes(_EH, _EM, OrigEnd),
    Duration is OrigEnd - OrigStart,
    time_to_minutes(MinStartH, MinStartM, MinStart),
    time_to_minutes(MaxEndH, MaxEndM, MaxEnd),
    % Remove the event being moved from the list
    exclude(event_has_id(Id), AllEvents, OtherEvents),
    % Generate candidate slots (30-min granularity)
    Step = 30,
    MaxStart is MaxEnd - Duration,
    findall(
        scored_slot(Score, SlotSH, SlotSM, SlotEH, SlotEM),
        (
            between(0, 100, N),
            SlotStart is MinStart + N * Step,
            SlotStart =< MaxStart,
            SlotEnd is SlotStart + Duration,
            SlotEnd =< MaxEnd,
            % Check no overlap with other events
            \+ slot_conflicts_with_any(SlotStart, SlotEnd, OtherEvents),
            % Calculate score: distance from original + soft cost
            Displacement is abs(SlotStart - OrigStart),
            DisplacementCost is Displacement / 60.0 * 2,
            minutes_to_time(SlotStart, SlotSH, SlotSM),
            minutes_to_time(SlotEnd, SlotEH, SlotEM),
            calculate_soft_cost(
                event(Id, Title, SlotSH, SlotSM, SlotEH, SlotEM, Priority, Type),
                OtherEvents, [], SoftCost
            ),
            Score is DisplacementCost + SoftCost
        ),
        ScoredSlots
    ),
    ScoredSlots \= [],
    sort(ScoredSlots, [scored_slot(BestScore, BSH, BSM, BEH, BEM)|_]),
    BestSlot = slot(BSH, BSM, BEH, BEM, BestScore).

%% Helper: check if event has given ID
event_has_id(Id, event(Id, _, _, _, _, _, _, _)).

%% Helper: check if a slot conflicts with any event in list
slot_conflicts_with_any(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM, _, _), Events),
    time_to_minutes(SH, SM, EStart),
    time_to_minutes(EH, EM, EEnd),
    Start < EEnd,
    End > EStart,
    !.

%% ============================================================================
%% A* RESCHEDULING — Find optimal schedule
%% ============================================================================

%% reschedule_event(+NewEvent, +ExistingEvents, +Strategy, +MinH, +MinM, +MaxH, +MaxM, -Result)
%% When adding a new event that conflicts, find the optimal rescheduling.
%%
%% Returns: result(Action, MovedEvents, TotalCost)
%%   Action: place_new (place new event, move others)
%%         | move_new (move the new event to a free slot)
%%         | no_solution
reschedule_event(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
    ExistingEvents,
    Strategy,
    MinH, MinM, MaxH, MaxM,
    Result
) :-
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    % Find conflicting events
    findall(
        event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType),
        (
            member(event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType), ExistingEvents),
            time_to_minutes(ESH, ESM, ES),
            time_to_minutes(EEH, EEM, EE),
            NewStart < EE,
            NewEnd > ES
        ),
        ConflictingEvents
    ),
    (   ConflictingEvents = []
    ->  % No conflicts, just place the event
        Result = result(no_conflict, [], 0)
    ;
        % Strategy 1: Move the NEW event to a free slot
        NewEvent = event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
        (   find_best_slot(NewEvent, ExistingEvents, MinH, MinM, MaxH, MaxM, NewSlot)
        ->  NewSlot = slot(SlotSH, SlotSM, SlotEH, SlotEM, MoveCost1)
        ;   MoveCost1 = 9999, SlotSH = 0, SlotSM = 0, SlotEH = 0, SlotEM = 0
        ),
        Option1Cost is MoveCost1 + NewPriority * 0.5,

        % Strategy 2: Keep new event, move conflicting events
        try_move_conflicts(
            ConflictingEvents, ExistingEvents, NewEvent,
            MinH, MinM, MaxH, MaxM,
            MovedEvents2, MoveCost2
        ),
        (   MovedEvents2 = failed
        ->  Option2Cost = 9999
        ;   calculate_priority_loss(ConflictingEvents, Strategy, [], PLoss),
            Option2Cost is MoveCost2 + PLoss
        ),

        % Pick best option based on strategy
        pick_best_option(
            Strategy, NewPriority,
            option(move_new, slot(SlotSH, SlotSM, SlotEH, SlotEM), Option1Cost),
            option(place_new, MovedEvents2, Option2Cost),
            Result
        )
    ).

%% try_move_conflicts(+Conflicts, +AllEvents, +NewEvent, +Bounds, -Moved, -Cost)
%% Try to relocate all conflicting events to new slots
try_move_conflicts([], _AllEvents, _NewEvent, _MinH, _MinM, _MaxH, _MaxM, [], 0).
try_move_conflicts(
    [Event|Rest], AllEvents, NewEvent,
    MinH, MinM, MaxH, MaxM,
    [moved(Id, OSH, OSM, OEH, OEM, NSH2, NSM2, NEH2, NEM2, SlotCost)|RestMoved],
    TotalCost
) :-
    Event = event(Id, _Title, OSH, OSM, OEH, OEM, _Pri, _Type),
    % Build updated event list (with new event added, this event removed)
    exclude(event_has_id(Id), AllEvents, WithoutThis),
    append([NewEvent], WithoutThis, UpdatedEvents),
    % Find a new slot for this conflicting event
    find_best_slot(Event, UpdatedEvents, MinH, MinM, MaxH, MaxM, Slot),
    Slot = slot(NSH2, NSM2, NEH2, NEM2, SlotCost),
    % Recurse for remaining conflicts
    try_move_conflicts(Rest, AllEvents, NewEvent, MinH, MinM, MaxH, MaxM, RestMoved, RestCost),
    TotalCost is SlotCost + RestCost.
try_move_conflicts(_, _, _, _, _, _, _, failed, 9999).

%% pick_best_option(+Strategy, +NewPriority, +Option1, +Option2, -Result)
%% Choose between moving the new event vs moving existing events
pick_best_option(
    Strategy, NewPriority,
    option(move_new, Slot, Cost1),
    option(place_new, MovedEvents, Cost2),
    Result
) :-
    % Apply strategy weighting
    (   Strategy = minimize_moves
    ->  AdjCost1 is Cost1 * 0.7,   % Favor moving just the new event
        AdjCost2 is Cost2 * 1.3
    ;   Strategy = maximize_quality
    ->  % Favor protecting highest-priority event
        (   NewPriority >= 8
        ->  AdjCost1 is Cost1 * 2.0,  % Dont want to move high-priority new event
            AdjCost2 is Cost2 * 0.5
        ;   AdjCost1 is Cost1 * 0.5,
            AdjCost2 is Cost2 * 1.5
        )
    ;   % balanced
        AdjCost1 is Cost1,
        AdjCost2 is Cost2
    ),
    (   AdjCost1 =< AdjCost2, Cost1 < 9999
    ->  Slot = slot(SH, SM, EH, EM, _),
        Result = result(move_new, [moved_to(SH, SM, EH, EM)], Cost1)
    ;   MovedEvents \= failed, Cost2 < 9999
    ->  Result = result(place_new, MovedEvents, Cost2)
    ;   Cost1 < 9999
    ->  Slot = slot(SH2, SM2, EH2, EM2, _),
        Result = result(move_new, [moved_to(SH2, SM2, EH2, EM2)], Cost1)
    ;   Result = result(no_solution, [], 9999)
    ).

%% ============================================================================
%% FULL A* SCHEDULE OPTIMIZATION
%% ============================================================================

%% find_optimal_schedule(+Events, +NewEvent, +Strategy, +MinMax, +MaxDepth, -Solution)
%% A* search through possible schedule states to find the optimal arrangement.
%%
%% State: schedule(Events, Cost, Moves)
%% Goal: No hard constraint violations
find_optimal_schedule(Events, NewEvent, Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution) :-
    NewEvent = event(_, _, _, _, _, _, _, _),
    % Initial state: add new event to schedule
    append([NewEvent], Events, InitialEvents),
    % Check for conflicts
    find_all_conflicts(InitialEvents, Conflicts),
    (   Conflicts = []
    ->  Solution = solution(InitialEvents, 0, [])
    ;   % Run A* search
        InitialState = state(InitialEvents, Events, 0, [], Conflicts),
        astar_search([InitialState], [], Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution)
    ).

%% find_all_conflicts(+Events, -ConflictPairs)
%% Find all pairs of overlapping events
find_all_conflicts(Events, ConflictPairs) :-
    findall(
        conflict(Id1, Id2),
        (
            member(event(Id1, _, S1H, S1M, E1H, E1M, _, _), Events),
            member(event(Id2, _, S2H, S2M, E2H, E2M, _, _), Events),
            Id1 @< Id2,  % Avoid duplicates
            time_to_minutes(S1H, S1M, S1),
            time_to_minutes(E1H, E1M, E1),
            time_to_minutes(S2H, S2M, S2),
            time_to_minutes(E2H, E2M, E2),
            S1 < E2,
            S2 < E1
        ),
        ConflictPairs
    ).

%% astar_search(+OpenList, +ClosedList, +Strategy, +Bounds, +MaxDepth, -Solution)
%% A* search implementation
astar_search([], _Closed, _Strategy, _Bounds, _MaxDepth,
    solution([], 9999, [no_solution])) :- !.

astar_search(Open, _Closed, _Strategy, _Bounds, 0,
    solution(BestEvents, BestCost, BestMoves)) :-
    % Max depth reached, return best state found
    sort_states_by_cost(Open, [state(BestEvents, _, BestCost, BestMoves, _)|_]), !.

astar_search(Open, Closed, Strategy, Bounds, MaxDepth, Solution) :-
    % Pick state with lowest f-score
    sort_states_by_cost(Open, [Current|RestOpen]),
    Current = state(Events, OrigEvents, CurrentCost, Moves, Conflicts),
    (   Conflicts = []
    ->  % Goal reached: no conflicts
        Solution = solution(Events, CurrentCost, Moves)
    ;
        % Expand: try to resolve each conflict
        Bounds = bounds(MinH, MinM, MaxH, MaxM),
        NewDepth is MaxDepth - 1,
        findall(NextState, (
            member(conflict(Id1, Id2), Conflicts),
            % Try moving one of the conflicting events
            (   MovedId = Id1 ; MovedId = Id2 ),
            member(MovedEvent, Events),
            MovedEvent = event(MovedId, _, _, _, _, _, _, _),
            find_best_slot(MovedEvent, Events, MinH, MinM, MaxH, MaxM, Slot),
            Slot = slot(NSH, NSM, NEH, NEM, SlotCost),
            % Apply the move
            replace_event_time(Events, MovedId, NSH, NSM, NEH, NEM, NewEvents),
            % Calculate new cost
            NewCost is CurrentCost + SlotCost,
            % Check remaining conflicts
            find_all_conflicts(NewEvents, NewConflicts),
            % Build new state
            NewMoves = [move(MovedId, NSH, NSM, NEH, NEM)|Moves],
            NextState = state(NewEvents, OrigEvents, NewCost, NewMoves, NewConflicts),
            % Not in closed list
            \+ member(NextState, Closed)
        ), NewStates),
        append(RestOpen, NewStates, AllOpen),
        astar_search(AllOpen, [Current|Closed], Strategy, Bounds, NewDepth, Solution)
    ).

%% sort_states_by_cost(+States, -SortedStates)
sort_states_by_cost(States, Sorted) :-
    map_list_to_pairs(state_cost, States, Pairs),
    keysort(Pairs, SortedPairs),
    pairs_values(SortedPairs, Sorted).

state_cost(state(_, _, Cost, _, _), Cost).

%% replace_event_time(+Events, +Id, +NewSH, +NewSM, +NewEH, +NewEM, -Updated)
replace_event_time([], _, _, _, _, _, []).
replace_event_time(
    [event(Id, Title, _SH, _SM, _EH, _EM, Pri, Type)|Rest],
    Id, NewSH, NewSM, NewEH, NewEM,
    [event(Id, Title, NewSH, NewSM, NewEH, NewEM, Pri, Type)|RestUpdated]
) :- !,
    replace_event_time(Rest, Id, NewSH, NewSM, NewEH, NewEM, RestUpdated).
replace_event_time([E|Rest], Id, NSH, NSM, NEH, NEM, [E|RestUpdated]) :-
    replace_event_time(Rest, Id, NSH, NSM, NEH, NEM, RestUpdated).

%% ============================================================================
%% CHAIN CONFLICT DETECTION
%% ============================================================================

%% detect_chain_conflicts(+MovedEventId, +NewStart, +NewEnd, +AllEvents, -ChainConflicts)
%% If we move event A, check if it creates new conflicts with B, C, etc.
detect_chain_conflicts(MovedId, NewSH, NewSM, NewEH, NewEM, AllEvents, ChainConflicts) :-
    time_to_minutes(NewSH, NewSM, NewStart),
    time_to_minutes(NewEH, NewEM, NewEnd),
    findall(
        chain_conflict(ConflictId, ConflictTitle),
        (
            member(event(ConflictId, ConflictTitle, CSH, CSM, CEH, CEM, _, _), AllEvents),
            ConflictId \= MovedId,
            time_to_minutes(CSH, CSM, CStart),
            time_to_minutes(CEH, CEM, CEnd),
            NewStart < CEnd,
            NewEnd > CStart
        ),
        ChainConflicts
    ).

%% ============================================================================
%% USER-FACING SUGGESTIONS
%% ============================================================================

%% suggest_reschedule_options(+NewEvent, +ExistingEvents, +Strategy, +MinH, +MinM, +MaxH, +MaxM, -Options)
%% Generate multiple rescheduling options for the user to choose from.
%% Returns up to 3 options sorted by cost.
suggest_reschedule_options(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPri, NewType),
    ExistingEvents,
    Strategy,
    MinH, MinM, MaxH, MaxM,
    Options
) :-
    NewEvent = event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPri, NewType),
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    Duration is NewEnd - NewStart,

    % Find conflicting events
    findall(
        event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType),
        (
            member(event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType), ExistingEvents),
            time_to_minutes(ESH, ESM, ES),
            time_to_minutes(EEH, EEM, EE),
            NewStart < EE,
            NewEnd > ES
        ),
        Conflicts
    ),

    (   Conflicts = []
    ->  Options = [option(no_conflict, [], 0, 'No conflicts detected')]
    ;
        % Option A: Move new event to nearest free slot
        findall(
            option(move_new, [moved_to(SH, SM, EH, EM)], Score, Description),
            (
                find_near_slot(NewStart, Duration, ExistingEvents, MinH, MinM, MaxH, MaxM, SH, SM, EH, EM, Score),
                format(atom(Description), 'Move "~w" to ~w:~w-~w:~w', [NewTitle, SH, SM, EH, EM])
            ),
            OptionAs
        ),

        % Option B: Move each conflicting event
        findall(
            option(move_existing, MovedList, TotalCost, Description),
            (
                member(ConflictEvent, Conflicts),
                ConflictEvent = event(CId, CTitle, _, _, _, _, CPri, _),
                find_best_slot(ConflictEvent, [NewEvent|ExistingEvents], MinH, MinM, MaxH, MaxM, CSlot),
                CSlot = slot(CSH, CSM, CEH, CEM, SlotCost),
                TotalCost is SlotCost + CPri * 0.3,
                MovedList = [moved(CId, CSH, CSM, CEH, CEM)],
                format(atom(Description), 'Move "~w" to ~w:~w-~w:~w (priority: ~w)',
                    [CTitle, CSH, CSM, CEH, CEM, CPri])
            ),
            OptionBs
        ),

        % Combine and sort all options
        append(OptionAs, OptionBs, AllOptions),
        sort_options(AllOptions, SortedOptions),
        take_n(3, SortedOptions, Options)
    ).

%% find_near_slot: find free slots near the original time
find_near_slot(OrigStart, Duration, Events, MinH, MinM, MaxH, MaxM, SH, SM, EH, EM, Score) :-
    time_to_minutes(MinH, MinM, MinStart),
    time_to_minutes(MaxH, MaxM, MaxEnd),
    Step = 30,
    MaxSlotStart is MaxEnd - Duration,
    between(0, 100, N),
    SlotStart is MinStart + N * Step,
    SlotStart =< MaxSlotStart,
    SlotEnd is SlotStart + Duration,
    SlotEnd =< MaxEnd,
    \+ slot_conflicts_with_any(SlotStart, SlotEnd, Events),
    Displacement is abs(SlotStart - OrigStart),
    Score is Displacement / 60.0 * 2,
    minutes_to_time(SlotStart, SH, SM),
    minutes_to_time(SlotEnd, EH, EM).

%% sort_options(+Options, -Sorted)
sort_options(Options, Sorted) :-
    map_list_to_pairs(option_cost, Options, Pairs),
    keysort(Pairs, SortedPairs),
    pairs_values(SortedPairs, Sorted).

option_cost(option(_, _, Cost, _), Cost).

%% take_n(+N, +List, -FirstN)
take_n(_, [], []) :- !.
take_n(0, _, []) :- !.
take_n(N, [H|T], [H|Rest]) :-
    N > 0,
    N1 is N - 1,
    take_n(N1, T, Rest).

%% ============================================================================
%% UTILITY: Sum a list of numbers
%% ============================================================================
sum_list([], 0).
sum_list([H|T], Sum) :-
    sum_list(T, RestSum),
    Sum is H + RestSum.
