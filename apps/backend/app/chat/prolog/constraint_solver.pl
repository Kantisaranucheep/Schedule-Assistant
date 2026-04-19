%% apps/backend/app/chat/prolog/constraint_solver.pl
%% ============================================================================
%% Enhanced Constraint Solver with KRR and Priority-Based A* Rescheduling
%% ============================================================================
%%
%% This module implements Knowledge Representation and Reasoning for
%% constraint-based schedule optimization. It is organized into:
%%
%%   1. Constraint Knowledge Base — hard/soft constraints as FACTS
%%   2. Constraint Reasoning     — inference over constraint declarations
%%   3. Priority Knowledge       — event priority as domain knowledge
%%   4. Cost Reasoning           — g(n), h(n), f(n) as inferred properties
%%   5. Meta-Reasoning           — reason about which constraints to apply
%%   6. Optimization Engine      — A* search (uses reasoning layer)
%%   7. Legacy Predicates        — backward-compatible exports
%%
%% KRR Principles Applied:
%%   - Constraints are DECLARED as facts, not embedded in code
%%   - Priority is KNOWLEDGE, not a computed parameter
%%   - The meta-reasoner selects which rules/constraints apply
%%   - The optimizer QUERIES the knowledge base, not procedural checks
%% ============================================================================

:- module(constraint_solver, [
    %% --- Legacy exports (backward compatible) ---
    validate_hard_constraints/3,
    calculate_soft_cost/4,
    calculate_displacement_cost/3,
    calculate_priority_loss/4,
    calculate_heuristic/5,
    find_best_slot/7,
    reschedule_event/8,
    find_optimal_schedule/6,
    detect_chain_conflicts/4,
    suggest_reschedule_options/7,

    %% --- KRR Exports ---
    hard_constraint/1,             % hard_constraint(Name) — declared fact
    soft_constraint/2,             % soft_constraint(Name, Weight) — declared fact
    constraint_satisfied/3,        % constraint_satisfied(Name, Event, Context) — inference
    all_hard_constraints_met/2,    % all_hard_constraints_met(Event, Context) — inference
    soft_cost_for/4,               % soft_cost_for(Name, Event, Context, Cost) — inference
    total_soft_cost/4,             % total_soft_cost(Event, Context, Prefs, Cost) — inference
    priority_knowledge/2,          % priority_knowledge(Level, Weight) — fact
    event_priority_class/3,        % event_priority_class(Priority, Class, Description) — fact
    reason_about_constraint/3,     % reason_about_constraint(Event, Context, Verdict) — meta
    demo/1                         % demo(Goal) — meta-interpreter
]).

:- use_module(scheduler, [
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3
]).

%% ============================================================================
%% 1. Constraint Knowledge Base — Declared as Facts
%% ============================================================================
%%
%% Hard constraints MUST be satisfied; soft constraints SHOULD be minimized.
%% Each is a FACT in the knowledge base, not embedded logic.

:- dynamic hard_constraint/1.
:- dynamic soft_constraint/2.

%% --- Hard Constraints (must hold, no exceptions) ---
hard_constraint(no_time_overlap).
hard_constraint(within_working_hours).
hard_constraint(positive_duration).

%% --- Soft Constraints (preferences, with penalty weights) ---
soft_constraint(preferred_time_window, 5).    % Penalty for suboptimal time
soft_constraint(buffer_proximity, 3).         % Penalty for insufficient buffer
soft_constraint(daily_overload, 4).           % Penalty for too many events
soft_constraint(priority_scheduling, 2).      % Penalty for priority mismatch

%% ============================================================================
%% 2. Priority Knowledge — Domain Expertise as Facts
%% ============================================================================

%% Priority levels and their numeric weights (domain knowledge)
priority_knowledge(critical, 10).
priority_knowledge(high, 8).
priority_knowledge(medium, 5).
priority_knowledge(low, 3).
priority_knowledge(optional, 1).

%% Classification rules: what priority level means
event_priority_class(P, critical, 'Must not be moved or displaced') :- P >= 9.
event_priority_class(P, high, 'Prefer not to move; high displacement cost') :- P >= 7, P < 9.
event_priority_class(P, medium, 'Can be moved with moderate cost') :- P >= 4, P < 7.
event_priority_class(P, low, 'Easy to move; minimal cost') :- P >= 2, P < 4.
event_priority_class(P, optional, 'Can be freely rescheduled') :- P < 2.

%% Strategy weights (how much to weigh priority loss by strategy)
scheduling_fact(strategy_weight(minimize_moves, 0.5)).
scheduling_fact(strategy_weight(maximize_quality, 2.0)).
scheduling_fact(strategy_weight(balanced, 1.0)).

%% Strategy classification rules
strategy_preference(minimize_moves, move_count, high).
strategy_preference(maximize_quality, event_quality, high).

%% ============================================================================
%% 3. Constraint Reasoning — Inference Over Declarations
%% ============================================================================
%%
%% constraint_satisfied(+ConstraintName, +Event, +Context)
%% Infers whether a named constraint holds for an event in a context.
%% The event and context are passed as structured terms.

%% Hard constraint: no overlap with other events
constraint_satisfied(no_time_overlap,
    event(Id, _Title, StartH, StartM, EndH, EndM, _Priority, _Type),
    context(AllEvents)
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    \+ (
        member(event(OtherId, _, OSH, OSM, OEH, OEM, _, _), AllEvents),
        OtherId \= Id,
        time_to_minutes(OSH, OSM, OStart),
        time_to_minutes(OEH, OEM, OEnd),
        OStart < EndMin,
        StartMin < OEnd
    ).

%% Hard constraint: within working hours (6:00–23:00)
constraint_satisfied(within_working_hours,
    event(_Id, _Title, StartH, StartM, EndH, EndM, _Priority, _Type),
    _Context
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    StartMin >= 360,   % >= 6:00 AM
    EndMin =< 1380.    % <= 23:00

%% Hard constraint: positive duration
constraint_satisfied(positive_duration,
    event(_Id, _Title, StartH, StartM, EndH, EndM, _Priority, _Type),
    _Context
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    EndMin > StartMin.

%% all_hard_constraints_met(+Event, +Context)
%% Inference: ALL declared hard constraints must be satisfied.
all_hard_constraints_met(Event, Context) :-
    forall(
        hard_constraint(C),
        constraint_satisfied(C, Event, Context)
    ).

%% ============================================================================
%% 4. Soft Cost Reasoning — Infer Penalty from Knowledge
%% ============================================================================

%% soft_cost_for(+ConstraintName, +Event, +Context, -Cost)
%% Infer the penalty cost for violating a named soft constraint.

soft_cost_for(preferred_time_window,
    event(_Id, _Title, StartH, StartM, _EndH, _EndM, _Priority, Type),
    _Context, Cost
) :-
    time_to_minutes(StartH, StartM, StartMin),
    preferred_time_cost_for_type(Type, StartMin, Cost).

soft_cost_for(buffer_proximity,
    event(_Id, _Title, StartH, StartM, EndH, EndM, _Priority, _Type),
    context(AllEvents), Cost
) :-
    time_to_minutes(StartH, StartM, StartMin),
    time_to_minutes(EndH, EndM, EndMin),
    buffer_proximity_cost(StartMin, EndMin, AllEvents, Cost).

soft_cost_for(daily_overload, _Event, context(AllEvents), Cost) :-
    daily_overload_cost(AllEvents, Cost).

soft_cost_for(priority_scheduling,
    event(_Id, _Title, StartH, StartM, _EndH, _EndM, Priority, _Type),
    _Context, Cost
) :-
    time_to_minutes(StartH, StartM, StartMin),
    priority_scheduling_cost(Priority, StartMin, Cost).

%% total_soft_cost(+Event, +Context, +Preferences, -TotalCost)
%% Sum of all soft constraint penalties, weighted by declaration.
total_soft_cost(Event, Context, _Preferences, TotalCost) :-
    findall(
        WeightedCost,
        (
            soft_constraint(Name, Weight),
            soft_cost_for(Name, Event, Context, RawCost),
            WeightedCost is RawCost * Weight / 5  % normalize by default weight
        ),
        Costs
    ),
    sum_list(Costs, TotalCost).

%% ============================================================================
%% 5. Meta-Reasoning — Reason About Constraint Application
%% ============================================================================
%%
%% reason_about_constraint(+Event, +Context, -Verdict)
%% The meta-reasoner examines all constraints and produces a verdict:
%%   verdict(HardViolations, SoftCost, Recommendation)

reason_about_constraint(Event, Context, verdict(HardViolations, SoftCost, Recommendation)) :-
    %% Check which hard constraints are violated
    findall(
        violated(C),
        (hard_constraint(C), \+ constraint_satisfied(C, Event, Context)),
        HardViolations
    ),
    %% Calculate total soft cost
    total_soft_cost(Event, Context, [], SoftCost),
    %% Infer recommendation
    (   HardViolations = []
    ->  (   SoftCost < 5
        ->  Recommendation = accept
        ;   Recommendation = accept_with_warning
        )
    ;   Recommendation = reject
    ).

%% demo/1: Meta-interpreter for constraint reasoning
demo(true) :- !.
demo((A, B)) :- !, demo(A), demo(B).
demo((A ; B)) :- !, (demo(A) ; demo(B)).
demo(\+ A) :- !, \+ demo(A).

demo(constraint_satisfied(C, E, Ctx)) :- constraint_satisfied(C, E, Ctx).
demo(all_hard_constraints_met(E, Ctx)) :- all_hard_constraints_met(E, Ctx).
demo(reason_about_constraint(E, Ctx, V)) :- reason_about_constraint(E, Ctx, V).
demo(hard_constraint(C)) :- hard_constraint(C).
demo(soft_constraint(C, W)) :- soft_constraint(C, W).
demo(priority_knowledge(L, W)) :- priority_knowledge(L, W).
demo(event_priority_class(P, C, D)) :- event_priority_class(P, C, D).

%% ============================================================================
%% 6. Legacy Predicates (Backward Compatible)
%% ============================================================================
%%
%% These preserve the original API. They now delegate to the KRR layer
%% for constraint checking where applicable.

%% validate_hard_constraints — now uses constraint_satisfied inference
validate_hard_constraints(
    event(Id, _Title, StartH, StartM, EndH, EndM, _Priority, _Type),
    AllEvents,
    Violations
) :-
    Event = event(Id, _Title, StartH, StartM, EndH, EndM, _Priority, _Type),
    Context = context(AllEvents),
    findall(Violation, (
        %% Check each hard constraint via inference
        (   hard_constraint(no_time_overlap),
            \+ constraint_satisfied(no_time_overlap, Event, Context),
            member(event(OtherId, OtherTitle, OSH, OSM, OEH, OEM, _, _), AllEvents),
            OtherId \= Id,
            time_to_minutes(OSH, OSM, OStart),
            time_to_minutes(OEH, OEM, OEnd),
            time_to_minutes(StartH, StartM, StartMin),
            time_to_minutes(EndH, EndM, EndMin),
            OStart < EndMin,
            StartMin < OEnd,
            Violation = overlap(OtherId, OtherTitle)
        )
        ;
        (   \+ constraint_satisfied(within_working_hours, Event, Context),
            time_to_minutes(StartH, StartM, SM),
            SM < 360,
            Violation = before_working_hours
        )
        ;
        (   \+ constraint_satisfied(within_working_hours, Event, Context),
            time_to_minutes(EndH, EndM, EM2),
            EM2 > 1380,
            Violation = after_working_hours
        )
        ;
        (   \+ constraint_satisfied(positive_duration, Event, Context),
            Violation = invalid_duration
        )
    ), Violations).

%% calculate_soft_cost — now delegates to total_soft_cost inference
calculate_soft_cost(
    event(Id, Title, StartH, StartM, EndH, EndM, Priority, Type),
    AllEvents,
    Preferences,
    TotalCost
) :-
    Event = event(Id, Title, StartH, StartM, EndH, EndM, Priority, Type),
    Context = context(AllEvents),
    total_soft_cost(Event, Context, Preferences, TotalCost).

%% Preferred time cost per event type (knowledge)
preferred_time_cost_for_type(meeting, StartMin, Cost) :-
    (   StartMin >= 540, StartMin =< 1020
    ->  Cost = 0
    ;   Diff is abs(StartMin - 540),
        Cost is min(Diff // 30, 10)
    ).
preferred_time_cost_for_type(study, StartMin, Cost) :-
    (   (StartMin >= 480, StartMin =< 720)
    ;   (StartMin >= 840, StartMin =< 1080)
    ->  Cost = 0
    ;   Cost = 5
    ).
preferred_time_cost_for_type(exercise, StartMin, Cost) :-
    (   StartMin =< 480
    ;   StartMin >= 1020
    ->  Cost = 0
    ;   Cost = 3
    ).
preferred_time_cost_for_type(_, _, 0).

%% Buffer proximity cost
buffer_proximity_cost(StartMin, EndMin, AllEvents, Cost) :-
    findall(1, (
        member(event(_, _, OSH, OSM, OEH, OEM, _, _), AllEvents),
        time_to_minutes(OSH, OSM, OStart),
        time_to_minutes(OEH, OEM, OEnd),
        (   (OEnd > StartMin - 15, OEnd =< StartMin)
        ;   (OStart >= EndMin, OStart < EndMin + 15)
        )
    ), CloseEvents),
    length(CloseEvents, NumClose),
    Cost is NumClose * 3.

%% Daily overload cost
daily_overload_cost(AllEvents, Cost) :-
    length(AllEvents, NumEvents),
    (   NumEvents > 8
    ->  Cost is (NumEvents - 8) * 5
    ;   NumEvents > 6
    ->  Cost is (NumEvents - 6) * 2
    ;   Cost = 0
    ).

%% Priority scheduling cost
priority_scheduling_cost(Priority, StartMin, Cost) :-
    Priority >= 8,
    (   StartMin >= 540, StartMin =< 1020
    ->  Cost = 0
    ;   Cost is (Priority - 7) * 3
    ),
    !.
priority_scheduling_cost(_, _, 0).

%% ============================================================================
%% g(n) — DISPLACEMENT COST (Actual cost of moves made)
%% ============================================================================

calculate_displacement_cost(OriginalEvents, ModifiedEvents, GCost) :-
    findall(EventCost, (
        member(event(Id, _, OSH, OSM, OEH, OEM, Priority, _), OriginalEvents),
        member(event(Id, _, NSH, NSM, NEH, NEM, _, _), ModifiedEvents),
        time_to_minutes(OSH, OSM, OldStart),
        time_to_minutes(OEH, OEM, OldEnd),
        time_to_minutes(NSH, NSM, NewStart),
        time_to_minutes(NEH, NEM, NewEnd),
        (   (OldStart =\= NewStart ; OldEnd =\= NewEnd)
        ->  Shift is abs(NewStart - OldStart),
            ShiftHours is Shift / 60.0,
            MovePenalty = 3,
            ShiftCost is ShiftHours * 2,
            PriorityPenalty is Priority * 0.5,
            EventCost is MovePenalty + ShiftCost + PriorityPenalty
        ;   EventCost = 0
        )
    ), Costs),
    sum_list(Costs, GCost).

%% ============================================================================
%% h(n) — PRIORITY LOSS HEURISTIC
%% ============================================================================

calculate_priority_loss(ConflictingEvents, Strategy, _Priorities, HCost) :-
    scheduling_fact(strategy_weight(Strategy, StratWeight)),
    findall(EventHCost, (
        member(event(_Id, _Title, _SH, _SM, _EH, _EM, Priority, _Type), ConflictingEvents),
        infer_conflict_severity(Priority, Strategy, Severity),
        EventHCost is Severity * StratWeight
    ), HCosts),
    sum_list(HCosts, HCost).

%% infer_conflict_severity/3: Reason about how "bad" a conflict is based on priority and strategy
infer_conflict_severity(Priority, _Strategy, Severity) :-
    Severity is Priority * Priority.

%% ============================================================================
%% f(n) = g(n) + h(n) — COMBINED HEURISTIC
%% ============================================================================

calculate_heuristic(OriginalEvents, CurrentState, RemainingConflicts, Strategy, FScore) :-
    calculate_displacement_cost(OriginalEvents, CurrentState, GCost),
    calculate_priority_loss(RemainingConflicts, Strategy, [], HCost),
    FScore is GCost + HCost.

%% ============================================================================
%% SLOT FINDING with Priority Awareness
%% ============================================================================

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
            Displacement is abs(SlotStart - OrigStart),
            DisplacementCost is Displacement / 60.0 * 2,
            minutes_to_time(SlotStart, SlotSH, SlotSM),
            minutes_to_time(SlotEnd, SlotEH, SlotEM),
            %% Use KRR soft cost inference
            CandidateEvent = event(Id, Title, SlotSH, SlotSM, SlotEH, SlotEM, Priority, Type),
            total_soft_cost(CandidateEvent, context(OtherEvents), [], SoftCost),
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

reschedule_event(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
    ExistingEvents,
    Strategy,
    MinH, MinM, MaxH, MaxM,
    Result
) :-
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
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
    ->  Result = result(no_conflict, [], 0)
    ;
        NewEvent = event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
        (   find_best_slot(NewEvent, ExistingEvents, MinH, MinM, MaxH, MaxM, NewSlot)
        ->  NewSlot = slot(SlotSH, SlotSM, SlotEH, SlotEM, MoveCost1)
        ;   MoveCost1 = 9999, SlotSH = 0, SlotSM = 0, SlotEH = 0, SlotEM = 0
        ),
        Option1Cost is MoveCost1 + NewPriority * 0.5,

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

pick_best_option(
    Strategy, NewPriority,
    option(move_new, Slot, Cost1),
    option(place_new, MovedEvents, Cost2),
    Result
) :-
    (   Strategy = minimize_moves
    ->  AdjCost1 is Cost1 * 0.7,
        AdjCost2 is Cost2 * 1.3
    ;   Strategy = maximize_quality
    ->  (   NewPriority >= 8
        ->  AdjCost1 is Cost1 * 2.0,
            AdjCost2 is Cost2 * 0.5
        ;   AdjCost1 is Cost1 * 0.5,
            AdjCost2 is Cost2 * 1.5
        )
    ;   AdjCost1 is Cost1,
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

find_optimal_schedule(Events, NewEvent, Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution) :-
    NewEvent = event(_, _, _, _, _, _, _, _),
    append([NewEvent], Events, InitialEvents),
    find_all_conflicts(InitialEvents, Conflicts),
    (   Conflicts = []
    ->  Solution = solution(InitialEvents, 0, [])
    ;   InitialState = state(InitialEvents, Events, 0, [], Conflicts),
        astar_search([InitialState], [], Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution)
    ).

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
            S1 < E2,
            S2 < E1
        ),
        ConflictPairs
    ).

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
            (   MovedId = Id1 ; MovedId = Id2 ),
            member(MovedEvent, Events),
            MovedEvent = event(MovedId, _, _, _, _, _, _, _),
            find_best_slot(MovedEvent, Events, MinH, MinM, MaxH, MaxM, Slot),
            Slot = slot(NSH, NSM, NEH, NEM, SlotCost),
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
%% CHAIN CONFLICT DETECTION
%% ============================================================================

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
        findall(
            option(move_new, [moved_to(SH, SM, EH, EM)], Score, Description),
            (
                find_near_slot(NewStart, Duration, ExistingEvents, MinH, MinM, MaxH, MaxM, SH, SM, EH, EM, Score),
                format(atom(Description), 'Move "~w" to ~w:~w-~w:~w', [NewTitle, SH, SM, EH, EM])
            ),
            OptionAs
        ),

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

        append(OptionAs, OptionBs, AllOptions),
        sort_options(AllOptions, SortedOptions),
        take_n(3, SortedOptions, Options)
    ).

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
%% UTILITY: Sum a list of numbers
%% ============================================================================
sum_list([], 0).
sum_list([H|T], Sum) :-
    sum_list(T, RestSum),
    Sum is H + RestSum.
