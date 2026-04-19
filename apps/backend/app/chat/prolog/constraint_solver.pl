%% apps/backend/app/chat/prolog/constraint_solver.pl
%% ============================================================================
%% Constraint Solver — Knowledge-Based Reasoning with Priority Scheduling
%% ============================================================================
%%
%% Architecture (Knowledge Representation & Reasoning):
%%
%%   Layer 1 — FACTS (Knowledge Base)
%%       Domain constants: working-hour boundaries, buffer thresholds,
%%       strategy weights, preference windows, cost parameters.
%%       All tunable knowledge is declared as facts, not buried in code.
%%
%%   Layer 2 — RULES (Inference Rules)
%%       Declarative rules that derive constraint violations, costs,
%%       and scheduling judgments from facts and event data.
%%
%%   Layer 3 — CONSTRAINTS (Hard & Soft, first-class objects)
%%       Named constraint objects with check_hard/2 and evaluate_soft/3.
%%       Hard constraints are binary (pass/fail); soft constraints
%%       return a numeric penalty cost.
%%
%%   Layer 4 — META-INTERPRETER (demo/1)
%%       Extends schedulers meta-interpreter with constraint-specific
%%       reasoning.  Allows queries like:
%%         ?- demo(hard_constraint_holds(no_overlap, Event, AllEvents)).
%%
%%   Layer 5 — SOLVER (solve/2 — Central Reasoning Entry Point)
%%       All high-level queries route through solve/2, which selects
%%       the applicable reasoning strategy (validation, cost calculation,
%%       rescheduling, A* search).
%%
%% Design principles:
%%   • Hard constraints are strictly boolean — they MUST hold.
%%   • Soft constraints yield penalty costs — the solver MINIMIZES them.
%%   • The A* search is expressed as state-space reasoning over schedule states.
%%   • Strategy selection is fact-driven (strategy_weight/2), not hard-coded.
%%   • Python calls the same exported predicates; the solver routes internally.
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
    detect_chain_conflicts/4,
    suggest_reschedule_options/7,
    %% --- New KRR-aware predicates ---
    solve/2,
    demo/1,
    check_hard/2,
    evaluate_soft/3
]).

:- use_module(scheduler, [
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3
]).

%% ============================================================================
%% LAYER 0 — CUSTOM OPERATORS
%% ============================================================================

:- op(700, xfx, violates).
:- op(700, xfx, satisfies).
:- op(700, xfx, penalized_by).

%% ============================================================================
%% LAYER 1 — FACTS  (Knowledge Base)
%% ============================================================================
%% Pure ground knowledge. Every tunable parameter is a fact, making the
%% systems assumptions explicit, inspectable, and modifiable.

%% --- Working-hour boundaries (minutes from midnight) ---
fact(working_hours_start, 360).    %% 6:00 AM
fact(working_hours_end,   1380).   %% 11:00 PM

%% --- Buffer requirements ---
fact(min_buffer_minutes, 15).      %% Minimum gap between events

%% --- Daily overload thresholds ---
fact(daily_soft_limit, 6).         %% Penalty starts here
fact(daily_hard_limit, 8).         %% Higher penalty above this

%% --- Slot search parameters ---
fact(slot_step, 30).               %% Candidate slot granularity (minutes)
fact(max_slot_candidates, 100).    %% Safety bound on search iterations
fact(max_reschedule_options, 3).   %% Max options returned to user

%% --- Displacement cost parameters ---
fact(move_penalty,    3).          %% Fixed cost per moved event
fact(shift_weight,    2).          %% Cost per hour of displacement
fact(priority_factor, 0.5).        %% Priority multiplier on displacement

%% --- Strategy weights (how much to weigh priority loss) ---
strategy_weight(minimize_moves,  0.5).   %% Prefer fewer moves
strategy_weight(maximize_quality, 2.0).  %% Protect high-priority events
strategy_weight(balanced,         1.0).  %% Equal balance

%% --- Preferred time windows (Type → ideal start range in minutes) ---
%% preferred_window(EventType, EarliestStart, LatestStart)
preferred_window(meeting,  540, 1020).   %% 9:00–17:00
preferred_window(study,    480,  720).   %% 8:00–12:00  (primary)
preferred_window(study,    840, 1080).   %% 14:00–18:00 (secondary)
preferred_window(exercise, 360,  480).   %% 6:00–8:00   (morning)
preferred_window(exercise, 1020, 1380).  %% 17:00–23:00 (evening)

%% --- Preference violation penalties ---
preference_penalty(meeting,  10).   %% Max penalty for off-window meeting
preference_penalty(study,     5).
preference_penalty(exercise,  3).

%% --- Metadata: self-describing knowledge ---
statement(no_overlap,        hard_constraint, 'Event must not overlap other events').
statement(within_work_hours, hard_constraint, 'Event must be within working hours').
statement(positive_duration, hard_constraint, 'End time must be after start time').
statement(preferred_time,    soft_constraint, 'Events should be in their preferred window').
statement(buffer_proximity,  soft_constraint, 'Events should have buffer gaps between them').
statement(daily_overload,    soft_constraint, 'Avoid too many events in one day').
statement(priority_schedule, soft_constraint, 'High-priority events belong in peak hours').

%% --- Rule metadata ---
rule(displacement_cost_rule,
     calculate_displacement_cost(_Orig, _Mod, _Cost),
     'g(n): actual cost of moving events from original positions').
rule(priority_loss_rule,
     calculate_priority_loss(_Conflicts, _Strategy, _Priorities, _Cost),
     'h(n): estimated future cost of unresolved conflicts').
rule(heuristic_rule,
     calculate_heuristic(_Orig, _Curr, _Rem, _Strat, _F),
     'f(n) = g(n) + h(n): A* evaluation function').

%% ============================================================================
%% LAYER 2 — RULES  (Inference Rules)
%% ============================================================================
%% Declarative rules that derive violations, costs, and judgments.

%% --- Hard constraint violation rules ---
%% Rule: An event violates no_overlap when it overlaps another event.
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

%% Rule: An event violates within_work_hours when it starts before working hours.
violation(before_working_hours, event(_Id, _T, SH, SM, _EH, _EM, _P, _Ty), _AllEvents,
          before_working_hours) :-
    time_to_minutes(SH, SM, Start),
    fact(working_hours_start, WorkStart),
    Start < WorkStart.

%% Rule: An event violates within_work_hours when it ends after working hours.
violation(after_working_hours, event(_Id, _T, _SH, _SM, EH, EM, _P, _Ty), _AllEvents,
          after_working_hours) :-
    time_to_minutes(EH, EM, End),
    fact(working_hours_end, WorkEnd),
    End > WorkEnd.

%% Rule: An event violates positive_duration when end <= start.
violation(positive_duration, event(_Id, _T, SH, SM, EH, EM, _P, _Ty), _AllEvents,
          invalid_duration) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    End =< Start.

%% --- Soft cost rules ---

%% Rule: preferred_time cost — penalty for scheduling outside preferred window.
soft_cost(preferred_time, event(_Id, _T, SH, SM, _EH, _EM, _P, Type), _AllEvents, _Prefs, Cost) :-
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

%% Rule: buffer_proximity cost — penalty when events are too close.
soft_cost(buffer_proximity, event(_Id, _T, SH, SM, EH, EM, _P, _Ty), AllEvents, _Prefs, Cost) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    fact(min_buffer_minutes, Buffer),
    findall(1, (
        member(event(_, _, OSH, OSM, OEH, OEM, _, _), AllEvents),
        time_to_minutes(OSH, OSM, OStart),
        time_to_minutes(OEH, OEM, OEnd),
        (   (OEnd > Start - Buffer, OEnd =< Start)
        ;   (OStart >= End, OStart < End + Buffer)
        )
    ), CloseEvents),
    length(CloseEvents, NumClose),
    Cost is NumClose * 3.

%% Rule: daily_overload cost — penalty for too many events.
soft_cost(daily_overload, _Event, AllEvents, _Prefs, Cost) :-
    length(AllEvents, N),
    fact(daily_hard_limit, HardLim),
    fact(daily_soft_limit, SoftLim),
    (   N > HardLim -> Cost is (N - HardLim) * 5
    ;   N > SoftLim -> Cost is (N - SoftLim) * 2
    ;   Cost = 0
    ).

%% Rule: priority_schedule cost — high-priority off peak-hours penalty.
soft_cost(priority_schedule, event(_Id, _T, SH, SM, _EH, _EM, Priority, _Ty), _AllEvents, _Prefs, Cost) :-
    (   Priority >= 8
    ->  time_to_minutes(SH, SM, Start),
        (   Start >= 540, Start =< 1020
        ->  Cost = 0
        ;   Cost is (Priority - 7) * 3
        )
    ;   Cost = 0
    ).

%% --- Displacement cost rule: g(n) ---
%% Rule: Each moved event incurs: move_penalty + shift_hours * shift_weight + priority * factor
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

%% --- Priority loss rule: h(n) ---
%% Rule: Each unresolved conflict contributes priority² × strategy_weight.
event_priority_loss(event(_Id, _T, _SH, _SM, _EH, _EM, Priority, _Ty), Strategy, Loss) :-
    strategy_weight(Strategy, W),
    Loss is Priority * Priority * W.

%% ============================================================================
%% LAYER 3 — CONSTRAINTS  (First-Class Constraint Objects)
%% ============================================================================
%% Hard constraints are binary: they either hold or produce a violation.
%% Soft constraints produce a penalty cost (0 = fully satisfied).

%% --- Hard constraint checker ---
%% check_hard(+ConstraintName, +Args)
%% Succeeds iff the hard constraint is NOT violated.
check_hard(no_overlap, [Event, AllEvents]) :-
    \+ violation(no_overlap, Event, AllEvents, _).

check_hard(before_working_hours, [Event]) :-
    \+ violation(before_working_hours, Event, [], _).

check_hard(after_working_hours, [Event]) :-
    \+ violation(after_working_hours, Event, [], _).

check_hard(positive_duration, [Event]) :-
    \+ violation(positive_duration, Event, [], _).

%% --- Soft constraint evaluator ---
%% evaluate_soft(+ConstraintName, +Args, -Cost)
evaluate_soft(preferred_time, [Event, AllEvents, Prefs], Cost) :-
    soft_cost(preferred_time, Event, AllEvents, Prefs, Cost).

evaluate_soft(buffer_proximity, [Event, AllEvents, _Prefs], Cost) :-
    soft_cost(buffer_proximity, Event, AllEvents, _, Cost).

evaluate_soft(daily_overload, [_Event, AllEvents, _Prefs], Cost) :-
    soft_cost(daily_overload, _, AllEvents, _, Cost).

evaluate_soft(priority_schedule, [Event, _AllEvents, _Prefs], Cost) :-
    soft_cost(priority_schedule, Event, _, _, Cost).

%% --- Operator-based constraint checking ---
%% Event satisfies ConstraintName  iff the hard constraint holds.
Event satisfies ConstraintName :-
    check_hard(ConstraintName, [Event, []]).

%% Event violates ConstraintName  iff a violation exists.
Event violates ConstraintName :-
    violation(ConstraintName, Event, [], _).

%% Event penalized_by soft(Name, Cost) iff the soft constraint yields Cost.
Event penalized_by soft(Name, Cost) :-
    evaluate_soft(Name, [Event, [], []], Cost),
    Cost > 0.

%% ============================================================================
%% LAYER 4 — META-INTERPRETER  (demo/1)
%% ============================================================================
%% Extends reasoning to constraint-specific queries.

%% Base cases.
demo(true).
demo((A, B)) :- demo(A), demo(B).
demo((A ; _)) :- demo(A).
demo((_ ; B)) :- demo(B).
demo(\+ A)    :- \+ demo(A).

%% Arithmetic / built-in.
demo(A is B)  :- A is B.
demo(A < B)   :- A < B.
demo(A > B)   :- A > B.
demo(A >= B)  :- A >= B.
demo(A =< B)  :- A =< B.
demo(A =:= B) :- A =:= B.
demo(A =\= B) :- A =\= B.

%% Constraint-specific reasoning.
demo(hard_constraint_holds(Name, Event, AllEvents)) :-
    check_hard(Name, [Event, AllEvents]).

demo(soft_constraint_cost(Name, Event, AllEvents, Prefs, Cost)) :-
    evaluate_soft(Name, [Event, AllEvents, Prefs], Cost).

demo(event_has_violation(Event, AllEvents, Violation)) :-
    violation(_, Event, AllEvents, Violation).

demo(event_is_valid(Event, AllEvents)) :-
    \+ violation(_, Event, AllEvents, _).

%% Catch-all: delegate to Prolog.
demo(Goal) :-
    Goal \= true,
    Goal \= (_ , _),
    Goal \= (_ ; _),
    Goal \= (\+ _),
    Goal \= (_ is _),
    Goal \= (_ < _),
    Goal \= (_ > _),
    Goal \= (_ >= _),
    Goal \= (_ =< _),
    Goal \= (_ =:= _),
    Goal \= (_ =\= _),
    Goal \= hard_constraint_holds(_, _, _),
    Goal \= soft_constraint_cost(_, _, _, _, _),
    Goal \= event_has_violation(_, _, _),
    Goal \= event_is_valid(_, _),
    call(Goal).

%% ============================================================================
%% LAYER 5 — SOLVER  (solve/2 — Central Reasoning Entry Point)
%% ============================================================================

%% --- Solve: validate hard constraints ---
solve(validate_hard(Event, AllEvents), Violations) :-
    findall(V, violation(_, Event, AllEvents, V), Violations).

%% --- Solve: calculate total soft cost ---
solve(soft_cost(Event, AllEvents, Preferences), TotalCost) :-
    evaluate_soft(preferred_time,    [Event, AllEvents, Preferences], C1),
    evaluate_soft(buffer_proximity,  [Event, AllEvents, Preferences], C2),
    evaluate_soft(daily_overload,    [Event, AllEvents, Preferences], C3),
    evaluate_soft(priority_schedule, [Event, AllEvents, Preferences], C4),
    TotalCost is C1 + C2 + C3 + C4.

%% --- Solve: displacement cost g(n) ---
solve(displacement_cost(OriginalEvents, ModifiedEvents), GCost) :-
    findall(EC, (
        member(OrigEvent, OriginalEvents),
        OrigEvent = event(Id, _, _, _, _, _, _, _),
        member(ModEvent, ModifiedEvents),
        ModEvent = event(Id, _, _, _, _, _, _, _),
        event_displacement_cost(OrigEvent, ModEvent, EC)
    ), Costs),
    sum_list(Costs, GCost).

%% --- Solve: priority loss h(n) ---
solve(priority_loss(ConflictingEvents, Strategy), HCost) :-
    findall(Loss, (
        member(Event, ConflictingEvents),
        event_priority_loss(Event, Strategy, Loss)
    ), Losses),
    sum_list(Losses, HCost).

%% --- Solve: heuristic f(n) = g(n) + h(n) ---
solve(heuristic(OrigEvents, CurrState, RemConflicts, Strategy), FScore) :-
    solve(displacement_cost(OrigEvents, CurrState), G),
    solve(priority_loss(RemConflicts, Strategy), H),
    FScore is G + H.

%% --- Solve: find best slot for an event ---
solve(find_best_slot(Event, AllEvents, MinH, MinM, MaxH, MaxM), BestSlot) :-
    Event = event(Id, Title, _SH, _SM, _EH, _EM, Priority, Type),
    time_to_minutes(_SH, _SM, OrigStart),
    time_to_minutes(_EH, _EM, OrigEnd),
    Duration is OrigEnd - OrigStart,
    time_to_minutes(MinH, MinM, MinStart),
    time_to_minutes(MaxH, MaxM, MaxEnd),
    exclude(event_has_id(Id), AllEvents, OtherEvents),
    fact(slot_step, Step),
    fact(max_slot_candidates, MaxN),
    MaxSlotStart is MaxEnd - Duration,
    findall(
        scored_slot(Score, SlotSH, SlotSM, SlotEH, SlotEM),
        (
            between(0, MaxN, N),
            SlotStart is MinStart + N * Step,
            SlotStart =< MaxSlotStart,
            SlotEnd is SlotStart + Duration,
            SlotEnd =< MaxEnd,
            \+ slot_conflicts_with_any(SlotStart, SlotEnd, OtherEvents),
            Displacement is abs(SlotStart - OrigStart),
            DisplacementCost is Displacement / 60.0 * 2,
            minutes_to_time(SlotStart, SlotSH, SlotSM),
            minutes_to_time(SlotEnd, SlotEH, SlotEM),
            CandidateEvent = event(Id, Title, SlotSH, SlotSM, SlotEH, SlotEM, Priority, Type),
            solve(soft_cost(CandidateEvent, OtherEvents, []), SoftCost),
            Score is DisplacementCost + SoftCost
        ),
        ScoredSlots
    ),
    ScoredSlots \= [],
    sort(ScoredSlots, [scored_slot(BestScore, BSH, BSM, BEH, BEM)|_]),
    BestSlot = slot(BSH, BSM, BEH, BEM, BestScore).

%% --- Solve: reschedule (decide between moving new or moving existing) ---
solve(reschedule(NewEvent, ExistingEvents, Strategy, MinH, MinM, MaxH, MaxM), Result) :-
    NewEvent = event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    %% Find conflicting events via inference rules
    findall(
        event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType),
        (
            member(event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType), ExistingEvents),
            time_to_minutes(ESH, ESM, ES),
            time_to_minutes(EEH, EEM, EE),
            NewStart < EE, NewEnd > ES
        ),
        ConflictingEvents
    ),
    (   ConflictingEvents = []
    ->  Result = result(no_conflict, [], 0)
    ;   %% Option 1: Move the new event
        (   solve(find_best_slot(NewEvent, ExistingEvents, MinH, MinM, MaxH, MaxM), NewSlot)
        ->  NewSlot = slot(SlotSH, SlotSM, SlotEH, SlotEM, MoveCost1)
        ;   MoveCost1 = 9999, SlotSH = 0, SlotSM = 0, SlotEH = 0, SlotEM = 0
        ),
        Option1Cost is MoveCost1 + NewPriority * 0.5,
        %% Option 2: Keep new event, move conflicting events
        try_move_conflicts(
            ConflictingEvents, ExistingEvents,
            event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
            MinH, MinM, MaxH, MaxM,
            MovedEvents2, MoveCost2
        ),
        (   MovedEvents2 = failed
        ->  Option2Cost = 9999
        ;   solve(priority_loss(ConflictingEvents, Strategy), PLoss),
            Option2Cost is MoveCost2 + PLoss
        ),
        pick_best_option(
            Strategy, NewPriority,
            option(move_new, slot(SlotSH, SlotSM, SlotEH, SlotEM), Option1Cost),
            option(place_new, MovedEvents2, Option2Cost),
            Result
        )
    ).

%% ============================================================================
%% PUBLIC API — Backward-Compatible Predicates
%% ============================================================================
%% These preserve the exact signatures Python calls.
%% Internally they delegate to solve/2.

%% validate_hard_constraints/3
validate_hard_constraints(Event, AllEvents, Violations) :-
    solve(validate_hard(Event, AllEvents), Violations).

%% calculate_soft_cost/4
calculate_soft_cost(Event, AllEvents, Preferences, TotalCost) :-
    solve(soft_cost(Event, AllEvents, Preferences), TotalCost).

%% calculate_displacement_cost/3
calculate_displacement_cost(OriginalEvents, ModifiedEvents, GCost) :-
    solve(displacement_cost(OriginalEvents, ModifiedEvents), GCost).

%% calculate_priority_loss/4
calculate_priority_loss(ConflictingEvents, Strategy, _Priorities, HCost) :-
    solve(priority_loss(ConflictingEvents, Strategy), HCost).

%% calculate_heuristic/5
calculate_heuristic(OriginalEvents, CurrentState, RemainingConflicts, Strategy, FScore) :-
    solve(heuristic(OriginalEvents, CurrentState, RemainingConflicts, Strategy), FScore).

%% find_best_slot/7
find_best_slot(Event, AllEvents, MinH, MinM, MaxH, MaxM, BestSlot) :-
    solve(find_best_slot(Event, AllEvents, MinH, MinM, MaxH, MaxM), BestSlot).

%% reschedule_event/8
reschedule_event(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
    ExistingEvents, Strategy,
    MinH, MinM, MaxH, MaxM,
    Result
) :-
    solve(reschedule(
        event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
        ExistingEvents, Strategy, MinH, MinM, MaxH, MaxM
    ), Result).

%% find_optimal_schedule/6
find_optimal_schedule(Events, NewEvent, Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution) :-
    NewEvent = event(_, _, _, _, _, _, _, _),
    append([NewEvent], Events, InitialEvents),
    find_all_conflicts(InitialEvents, Conflicts),
    (   Conflicts = []
    ->  Solution = solution(InitialEvents, 0, [])
    ;   InitialState = state(InitialEvents, Events, 0, [], Conflicts),
        astar_search([InitialState], [], Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution)
    ).

%% detect_chain_conflicts/4
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
            NewStart < CEnd, NewEnd > CStart
        ),
        ChainConflicts
    ).

%% suggest_reschedule_options/7
suggest_reschedule_options(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPri, NewType),
    ExistingEvents, Strategy,
    MinH, MinM, MaxH, MaxM,
    Options
) :-
    NewEvent = event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPri, NewType),
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    Duration is NewEnd - NewStart,
    %% Infer conflicts
    findall(
        event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType),
        (
            member(event(EId, ETitle, ESH, ESM, EEH, EEM, EPri, EType), ExistingEvents),
            time_to_minutes(ESH, ESM, ES),
            time_to_minutes(EEH, EEM, EE),
            NewStart < EE, NewEnd > ES
        ),
        Conflicts
    ),
    (   Conflicts = []
    ->  Options = [option(no_conflict, [], 0, 'No conflicts detected')]
    ;   %% Option A: Move new event to nearby free slots
        findall(
            option(move_new, [moved_to(SH, SM, EH, EM)], Score, Description),
            (
                find_near_slot(NewStart, Duration, ExistingEvents, MinH, MinM, MaxH, MaxM, SH, SM, EH, EM, Score),
                format(atom(Description), 'Move "~w" to ~w:~w-~w:~w', [NewTitle, SH, SM, EH, EM])
            ),
            OptionAs
        ),
        %% Option B: Move each conflicting event
        findall(
            option(move_existing, MovedList, TotalCost, Description),
            (
                member(ConflictEvent, Conflicts),
                ConflictEvent = event(CId, CTitle, _, _, _, _, CPri, _),
                solve(find_best_slot(ConflictEvent, [NewEvent|ExistingEvents], MinH, MinM, MaxH, MaxM), CSlot),
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
        fact(max_reschedule_options, MaxOpts),
        take_n(MaxOpts, SortedOptions, Options)
    ).

%% ============================================================================
%% INTERNAL — A* Search (State-Space Reasoning)
%% ============================================================================

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
            S1 < E2, S2 < E1
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
    ;   Bounds = bounds(MinH, MinM, MaxH, MaxM),
        NewDepth is MaxDepth - 1,
        findall(NextState, (
            member(conflict(Id1, Id2), Conflicts),
            (MovedId = Id1 ; MovedId = Id2),
            member(MovedEvent, Events),
            MovedEvent = event(MovedId, _, _, _, _, _, _, _),
            solve(find_best_slot(MovedEvent, Events, MinH, MinM, MaxH, MaxM), Slot),
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

%% ============================================================================
%% INTERNAL — Helpers
%% ============================================================================

event_has_id(Id, event(Id, _, _, _, _, _, _, _)).

slot_conflicts_with_any(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM, _, _), Events),
    time_to_minutes(SH, SM, EStart),
    time_to_minutes(EH, EM, EEnd),
    Start < EEnd, End > EStart,
    !.

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
    solve(find_best_slot(Event, UpdatedEvents, MinH, MinM, MaxH, MaxM), Slot),
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

find_near_slot(OrigStart, Duration, Events, MinH, MinM, MaxH, MaxM, SH, SM, EH, EM, Score) :-
    time_to_minutes(MinH, MinM, MinStart),
    time_to_minutes(MaxH, MaxM, MaxEnd),
    fact(slot_step, Step),
    fact(max_slot_candidates, MaxN),
    MaxSlotStart is MaxEnd - Duration,
    between(0, MaxN, N),
    SlotStart is MinStart + N * Step,
    SlotStart =< MaxSlotStart,
    SlotEnd is SlotStart + Duration,
    SlotEnd =< MaxEnd,
    \+ slot_conflicts_with_any(SlotStart, SlotEnd, Events),
    Displacement is abs(SlotStart - OrigStart),
    Score is Displacement / 60.0 * 2,
    minutes_to_time(SlotStart, SH, SM),
    minutes_to_time(SlotEnd, EH, EM).

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

sum_list([], 0).
sum_list([H|T], Sum) :-
    sum_list(T, RestSum),
    Sum is H + RestSum.

%% ============================================================================
%% Example Queries (KRR-style)
%% ============================================================================
%%
%% Hard constraint validation (via solver):
%% ?- solve(validate_hard(event(e1,"M",9,0,10,0,5,meeting), []), Violations).
%%
%% Soft cost calculation (via solver):
%% ?- solve(soft_cost(event(e1,"M",9,0,10,0,5,meeting), [], []), Cost).
%%
%% Meta-interpreter reasoning:
%% ?- demo(hard_constraint_holds(no_overlap, event(e1,"M",9,0,10,0,5,meeting), [])).
%% ?- demo(event_is_valid(event(e1,"M",9,0,10,0,5,meeting), [])).
%%
%% Custom operator queries:
%% ?- event(e1,"M",9,0,10,0,5,meeting) satisfies positive_duration.
%% ?- event(e1,"M",9,0,10,0,5,meeting) penalized_by soft(preferred_time, Cost).
%%
%% Heuristic calculation:
%% ?- solve(heuristic(Orig, Curr, Remaining, balanced), FScore).
