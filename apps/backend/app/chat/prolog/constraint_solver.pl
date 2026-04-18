%% apps/backend/app/chat/prolog/constraint_solver.pl
%% ============================================================================
%% Enhanced Constraint Solver with Meta-Interpreter Architecture
%% ============================================================================
%%
%% This module implements constraint-based schedule optimisation using
%% Knowledge Representation and Reasoning (KR&R) with a meta-interpreter.
%%
%%   Layer 1 — Domain Knowledge:
%%     Named facts that encode scheduling domain knowledge
%%     (working hours, preferred windows, capacity limits, cost weights).
%%     No magic numbers — every constant has a descriptive name.
%%
%%   Layer 1b — Constraint Rules:
%%     constraint_rule/2 facts expressed in near-natural language.
%%     Rules describe WHAT a constraint violation means.
%%
%%   Layer 2 — Constraint Solver (Meta-Interpreter):
%%     solve_constraint/1 interprets constraint rules, delegates shared
%%     knowledge to scheduler:solve/1, and falls back to compute_constraint/1.
%%
%%   Layer 3 — Computation:
%%     All arithmetic is hidden inside compute_constraint/1 predicates.
%%
%%   Procedural Layer:
%%     A* search and slot scoring remain algorithmic but USE the solver
%%     for all constraint evaluation and domain lookups.
%% ============================================================================

:- module(constraint_solver, [
    validate_hard_constraints/3,
    calculate_soft_cost/4,
    calculate_displacement_cost/3,
    calculate_priority_loss/4,
    calculate_heuristic/5,
    find_best_slot/7,
    reschedule_event/8,
    find_optimal_schedule/6,
    detect_chain_conflicts/7,
    suggest_reschedule_options/8
]).

:- use_module(scheduler, [
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3,
    solve/1
]).

%% Fallback: if module-name resolution fails, try same-directory file path.
%% This handles cases where the files are loaded via absolute paths (e.g., pyswip).
:- (   current_module(scheduler)
   ->  true
   ;   prolog_load_context(directory, Dir),
       atom_concat(Dir, '/scheduler', Path),
       use_module(Path, [
           time_to_minutes/3,
           minutes_to_time/3,
           events_overlap/4,
           slot_conflicts_with_events/3,
           solve/1
       ])
   ).

%% ============================================================================
%% Layer 1: Domain Knowledge — Named Facts
%% ============================================================================
%%
%% Every scheduling constant lives here as a named fact.
%% To change a policy (e.g., extend working hours), edit ONE fact.
%% ============================================================================

%% Boundaries of the working day
working_hours(start, 6, 0).    % 06:00
working_hours(end,  23, 0).    % 23:00

%% Peak productivity hours
peak_hours(start, 9, 0).       % 09:00
peak_hours(end,  17, 0).       % 17:00

%% Preferred time windows per event type (may have multiple windows)
type_preferred_window(meeting,  9, 0, 17, 0).
type_preferred_window(study,    8, 0, 12, 0).
type_preferred_window(study,   14, 0, 18, 0).
type_preferred_window(exercise,  6, 0,  8, 0).
type_preferred_window(exercise, 17, 0, 23, 0).

%% Minimum gap between consecutive events
minimum_buffer(15).

%% Daily event-count thresholds
daily_capacity(comfortable, 6).
daily_capacity(heavy, 8).

%% A* displacement cost parameters
move_penalty(3).
shift_weight(2.0).
priority_factor(0.5).

%% Strategy weights for priority-loss heuristic h(n)
strategy_weight(minimize_moves,  0.5).
strategy_weight(maximize_quality, 2.0).
strategy_weight(balanced,         1.0).

%% Strategy cost adjustments for option comparison
strategy_adjustment(minimize_moves,  move_new,  0.7).
strategy_adjustment(minimize_moves,  place_new, 1.3).
strategy_adjustment(maximize_quality, move_new_high_priority,  2.0).
strategy_adjustment(maximize_quality, place_new_high_priority, 0.5).
strategy_adjustment(maximize_quality, move_new_low_priority,   0.5).
strategy_adjustment(maximize_quality, place_new_low_priority,  1.5).

%% Threshold above which an event is considered high-priority
high_priority_threshold(8).

%% Penalty rates
proximity_penalty_per_event(3).
overload_penalty(heavy,       5).
overload_penalty(comfortable, 2).
priority_time_penalty_multiplier(3).

%% ============================================================================
%% Layer 1b: Constraint Rules — Human-Readable Knowledge
%% ============================================================================
%%
%% Declared as constraint_rule(Conclusion, [Condition1, ...]).
%% The constraint solver proves Conclusion by proving every Condition.
%% ============================================================================

%% "An event starts before working hours when its start time
%%  is earlier than the working-hours start boundary."
constraint_rule(
    before_working_hours(StartMin),
    [ working_hours_start_minutes(Boundary),
      starts_before(StartMin, Boundary) ]
).

%% "An event runs past working hours when its end time
%%  exceeds the working-hours end boundary."
constraint_rule(
    after_working_hours(EndMin),
    [ working_hours_end_minutes(Boundary),
      exceeds_limit(EndMin, Boundary) ]
).

%% "An event has invalid duration when its end is not after its start."
constraint_rule(
    invalid_event_duration(StartMin, EndMin),
    [ end_not_after_start(StartMin, EndMin) ]
).

%% "A time falls inside a preferred window for a given event type."
constraint_rule(
    in_preferred_window(Type, StartMin),
    [ time_in_preferred_window(Type, StartMin) ]
).

%% "Events are too close together when the gap between them
%%  is smaller than the minimum required buffer."
constraint_rule(
    events_too_close(StartMin, EndMin, AllEvents),
    [ count_buffer_violations(StartMin, EndMin, AllEvents, Count),
      count_is_positive(Count) ]
).

%% "A day is overloaded at a given capacity level when the number
%%  of events exceeds that level's threshold."
constraint_rule(
    day_is_overloaded(AllEvents, Level),
    [ event_count_exceeds_capacity(AllEvents, Level) ]
).

%% "A high-priority event is at a suboptimal time when its
%%  priority crosses the threshold and the time is outside peak hours."
constraint_rule(
    high_priority_at_suboptimal_time(Priority, StartMin),
    [ priority_exceeds_threshold(Priority),
      time_outside_peak_hours(StartMin) ]
).

%% ============================================================================
%% Layer 2: Meta-Interpreter (Constraint Solver)
%% ============================================================================
%%
%% Resolves constraint goals by:
%%   1. Trivially true / conjunction handling
%%   2. Negation-as-failure
%%   3. Looking up constraint_rule/2 and solving its body
%%   4. Delegating to scheduler:solve/1 for shared rules
%%   5. Falling back to compute_constraint/1 for arithmetic
%% ============================================================================

solve_constraint(true) :- !.

solve_constraint([]) :- !.

solve_constraint([Goal | Rest]) :- !,
    solve_constraint(Goal),
    solve_constraint(Rest).

solve_constraint(not(Goal)) :- !,
    \+ solve_constraint(Goal).

% Constraint rule resolution
solve_constraint(Goal) :-
    constraint_rule(Goal, Body),
    solve_constraint(Body).

% Delegate to schedulers solver (shared knowledge like intervals_overlap)
solve_constraint(Goal) :-
    solve(Goal).

% Ground computation fallback
solve_constraint(Goal) :-
    compute_constraint(Goal).

%% ============================================================================
%% Layer 3: Computation — Hidden Arithmetic
%% ============================================================================
%%
%% All mathematical operations abstracted behind descriptive names.
%% The solver delegates here; callers never see raw arithmetic.
%% ============================================================================

%% Convert hours and minutes to total minutes (thin wrapper)
compute_constraint(convert_to_minutes(H, M, Total)) :-
    time_to_minutes(H, M, Total).

%% Look up working-hours start boundary in minutes
compute_constraint(working_hours_start_minutes(Boundary)) :-
    working_hours(start, H, M),
    time_to_minutes(H, M, Boundary).

%% Look up working-hours end boundary in minutes
compute_constraint(working_hours_end_minutes(Boundary)) :-
    working_hours(end, H, M),
    time_to_minutes(H, M, Boundary).

%% "Value exceeds Limit"
compute_constraint(exceeds_limit(Value, Limit)) :-
    number(Value), number(Limit),
    Value > Limit.

%% "End is not after start (invalid duration)"
compute_constraint(end_not_after_start(Start, End)) :-
    End =< Start.

%% "StartMin falls within a preferred time window for Type"
compute_constraint(time_in_preferred_window(Type, StartMin)) :-
    type_preferred_window(Type, WStartH, WStartM, WEndH, WEndM),
    time_to_minutes(WStartH, WStartM, WStart),
    time_to_minutes(WEndH, WEndM, WEnd),
    StartMin >= WStart,
    StartMin =< WEnd.

%% Count how many events violate the minimum buffer
compute_constraint(count_buffer_violations(StartMin, EndMin, AllEvents, Count)) :-
    minimum_buffer(Buffer),
    findall(1, (
        member(event(_, _, OSH, OSM, OEH, OEM, _, _), AllEvents),
        time_to_minutes(OSH, OSM, OStart),
        time_to_minutes(OEH, OEM, OEnd),
        (   (OEnd > StartMin - Buffer, OEnd =< StartMin)
        ;   (OStart >= EndMin, OStart < EndMin + Buffer)
        )
    ), Violations),
    length(Violations, Count).

%% "A count is positive"
compute_constraint(count_is_positive(Count)) :-
    Count > 0.

%% "Event count exceeds the daily capacity at a given level"
compute_constraint(event_count_exceeds_capacity(AllEvents, Level)) :-
    length(AllEvents, NumEvents),
    daily_capacity(Level, Threshold),
    NumEvents > Threshold.

%% "Priority crosses the high-priority threshold"
compute_constraint(priority_exceeds_threshold(Priority)) :-
    high_priority_threshold(Threshold),
    Priority >= Threshold.

%% "Time is outside peak hours"
compute_constraint(time_outside_peak_hours(StartMin)) :-
    peak_hours(start, PStartH, PStartM),
    peak_hours(end, PEndH, PEndM),
    time_to_minutes(PStartH, PStartM, PeakStart),
    time_to_minutes(PEndH, PEndM, PeakEnd),
    (StartMin < PeakStart ; StartMin > PeakEnd).

%% "Distance from nearest preferred window for a type"
compute_constraint(preferred_time_distance(Type, StartMin, Distance)) :-
    (   type_preferred_window(Type, WStartH, WStartM, WEndH, WEndM),
        time_to_minutes(WStartH, WStartM, WStart),
        time_to_minutes(WEndH, WEndM, WEnd),
        StartMin >= WStart,
        StartMin =< WEnd
    ->  Distance = 0
    ;   findall(D, (
            type_preferred_window(Type, WSH, WSM, _, _),
            time_to_minutes(WSH, WSM, WS),
            D is abs(StartMin - WS)
        ), Distances),
        Distances \= []
    ->  min_list(Distances, Distance)
    ;   Distance = 0
    ).

%% ============================================================================
%% Public API — Hard Constraint Validation (uses solver)
%% ============================================================================

%% validate_hard_constraints(+Event, +AllEvents, -Violations)
%% Returns a list of hard constraint violations. Empty list = valid.
validate_hard_constraints(
    event(Id, _Title, StartH, StartM, EndH, EndM, _Priority, _Type),
    AllEvents,
    Violations
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    findall(Violation, (
        % Check 1: Overlap with another event (via scheduler solver)
        (   member(event(OtherId, OtherTitle, OSH, OSM, OEH, OEM, _, _), AllEvents),
            OtherId \= Id,
            time_to_minutes(OSH, OSM, OStart),
            time_to_minutes(OEH, OEM, OEnd),
            solve(intervals_overlap(interval(StartMin, EndMin), interval(OStart, OEnd))),
            Violation = overlap(OtherId, OtherTitle)
        )
        ;
        % Check 2: Before working hours (via constraint solver)
        (   solve_constraint(before_working_hours(StartMin)),
            Violation = before_working_hours
        )
        ;
        % Check 3: After working hours (via constraint solver)
        (   solve_constraint(after_working_hours(EndMin)),
            Violation = after_working_hours
        )
        ;
        % Check 4: Invalid duration (via constraint solver)
        (   solve_constraint(invalid_event_duration(StartMin, EndMin)),
            Violation = invalid_duration
        )
    ), Violations).

%% ============================================================================
%% Soft Constraint Costs (uses solver + domain knowledge)
%% ============================================================================

%% calculate_soft_cost(+Event, +AllEvents, +Preferences, -TotalCost)
calculate_soft_cost(
    event(_Id, _Title, StartH, StartM, EndH, EndM, Priority, Type),
    AllEvents,
    _Preferences,
    TotalCost
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    preferred_time_cost(Type, StartMin, TimeCost),
    buffer_proximity_cost(StartMin, EndMin, AllEvents, BufferCost),
    daily_overload_cost(AllEvents, OverloadCost),
    priority_scheduling_cost(Priority, StartMin, PriorityCost),
    TotalCost is TimeCost + BufferCost + OverloadCost + PriorityCost.

%% Preferred time cost: uses solver to check preferred window
preferred_time_cost(Type, StartMin, Cost) :-
    (   solve_constraint(in_preferred_window(Type, StartMin))
    ->  Cost = 0
    ;   compute_constraint(preferred_time_distance(Type, StartMin, Distance)),
        Cost is min(Distance // 30, 10)
    ).

%% Buffer proximity cost: counts violations via solver
buffer_proximity_cost(StartMin, EndMin, AllEvents, Cost) :-
    compute_constraint(count_buffer_violations(StartMin, EndMin, AllEvents, NumClose)),
    proximity_penalty_per_event(PenaltyPerEvent),
    Cost is NumClose * PenaltyPerEvent.

%% Daily overload cost: uses domain knowledge thresholds
daily_overload_cost(AllEvents, Cost) :-
    length(AllEvents, NumEvents),
    daily_capacity(comfortable, ComfortThreshold),
    daily_capacity(heavy, HeavyThreshold),
    (   NumEvents > HeavyThreshold
    ->  overload_penalty(heavy, Penalty),
        Cost is (NumEvents - HeavyThreshold) * Penalty
    ;   NumEvents > ComfortThreshold
    ->  overload_penalty(comfortable, Penalty),
        Cost is (NumEvents - ComfortThreshold) * Penalty
    ;   Cost = 0
    ).

%% Priority scheduling cost: uses solver to detect suboptimal placement
priority_scheduling_cost(Priority, StartMin, Cost) :-
    (   solve_constraint(high_priority_at_suboptimal_time(Priority, StartMin))
    ->  high_priority_threshold(Threshold),
        priority_time_penalty_multiplier(Multiplier),
        Cost is (Priority - Threshold + 1) * Multiplier
    ;   Cost = 0
    ).

%% ============================================================================
%% g(n) — Displacement Cost (uses domain knowledge cost parameters)
%% ============================================================================

%% calculate_displacement_cost(+OriginalEvents, +ModifiedEvents, -GCost)
calculate_displacement_cost(OriginalEvents, ModifiedEvents, GCost) :-
    move_penalty(MovePen),
    shift_weight(ShiftW),
    priority_factor(PriFactor),
    findall(EventCost, (
        member(event(Id, _, OSH, OSM, OEH, OEM, Priority, _), OriginalEvents),
        member(event(Id, _, NSH, NSM, NEH, NEM, _, _), ModifiedEvents),
        time_to_minutes(OSH, OSM, OldStart),
        time_to_minutes(OEH, OEM, _OldEnd),
        time_to_minutes(NSH, NSM, NewStart),
        time_to_minutes(NEH, NEM, _NewEnd),
        (   OldStart =\= NewStart
        ->  Shift is abs(NewStart - OldStart),
            ShiftHours is Shift / 60.0,
            EventCost is MovePen + ShiftHours * ShiftW + Priority * PriFactor
        ;   EventCost = 0
        )
    ), Costs),
    sum_list(Costs, GCost).

%% ============================================================================
%% h(n) — Priority Loss Heuristic (uses strategy domain knowledge)
%% ============================================================================

%% calculate_priority_loss(+ConflictingEvents, +Strategy, +Priorities, -HCost)
calculate_priority_loss(ConflictingEvents, Strategy, _Priorities, HCost) :-
    strategy_weight(Strategy, StratWeight),
    findall(EventHCost, (
        member(event(_, _, _, _, _, _, Priority, _), ConflictingEvents),
        ConflictSeverity is Priority * Priority,
        EventHCost is ConflictSeverity * StratWeight
    ), HCosts),
    sum_list(HCosts, HCost).

%% ============================================================================
%% f(n) = g(n) + h(n) — Combined A* Evaluation
%% ============================================================================

calculate_heuristic(OriginalEvents, CurrentState, RemainingConflicts, Strategy, FScore) :-
    calculate_displacement_cost(OriginalEvents, CurrentState, GCost),
    calculate_priority_loss(RemainingConflicts, Strategy, [], HCost),
    FScore is GCost + HCost.

%% ============================================================================
%% Slot Finding with Priority Awareness (uses solver for overlap checks)
%% ============================================================================

%% find_best_slot(+EventToMove, +AllEvents, +MinSH, +MinSM, +MaxEH, +MaxEM, -BestSlot)
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
    exclude(event_has_id(Id), AllEvents, OtherEvents),
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
            \+ slot_conflicts_with_any(SlotStart, SlotEnd, OtherEvents),
            shift_weight(ShiftW),
            Displacement is abs(SlotStart - OrigStart),
            DisplacementCost is Displacement / 60.0 * ShiftW,
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

%% Helper: check if event has the given ID
event_has_id(Id, event(Id, _, _, _, _, _, _, _)).

%% Helper: slot conflicts with any extended event — uses scheduler solver
slot_conflicts_with_any(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM, _, _), Events),
    time_to_minutes(SH, SM, EStart),
    time_to_minutes(EH, EM, EEnd),
    solve(intervals_overlap(interval(Start, End), interval(EStart, EEnd))),
    !.

%% ============================================================================
%% A* Rescheduling (procedural, but uses solver for constraint checks)
%% ============================================================================

%% reschedule_event(+NewEvent, +ExistingEvents, +Strategy, +MinH, +MinM, +MaxH, +MaxM, -Result)
reschedule_event(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
    ExistingEvents,
    Strategy,
    MinH, MinM, MaxH, MaxM,
    Result
) :-
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    % Find conflicting events using solver
    findall(
        event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType),
        (
            member(event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType), ExistingEvents),
            time_to_minutes(ESH, ESM, ES),
            time_to_minutes(EEH, EEM, EE),
            solve(intervals_overlap(interval(NewStart, NewEnd), interval(ES, EE)))
        ),
        ConflictingEvents
    ),
    (   ConflictingEvents = []
    ->  Result = result(no_conflict, [], 0)
    ;
        NewEvent = event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
        % Option 1: Move the new event to a free slot
        (   find_best_slot(NewEvent, ExistingEvents, MinH, MinM, MaxH, MaxM, NewSlot)
        ->  NewSlot = slot(SlotSH, SlotSM, SlotEH, SlotEM, MoveCost1)
        ;   MoveCost1 = 9999, SlotSH = 0, SlotSM = 0, SlotEH = 0, SlotEM = 0
        ),
        priority_factor(PriFactor),
        Option1Cost is MoveCost1 + NewPriority * PriFactor,

        % Option 2: Keep new event, move conflicting events
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

        pick_best_option(
            Strategy, NewPriority,
            option(move_new, slot(SlotSH, SlotSM, SlotEH, SlotEM), Option1Cost),
            option(place_new, MovedEvents2, Option2Cost),
            Result
        )
    ).

%% Try to relocate all conflicting events to new slots
try_move_conflicts([], _AllEvents, _NewEvent, _MinH, _MinM, _MaxH, _MaxM, [], 0).
try_move_conflicts(
    [Event|Rest], AllEvents, NewEvent,
    MinH, MinM, MaxH, MaxM,
    [moved(Id, OSH, OSM, OEH, OEM, NSH2, NSM2, NEH2, NEM2, SlotCost)|RestMoved],
    TotalCost
) :-
    Event = event(Id, _Title, OSH, OSM, OEH, OEM, _Pri, _Type),
    exclude(event_has_id(Id), AllEvents, WithoutThis),
    append([NewEvent], WithoutThis, UpdatedEvents),
    find_best_slot(Event, UpdatedEvents, MinH, MinM, MaxH, MaxM, Slot),
    Slot = slot(NSH2, NSM2, NEH2, NEM2, SlotCost),
    try_move_conflicts(Rest, AllEvents, NewEvent, MinH, MinM, MaxH, MaxM, RestMoved, RestCost),
    TotalCost is SlotCost + RestCost.
try_move_conflicts(_, _, _, _, _, _, _, failed, 9999).

%% Pick best option — uses domain knowledge for strategy adjustments
pick_best_option(
    Strategy, NewPriority,
    option(move_new, Slot, Cost1),
    option(place_new, MovedEvents, Cost2),
    Result
) :-
    adjust_costs_by_strategy(Strategy, NewPriority, Cost1, Cost2, AdjCost1, AdjCost2),
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

%% Strategy adjustments via domain knowledge facts
adjust_costs_by_strategy(minimize_moves, _, Cost1, Cost2, AdjCost1, AdjCost2) :-
    strategy_adjustment(minimize_moves, move_new, Adj1),
    strategy_adjustment(minimize_moves, place_new, Adj2),
    AdjCost1 is Cost1 * Adj1,
    AdjCost2 is Cost2 * Adj2.
adjust_costs_by_strategy(maximize_quality, NewPriority, Cost1, Cost2, AdjCost1, AdjCost2) :-
    high_priority_threshold(Threshold),
    (   NewPriority >= Threshold
    ->  strategy_adjustment(maximize_quality, move_new_high_priority, Adj1),
        strategy_adjustment(maximize_quality, place_new_high_priority, Adj2)
    ;   strategy_adjustment(maximize_quality, move_new_low_priority, Adj1),
        strategy_adjustment(maximize_quality, place_new_low_priority, Adj2)
    ),
    AdjCost1 is Cost1 * Adj1,
    AdjCost2 is Cost2 * Adj2.
adjust_costs_by_strategy(balanced, _, Cost1, Cost2, Cost1, Cost2).
adjust_costs_by_strategy(_, _, Cost1, Cost2, Cost1, Cost2).

%% ============================================================================
%% Full A* Schedule Optimisation
%% ============================================================================

%% find_optimal_schedule(+Events, +NewEvent, +Strategy, +Bounds, +MaxDepth, -Solution)
find_optimal_schedule(Events, NewEvent, Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution) :-
    NewEvent = event(_, _, _, _, _, _, _, _),
    append([NewEvent], Events, InitialEvents),
    find_all_conflicts(InitialEvents, Conflicts),
    (   Conflicts = []
    ->  Solution = solution(InitialEvents, 0, [])
    ;   InitialState = state(InitialEvents, Events, 0, [], Conflicts),
        astar_search([InitialState], [], Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution)
    ).

%% Find all pairs of overlapping events — uses scheduler solver
find_all_conflicts(Events, ConflictPairs) :-
    findall(
        conflict(Id1, Id2),
        (
            member(event(Id1, _, S1H, S1M, E1H, E1M, _, _), Events),
            member(event(Id2, _, S2H, S2M, E2H, E2M, _, _), Events),
            Id1 @< Id2,
            time_to_minutes(S1H, S1M, S1),
            time_to_minutes(E1H, E1M, E1),
            time_to_minutes(S2H, S2M, S2),
            time_to_minutes(E2H, E2M, E2),
            solve(intervals_overlap(interval(S1, E1), interval(S2, E2)))
        ),
        ConflictPairs
    ).

%% A* search implementation
astar_search([], _Closed, _Strategy, _Bounds, _MaxDepth,
    solution([], 9999, [no_solution])) :- !.

astar_search(Open, _Closed, _Strategy, _Bounds, 0,
    solution(BestEvents, BestCost, BestMoves)) :-
    sort_states_by_cost(Open, [state(BestEvents, _, BestCost, BestMoves, _)|_]), !.

astar_search(Open, Closed, Strategy, Bounds, MaxDepth, Solution) :-
    sort_states_by_cost(Open, [Current|RestOpen]),
    Current = state(Events, OrigEvents, CurrentCost, Moves, Conflicts),
    (   Conflicts = []
    ->  Solution = solution(Events, CurrentCost, Moves)
    ;
        Bounds = bounds(MinH, MinM, MaxH, MaxM),
        NewDepth is MaxDepth - 1,
        findall(NextState, (
            member(conflict(Id1, Id2), Conflicts),
            ( MovedId = Id1 ; MovedId = Id2 ),
            member(MovedEvent, Events),
            MovedEvent = event(MovedId, _, _, _, _, _, _, _),
            find_best_slot(MovedEvent, Events, MinH, MinM, MaxH, MaxM, FoundSlot),
            FoundSlot = slot(NSH, NSM, NEH, NEM, SlotCost),
            replace_event_time(Events, MovedId, NSH, NSM, NEH, NEM, NewEvents),
            NewCost is CurrentCost + SlotCost,
            find_all_conflicts(NewEvents, NewConflicts),
            NewMoves = [move(MovedId, NSH, NSM, NEH, NEM)|Moves],
            NextState = state(NewEvents, OrigEvents, NewCost, NewMoves, NewConflicts),
            \+ member(NextState, Closed)
        ), NewStates),
        append(RestOpen, NewStates, AllOpen),
        astar_search(AllOpen, [Current|Closed], Strategy, Bounds, NewDepth, Solution)
    ).

sort_states_by_cost(States, Sorted) :-
    map_list_to_pairs(state_cost, States, Pairs),
    keysort(Pairs, SortedPairs),
    pairs_values(SortedPairs, Sorted).

state_cost(state(_, _, Cost, _, _), Cost).

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
%% Chain Conflict Detection — uses solver
%% ============================================================================

%% detect_chain_conflicts(+MovedId, +NewSH, +NewSM, +NewEH, +NewEM, +AllEvents, -Chains)
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
            solve(intervals_overlap(interval(NewStart, NewEnd), interval(CStart, CEnd)))
        ),
        ChainConflicts
    ).

%% ============================================================================
%% User-Facing Suggestions
%% ============================================================================

%% suggest_reschedule_options(+NewEvent, +ExistingEvents, +Strategy,
%%     +MinH, +MinM, +MaxH, +MaxM, -Options)
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
    % Find conflicts using solver
    findall(
        event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType),
        (
            member(event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType), ExistingEvents),
            time_to_minutes(ESH, ESM, ES),
            time_to_minutes(EEH, EEM, EE),
            solve(intervals_overlap(interval(NewStart, NewEnd), interval(ES, EE)))
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
                priority_factor(PriFactor),
                TotalCost is SlotCost + CPri * PriFactor,
                MovedList = [moved(CId, CSH, CSM, CEH, CEM)],
                format(atom(Description), 'Move "~w" to ~w:~w-~w:~w (priority: ~w)',
                    [CTitle, CSH, CSM, CEH, CEM, CPri])
            ),
            OptionBs
        ),
        append(OptionAs, OptionBs, AllOptions),
        sort_options(AllOptions, SortedOptions),
        take_n(3, SortedOptions, Options)
    ).

%% Find free slots near the original time — uses solver for overlap check
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
    shift_weight(ShiftW),
    Displacement is abs(SlotStart - OrigStart),
    Score is Displacement / 60.0 * ShiftW,
    minutes_to_time(SlotStart, SH, SM),
    minutes_to_time(SlotEnd, EH, EM).

sort_options(Options, Sorted) :-
    map_list_to_pairs(option_cost, Options, Pairs),
    keysort(Pairs, SortedPairs),
    pairs_values(SortedPairs, Sorted).

option_cost(option(_, _, Cost, _), Cost).

take_n(_, [], []) :- !.
take_n(0, _, []) :- !.
take_n(N, [H|T], [H|Rest]) :-
    N > 0,
    N1 is N - 1,
    take_n(N1, T, Rest).

%% ============================================================================
%% Utility
%% ============================================================================
sum_list([], 0).
sum_list([H|T], Sum) :-
    sum_list(T, RestSum),
    Sum is H + RestSum.
