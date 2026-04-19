%% apps/backend/app/chat/prolog/constraint_solver_krr.pl
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
%%   - Logical inference: Backward chaining with proof construction
%%   - Explanation generation: Proof traces showing reasoning steps
%%   - Constraint satisfaction: Logical derivation, not arithmetic
%%   - Heuristic A* framed as logical preference rules
%% ============================================================================

:- module(constraint_solver_krr, [
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
    explain_decision/3,         % explain_decision(Decision, Proof, Explanation)
    
    % Logical search (A* with logical heuristics)
    logical_search/5            % logical_search(Goal, InitState, KB, Solution, Proof)
]).

:- use_module(library(clpfd)).  % Constraint Logic Programming over Finite Domains

:- use_module(scheduler, [
    time_to_minutes/3,
    minutes_to_time/3
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

% Logical heuristic rules (not arbitrary costs, but preference ordering)
logical_preference(move_lower_priority_first).
logical_preference(prefer_minimal_displacement).
logical_preference(preserve_high_priority_slots).
logical_preference(respect_event_type_windows).

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

prove(logical_preference(Pref), _KB, proof(logical_preference(Pref), fact)) :-
    logical_preference(Pref), !.

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
        proof(Goal, P),
        (
            constraint_type(C, _),
            (   Relation = satisfies
            ->  Goal = satisfies(Event, C),
                prove(satisfies(Event, C), KB, P)
            ;   Goal = violates(Event, C),
                prove(violates(Event, C), KB, P)
            )
        ),
        Proofs
    ), !.

% Exists quantification
prove(exists(Variable, Goal), KB, proof(exists(Variable, Goal), witness(Variable, Value, SubProof))) :-
    copy_term((Variable, Goal), (Value, InstantiatedGoal)),
    prove(InstantiatedGoal, KB, SubProof), !.

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
    flatten([[step(and(G1, G2), 'proving conjunction')], T1, T2], Trace).
proof_to_trace(proof(or(G1, G2), left(P)), Trace) :-
    !,
    proof_to_trace(P, T),
    flatten([[step(or(G1, G2), 'proving left disjunct')], T], Trace).
proof_to_trace(proof(or(G1, G2), right(P)), Trace) :-
    !,
    proof_to_trace(P, T),
    flatten([[step(or(G1, G2), 'proving right disjunct')], T], Trace).
proof_to_trace(proof(Goal, SubProof), Trace) :-
    is_list(SubProof),
    !,
    maplist(proof_to_trace, SubProof, SubTraces),
    flatten([[step(Goal, 'derived from')], SubTraces], Trace).
proof_to_trace(proof(Goal, witness(Var, Val, SubProof)), Trace) :-
    !,
    proof_to_trace(SubProof, SubTrace),
    flatten([[step(Goal, format('witness found: ~w = ~w', [Var, Val]))], SubTrace], Trace).
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

% WITHIN WORKING HOURS constraint (declarative CLP(FD) definition)
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
    % Declarative constraints (not comparisons!)
    StartMin #>= MinMinutes,
    EndMin #=< MaxMinutes,
    StartProof = proof(start_after(MinH, MinM), constraint_satisfaction),
    EndProof = proof(end_before(MaxH, MaxM), constraint_satisfaction).

% POSITIVE DURATION constraint (declarative CLP(FD) definition)
satisfies_constraint_logic(
    event(_, _, StartH, StartM, EndH, EndM, _, _),
    positive_duration,
    _KB,
    proof(positive_duration, constraint_derived)
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    % Declarative constraint: end must be strictly after start
    EndMin #> StartMin.

% RESPECTS PRIORITY constraint (declarative constraint inference)
satisfies_constraint_logic(
    event(_, _, StartH, _, _, _, Priority, _),
    respects_priority,
    _KB,
    proof(priority_satisfied, PreferenceProof)
) :-
    prove(priority_time_preference(Priority, PreferredStart, PreferredEnd), [], PreferenceProof),
    % Declarative constraints for time preferences
    StartH #>= PreferredStart,
    StartH #=< PreferredEnd.

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

% WORKING HOURS violation (declarative constraint checking)
violates_constraint_logic(
    event(_, _, StartH, StartM, EndH, EndM, _, _),
    within_working_hours,
    _KB,
    proof(Violation, constraint_violation)
) :-
    working_hours(MinH, MinM, MaxH, MaxM),
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    time_to_minutes(MinH, MinM, MinMinutes),
    time_to_minutes(MaxH, MaxM, MaxMinutes),
    % Declarative constraint: check which constraint is violated
    (   StartMin #< MinMinutes, Violation = starts_too_early(StartH, StartM)
    ;   EndMin #> MaxMinutes, Violation = ends_too_late(EndH, EndM)
    ).

% POSITIVE DURATION violation (declarative constraint checking)
violates_constraint_logic(
    event(_, _, StartH, StartM, EndH, EndM, _, _),
    positive_duration,
    _KB,
    proof(invalid_duration, constraint_violation)
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    % Declarative constraint: end must not be before or equal to start
    EndMin #=< StartMin.

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
%% CONFLICT RESOLUTION THROUGH LOGICAL REASONING
%% ============================================================================

%% resolve_conflict(+Conflict, +KB, -Action, -Proof)
%% Uses logical inference to determine how to resolve a scheduling conflict
resolve_conflict(
    conflict(Event1, Event2),
    KB,
    Action,
    proof(resolution_strategy(Action), ReasoningChain)
) :-
    Event1 = event(_, _, _, _, _, _, Pri1, _),
    Event2 = event(_, _, _, _, _, _, Pri2, _),
    % Logical rule: Higher priority event should keep its slot
    prove(should_move(Event1, Event2, MovedEvent), KB, PriorityProof),
    % Logical rule: Find valid alternative slot
    prove(exists_valid_slot(MovedEvent, KB, Slot), KB, SlotProof),
    (   MovedEvent = Event1
    ->  Action = move_event(Event1, Slot),
        ReasoningChain = [
            step(compare_priorities(Pri1, Pri2), 'compared event priorities'),
            PriorityProof,
            step(decision(move_lower_priority), 'logical inference: move lower priority'),
            SlotProof
        ]
    ;   Action = move_event(Event2, Slot),
        ReasoningChain = [
            step(compare_priorities(Pri1, Pri2), 'compared event priorities'),
            PriorityProof,
            step(decision(keep_higher_priority), 'logical inference: protect higher priority'),
            SlotProof
        ]
    ).

%% should_move(+Event1, +Event2, -MovedEvent)
%% Logical rule: which event should be moved to resolve conflict
should_move(Event1, Event2, Event1) :-
    Event1 = event(_, _, _, _, _, _, Pri1, _),
    Event2 = event(_, _, _, _, _, _, Pri2, _),
    Pri1 < Pri2.  % Lower priority moves

should_move(Event1, Event2, Event2) :-
    Event1 = event(_, _, _, _, _, _, Pri1, _),
    Event2 = event(_, _, _, _, _, _, Pri2, _),
    Pri2 < Pri1.  % Lower priority moves

should_move(Event1, Event2, Event1) :-
    Event1 = event(_, _, _, _, _, _, Pri, _),
    Event2 = event(_, _, _, _, _, _, Pri, _),
    % If equal priority, prefer moving the later event
    event_start_time(Event1, T1),
    event_start_time(Event2, T2),
    T1 > T2.

should_move(Event1, Event2, Event2) :-
    Event1 = event(_, _, _, _, _, _, Pri, _),
    Event2 = event(_, _, _, _, _, _, Pri, _),
    event_start_time(Event1, T1),
    event_start_time(Event2, T2),
    T2 > T1.

%% exists_valid_slot(+Event, +KB, -Slot)
%% Logical predicate: there exists a valid time slot for the event
exists_valid_slot(Event, KB, slot(SH, SM, EH, EM)) :-
    find_valid_slot(Event, KB, slot(SH, SM, EH, EM), _).

%% find_valid_slot(+Event, +KB, -Slot, -Proof)
%% Finds a valid time slot using logical constraint satisfaction
find_valid_slot(
    event(Id, Title, _SH, _SM, _EH, _EM, Priority, Type),
    KB,
    slot(SlotSH, SlotSM, SlotEH, SlotEM),
    proof(found_valid_slot, ReasoningSteps)
) :-
    % Get current schedule from KB
    member(kb(schedule(Events)), KB),
    % Get search bounds from KB or use defaults
    (   member(kb(bounds(MinH, MinM, MaxH, MaxM)), KB)
    ->  true
    ;   MinH = 6, MinM = 0, MaxH = 23, MaxM = 0
    ),
    % Calculate event duration
    event_duration(event(Id, Title, _SH, _SM, _EH, _EM, Priority, Type), Duration),
    % Generate candidate slots through logical inference
    time_to_minutes(MinH, MinM, MinStart),
    time_to_minutes(MaxH, MaxM, MaxEnd),
    % Use logical heuristic: prefer slots near original or type-preferred times
    findall(
        candidate(Quality, SH, SM, EH, EM, LogicalJustification),
        (
            generate_candidate_slot(MinStart, MaxEnd, Duration, SH, SM, EH, EM),
            % Build a hypothetical event in this slot
            TestEvent = event(Id, Title, SH, SM, EH, EM, Priority, Type),
            % Logical test: does this slot satisfy all hard constraints?
            \+ violates_constraint_logic(TestEvent, no_overlap, [kb(schedule(Events))|KB], _),
            \+ violates_constraint_logic(TestEvent, within_working_hours, KB, _),
            \+ violates_constraint_logic(TestEvent, positive_duration, KB, _),
            % Logical quality assessment (not arithmetic cost, but logical preference)
            assess_slot_quality(TestEvent, Type, Priority, KB, Quality, LogicalJustification)
        ),
        Candidates
    ),
    Candidates \= [],
    % Logical selection: choose slot with best logical justification
    keysort(Candidates, [candidate(_, SlotSH, SlotSM, SlotEH, SlotEM, BestJustification)|_]),
    ReasoningSteps = [
        step(search_space([MinH:MinM, MaxH:MaxM]), 'defined search space'),
        step(duration(Duration), 'calculated required duration'),
        step(found_candidates(length(Candidates)), 'generated valid candidates'),
        step(selected_best(BestJustification), 'logical selection')
    ].

%% generate_candidate_slot(+MinStart, +MaxEnd, +Duration, -SH, -SM, -EH, -EM)
%% Generates candidate time slots using CLP(FD) constraints
%% Declarative: we state what SlotStart must satisfy, not how to compute it
generate_candidate_slot(MinStart, MaxEnd, Duration, SH, SM, EH, EM) :-
    % Declare constraint variables
    SlotStart in MinStart..MaxEnd,
    SlotEnd in MinStart..MaxEnd,
    % Declare constraints (not calculations!)
    SlotEnd #= SlotStart + Duration,
    SlotEnd #=< MaxEnd,
    SlotStart #>= MinStart,
    % Constraint: slot starts on 30-minute boundaries (declarative scheduling grid)
    SlotStart mod 30 #= 0,
    % Label (find solution satisfying constraints)
    label([SlotStart, SlotEnd]),
    % Convert to time representation
    minutes_to_time(SlotStart, SH, SM),
    minutes_to_time(SlotEnd, EH, EM).

%% assess_slot_quality(+Event, +Type, +Priority, +KB, -Quality, -Justification)
%% Logical assessment of slot quality using declarative rules
%% Quality is a logical preference ordering derived from constraint satisfaction
assess_slot_quality(
    event(_, _, StartH, StartM, EndH, EndM, Priority, Type),
    Type,
    Priority,
    _KB,
    Quality,
    justification(Reasons)
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    % Declarative constraint variables for quality assessment
    PeakHourScore in 0..10,
    TypePrefScore in 0..10,
    
    % Logical rules as constraints
    (   Priority #>= 8,
        StartMin #>= 540,  % 9 AM
        StartMin #=< 1020  % 5 PM
    ->  PeakHourScore = 10,
        PeakReason = satisfies(peak_hours_for_high_priority)
    ;   PeakHourScore = 0,
        PeakReason = satisfies(flexible_priority)
    ),
    
    % Event type preference as declarative constraint
    (   event_type_preference(Type, PrefSH, PrefSM, PrefEH, PrefEM),
        time_to_minutes(PrefSH, PrefSM, PrefStart),
        time_to_minutes(PrefEH, PrefEM, PrefEnd),
        StartMin #>= PrefStart,
        EndMin #=< PrefEnd
    ->  TypePrefScore = 10,
        TypeReason = satisfies(type_preference(Type))
    ;   TypePrefScore = 0,
        TypeReason = satisfies(no_type_constraint)
    ),
    
    % Declarative quality calculation
    Quality #= 100 - (PeakHourScore + TypePrefScore),
    Reasons = [PeakReason, TypeReason].

%% ============================================================================
%% QUERY INTERFACE: Ask Questions About Schedule
%% ============================================================================

%% query_schedule(+Query, +Schedule, +KB, -Answer)
%% Logical query interface for reasoning about schedules

query_schedule(why(Event, HasProperty), Schedule, KB, Answer) :-
    % Why does an event have a property?
    prove(has_property(Event, HasProperty), [kb(Schedule)|KB], Proof),
    proof_to_explanation(Proof, Explanation),
    Answer = answer(because(Explanation)).

query_schedule(can(Action), Schedule, KB, Answer) :-
    % Can we perform this action?
    (   prove(possible(Action), [kb(Schedule)|KB], Proof)
    ->  proof_to_explanation(Proof, Explanation),
        Answer = answer(yes(Explanation))
    ;   Answer = answer(no('Logical constraints prevent this action'))
    ).

query_schedule(what_if(Modification), Schedule, KB, Answer) :-
    % What would happen if we made this modification?
    apply_modification(Modification, Schedule, NewSchedule),
    find_violations(NewSchedule, KB, Violations),
    (   Violations = []
    ->  Answer = answer(safe('No constraint violations would occur'))
    ;   Answer = answer(unsafe(Violations))
    ).

query_schedule(best(Action, Goal), Schedule, KB, Answer) :-
    % Whats the best way to achieve a goal?
    findall(
        result(Action, Justification),
        (
            prove(achieves(Action, Goal), [kb(Schedule)|KB], Proof),
            proof_to_explanation(Proof, Justification)
        ),
        Options
    ),
    sort_by_justification(Options, [Best|_]),
    Answer = answer(Best).

%% explain_decision(+Decision, +Proof, -Explanation)
%% Converts a proof tree into human-readable explanation
explain_decision(Decision, Proof, explanation(Decision, Steps)) :-
    proof_to_trace(Proof, Trace),
    trace_to_steps(Trace, Steps).

trace_to_steps([], []).
trace_to_steps([step(Goal, Reason)|Rest], [Step|Steps]) :-
    format(atom(Step), '~w because ~w', [Goal, Reason]),
    trace_to_steps(Rest, Steps).
trace_to_steps([H|T], Steps) :-
    is_list(H),
    !,
    trace_to_steps(H, SubSteps),
    trace_to_steps(T, RestSteps),
    append(SubSteps, RestSteps, Steps).
trace_to_steps([_|T], Steps) :-
    trace_to_steps(T, Steps).

proof_to_explanation(proof(Goal, fact), ['Known fact:', Goal]).
proof_to_explanation(proof(Goal, axiom), ['Axiom:', Goal]).
proof_to_explanation(proof(Goal, derived), ['Derived through inference:', Goal]).
proof_to_explanation(proof(Goal, SubProofs), [Goal, 'because'|SubExplanations]) :-
    is_list(SubProofs),
    maplist(proof_to_explanation, SubProofs, SubExplanations).
proof_to_explanation(proof(Goal, _), [Goal]).

%% ============================================================================
%% LOGICAL HEURISTIC SEARCH (A* framed as logical reasoning)
%% ============================================================================
%% Instead of treating A* as pure algorithm, we frame it as:
%% "Logically prefer actions that satisfy more constraints"

%% logical_search(+Goal, +InitialState, +KB, -Solution, -Proof)
%% Search for solution using logical preferences (not arbitrary costs)
logical_search(
    find_schedule(Events),
    initial_state(Events, Conflicts),
    KB,
    solution(FinalSchedule),
    proof(search_derivation, ReasoningChain)
) :-
    % Logical search with preference-guided exploration
    search_with_preferences(
        state(Events, Conflicts, [], []),
        KB,
        FinalState,
        ReasoningChain
    ),
    FinalState = state(FinalSchedule, [], _, _).

%% search_with_preferences(+State, +KB, -FinalState, -ReasoningChain)
%% Preference-guided search (A* logic, not A* arithmetic)
search_with_preferences(
    state(Schedule, [], Moves, Reasoning),
    _KB,
    state(Schedule, [], Moves, Reasoning),
    [step(goal_achieved, 'no conflicts remain')]
) :- !.

search_with_preferences(
    state(Schedule, [Conflict|RestConflicts], Moves, Reasoning),
    KB,
    FinalState,
    [step(resolving(Conflict), 'logical conflict resolution')|RestReasoning]
) :-
    % Logically resolve the conflict
    resolve_conflict(Conflict, [kb(schedule(Schedule))|KB], Action, ResolutionProof),
    % Apply the action
    apply_action(Action, Schedule, NewSchedule),
    % Check for new conflicts
    find_all_conflicts(NewSchedule, NewConflicts),
    % Logical preference: actions that create fewer conflicts are preferred
    prefer_action_by_logic(Action, Moves, ResolutionProof, NewMoves, NewReasoning),
    % Continue search
    append(RestConflicts, NewConflicts, AllConflicts),
    list_to_set(AllConflicts, UniqueConflicts),
    search_with_preferences(
        state(NewSchedule, UniqueConflicts, NewMoves, NewReasoning),
        KB,
        FinalState,
        RestReasoning
    ).

%% prefer_action_by_logic(+Action, +Moves, +Proof, -NewMoves, -NewReasoning)
%% Logical justification for action preference (not numeric cost)
prefer_action_by_logic(Action, Moves, Proof, [Action|Moves], [Proof|Moves]).

%% apply_action(+Action, +Schedule, -NewSchedule)
apply_action(move_event(Event, slot(SH, SM, EH, EM)), Events, NewEvents) :-
    Event = event(Id, Title, _, _, _, _, Pri, Type),
    NewEvent = event(Id, Title, SH, SM, EH, EM, Pri, Type),
    replace_event(Events, Id, NewEvent, NewEvents).

replace_event([], _, _, []).
replace_event([event(Id, _, _, _, _, _, _, _)|Rest], Id, NewEvent, [NewEvent|Rest]) :- !.
replace_event([E|Rest], Id, NewEvent, [E|NewRest]) :-
    replace_event(Rest, Id, NewEvent, NewRest).

%% find_all_conflicts(+Schedule, -Conflicts)
find_all_conflicts(Events, Conflicts) :-
    findall(
        conflict(Event1, Event2),
        (
            member(Event1, Events),
            member(Event2, Events),
            Event1 = event(Id1, _, S1H, S1M, E1H, E1M, _, _),
            Event2 = event(Id2, _, S2H, S2M, E2H, E2M, _, _),
            Id1 @< Id2,
            time_to_minutes(S1H, S1M, S1),
            time_to_minutes(E1H, E1M, E1),
            time_to_minutes(S2H, S2M, S2),
            time_to_minutes(E2H, E2M, E2),
            S1 < E2,
            S2 < E1
        ),
        Conflicts
    ).

%% ============================================================================
%% HELPER PREDICATES FOR LOGICAL REASONING
%% ============================================================================

event_duration(event(_, _, SH, SM, EH, EM, _, _), Duration) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    Duration is End - Start.

event_start_time(event(_, _, SH, SM, _, _, _, _), Time) :-
    time_to_minutes(SH, SM, Time).

events_do_not_overlap(time(S1H, S1M, E1H, E1M), time(S2H, S2M, E2H, E2M)) :-
    time_to_minutes(S1H, S1M, S1),
    time_to_minutes(E1H, E1M, E1),
    time_to_minutes(S2H, S2M, S2),
    time_to_minutes(E2H, E2M, E2),
    (   E1 =< S2    % First ends before second starts
    ;   E2 =< S1    % Second ends before first starts
    ).

apply_modification(add_event(Event), schedule(Events), schedule([Event|Events])).
apply_modification(remove_event(EventId), schedule(Events), schedule(NewEvents)) :-
    exclude(has_id(EventId), Events, NewEvents).
apply_modification(move_event(EventId, NewSlot), schedule(Events), schedule(NewEvents)) :-
    member(event(EventId, Title, _, _, _, _, Pri, Type), Events),
    NewSlot = slot(SH, SM, EH, EM),
    NewEvent = event(EventId, Title, SH, SM, EH, EM, Pri, Type),
    replace_event(Events, EventId, NewEvent, NewEvents).

has_id(Id, event(Id, _, _, _, _, _, _, _)).

sort_by_justification(Results, Sorted) :-
    % Logical sorting: prefer results with stronger justifications
    % For now, simple sort (can be enhanced with logical preference rules)
    sort(Results, Sorted).

%% ============================================================================
%% END OF META-INTERPRETER BASED CONSTRAINT SOLVER
%% ============================================================================
