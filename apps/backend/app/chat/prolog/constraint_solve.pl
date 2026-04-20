%% ============================================================================
%% constraint_solve.pl — Full Meta-Interpreter for Constraint-Based Reasoning
%% ============================================================================
%%
%% Full meta-interpreter version of constraint_solver.pl. Every domain predicate
%% is resolved via clause/2 + recursive demo/1 instead of call/1.
%%
%% KEY DIFFERENCE from constraint_solver.pl:
%%
%%   constraint_solver.pl   demo(Goal) :- ... call(Goal).      ← wrapper
%%   constraint_solve.pl    demo(Goal) :- clause(Goal, Body), demo(Body). ← full
%%
%% Architecture (same 5 layers as constraint_solver.pl):
%%
%%   Layer 1 — FACTS       : Domain constants, weights, windows
%%   Layer 2 — RULES       : Violation rules, soft cost rules, displacement
%%   Layer 3 — CONSTRAINTS : Hard (check_hard/2) and soft (evaluate_soft/3)
%%   Layer 4 — META-INTERP : demo/1 with clause/2 (the full version)
%%   Layer 5 — SOLVER      : solve/2 routes through demo/1
%%
%% ============================================================================

:- module(constraint_solve, [
    %% --- Same exports as constraint_solver.pl ---
    validate_hard_constraints/3,
    calculate_soft_cost/4,
    calculate_displacement_cost/3,
    calculate_priority_loss/4,
    calculate_heuristic/5,
    find_best_slot/7,
    reschedule_event/8,
    find_optimal_schedule/6,
    detect_chain_conflicts/7,
    suggest_reschedule_options/8,
    %% --- Full meta-interpreter predicates ---
    solve/2,
    demo/1,
    holds/1,
    demo_trace/2,
    demo_depth/2,
    demo_all/2,
    is_builtin/1,
    check_hard/2,
    evaluate_soft/3
]).

:- use_module(schedule, [
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3
]).

%% ============================================================================
%% LAYER 0 — CUSTOM OPERATORS  (same as constraint_solver.pl)
%% ============================================================================

:- op(700, xfx, violates).
:- op(700, xfx, satisfies).
:- op(700, xfx, penalized_by).

%% ============================================================================
%% DYNAMIC DECLARATIONS
%% ============================================================================
%% All domain predicates MUST be dynamic so clause/2 can introspect them.

:- dynamic fact/2.
:- dynamic statement/3.
:- dynamic rule/3.
:- dynamic strategy_weight/2.
:- dynamic preferred_window/3.
:- dynamic preference_penalty/2.
:- dynamic violation/4.
:- dynamic soft_cost/5.
:- dynamic event_displacement_cost/3.
:- dynamic event_priority_loss/3.
:- dynamic check_hard/2.
:- dynamic evaluate_soft/3.
:- dynamic (violates)/2.
:- dynamic (satisfies)/2.
:- dynamic (penalized_by)/2.
:- dynamic event_has_id/2.
:- dynamic slot_conflicts_with_any/3.

%% ============================================================================
%% LAYER 1 — FACTS  (Knowledge Base)
%% ============================================================================
%% Same domain constants as constraint_solver.pl.

%% --- Working-hour boundaries (minutes from midnight) ---
fact(working_hours_start, 360).    %% 6:00 AM
fact(working_hours_end,   1380).   %% 11:00 PM

%% --- Buffer requirements ---
fact(min_buffer_minutes, 15).

%% --- Daily overload thresholds ---
fact(daily_soft_limit, 6).
fact(daily_hard_limit, 8).

%% --- Slot search parameters ---
fact(slot_step, 30).
fact(max_slot_candidates, 100).
fact(max_reschedule_options, 3).

%% --- Displacement cost parameters ---
fact(move_penalty,    3).
fact(shift_weight,    2).
fact(priority_factor, 0.5).

%% --- Strategy weights ---
strategy_weight(minimize_moves,  0.5).
strategy_weight(maximize_quality, 2.0).
strategy_weight(balanced,         1.0).

%% --- Preferred time windows ---
preferred_window(meeting,  540, 1020).
preferred_window(study,    480,  720).
preferred_window(study,    840, 1080).
preferred_window(exercise, 360,  480).
preferred_window(exercise, 1020, 1380).

%% --- Preference violation penalties ---
preference_penalty(meeting,  10).
preference_penalty(study,     5).
preference_penalty(exercise,  3).

%% --- Metadata ---
statement(no_overlap,        hard_constraint, 'Event must not overlap other events').
statement(within_work_hours, hard_constraint, 'Event must be within working hours').
statement(positive_duration, hard_constraint, 'End time must be after start time').
statement(preferred_time,    soft_constraint, 'Events should be in their preferred window').
statement(buffer_proximity,  soft_constraint, 'Events should have buffer gaps between them').
statement(daily_overload,    soft_constraint, 'Avoid too many events in one day').
statement(priority_schedule, soft_constraint, 'High-priority events belong in peak hours').

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
%% LAYER 2 — RULES  (Inference Rules — all dynamic)
%% ============================================================================

%% --- Hard constraint violation rules ---

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

violation(before_working_hours, event(_Id, _T, SH, SM, _EH, _EM, _P, _Ty), _AllEvents,
          before_working_hours) :-
    time_to_minutes(SH, SM, Start),
    fact(working_hours_start, WorkStart),
    Start < WorkStart.

violation(after_working_hours, event(_Id, _T, _SH, _SM, EH, EM, _P, _Ty), _AllEvents,
          after_working_hours) :-
    time_to_minutes(EH, EM, End),
    fact(working_hours_end, WorkEnd),
    End > WorkEnd.

violation(positive_duration, event(_Id, _T, SH, SM, EH, EM, _P, _Ty), _AllEvents,
          invalid_duration) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    End =< Start.

%% --- Soft cost rules ---

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

soft_cost(daily_overload, _Event, AllEvents, _Prefs, Cost) :-
    length(AllEvents, N),
    fact(daily_hard_limit, HardLim),
    fact(daily_soft_limit, SoftLim),
    (   N > HardLim -> Cost is (N - HardLim) * 5
    ;   N > SoftLim -> Cost is (N - SoftLim) * 2
    ;   Cost = 0
    ).

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
event_priority_loss(event(_Id, _T, _SH, _SM, _EH, _EM, Priority, _Ty), Strategy, Loss) :-
    strategy_weight(Strategy, W),
    Loss is Priority * Priority * W.

%% ============================================================================
%% LAYER 3 — CONSTRAINTS  (First-Class Constraint Objects)
%% ============================================================================
%% check_hard/2 and evaluate_soft/3 use demo/1 for domain reasoning.

%% --- Hard constraint checker ---
%% Uses demo(\+ violation(...)) so violation checks go through clause/2.
check_hard(no_overlap, [Event, AllEvents]) :-
    \+ demo(violation(no_overlap, Event, AllEvents, _)).

check_hard(before_working_hours, [Event]) :-
    \+ demo(violation(before_working_hours, Event, [], _)).

check_hard(after_working_hours, [Event]) :-
    \+ demo(violation(after_working_hours, Event, [], _)).

check_hard(positive_duration, [Event]) :-
    \+ demo(violation(positive_duration, Event, [], _)).

%% --- Soft constraint evaluator ---
%% Uses demo(soft_cost(...)) so cost computation goes through clause/2.
evaluate_soft(preferred_time, [Event, AllEvents, Prefs], Cost) :-
    demo(soft_cost(preferred_time, Event, AllEvents, Prefs, Cost)).

evaluate_soft(buffer_proximity, [Event, AllEvents, _Prefs], Cost) :-
    demo(soft_cost(buffer_proximity, Event, AllEvents, _, Cost)).

evaluate_soft(daily_overload, [_Event, AllEvents, _Prefs], Cost) :-
    demo(soft_cost(daily_overload, _, AllEvents, _, Cost)).

evaluate_soft(priority_schedule, [Event, _AllEvents, _Prefs], Cost) :-
    demo(soft_cost(priority_schedule, Event, _, _, Cost)).

%% --- Operator-based constraint checking ---
Event satisfies ConstraintName :-
    check_hard(ConstraintName, [Event, []]).

Event violates ConstraintName :-
    demo(violation(ConstraintName, Event, [], _)).

Event penalized_by soft(Name, Cost) :-
    evaluate_soft(Name, [Event, [], []], Cost),
    Cost > 0.

%% ============================================================================
%% LAYER 4 — FULL META-INTERPRETER  (demo/1 with clause/2)
%% ============================================================================
%%
%% constraint_solver.pl:  demo(Goal) :- ... call(Goal).       ← wrapper
%% constraint_solve.pl:   demo(Goal) :- clause(Goal, Body), demo(Body). ← full
%%
%% For cross-module predicates (time_to_minutes, etc.), clause/2 follows
%% SWI-Prologs import chain to find clauses in the schedule module.
%% If not found locally, we fall back to schedule:demo(Goal).

%% --- Base case ---
demo(true).

%% --- Conjunction ---
demo((A, B)) :-
    demo(A),
    demo(B).

%% --- If-then-else (must come BEFORE general disjunction) ---
demo((Cond -> Then ; Else)) :-
    (   demo(Cond)
    ->  demo(Then)
    ;   demo(Else)
    ).

%% --- If-then ---
demo((Cond -> Then)) :-
    demo(Cond),
    demo(Then).

%% --- Disjunction ---
demo((A ; _B)) :- demo(A).
demo((_A ; B)) :- demo(B).

%% --- Negation as failure ---
demo(\+ A) :- \+ demo(A).

%% --- Equality and unification ---
demo(X = Y)  :- X = Y.
demo(X \= Y) :- X \= Y.

%% --- Arithmetic built-ins ---
demo(X is E)  :- X is E.
demo(X < Y)   :- X < Y.
demo(X > Y)   :- X > Y.
demo(X >= Y)  :- X >= Y.
demo(X =< Y)  :- X =< Y.
demo(X =:= Y) :- X =:= Y.
demo(X =\= Y) :- X =\= Y.

%% --- Type-checking built-ins ---
demo(integer(X))  :- integer(X).
demo(number(X))   :- number(X).
demo(atom(X))     :- atom(X).
demo(is_list(X))  :- is_list(X).

%% --- List / collection built-ins ---
demo(member(X, L))        :- member(X, L).
demo(append(A, B, C))     :- append(A, B, C).
demo(length(L, N))        :- length(L, N).
demo(between(Lo, Hi, X))  :- between(Lo, Hi, X).
demo(msort(L, S))         :- msort(L, S).
demo(sort(L, S))          :- sort(L, S).
demo(exclude(P, L, R))    :- exclude(P, L, R).
demo(sum_list(L, S))      :- sum_list(L, S).

%% --- findall: wrap inner goal in demo/1 ---
demo(findall(T, G, L)) :- findall(T, demo(G), L).

%% --- I/O built-ins ---
demo(write(X))   :- write(X).
demo(writeln(X)) :- writeln(X).
demo(nl) :- nl.
demo(format(Fmt, Args)) :- format(Fmt, Args).
demo(format(atom(A), Fmt, Args)) :- format(atom(A), Fmt, Args).

%% --- Misc built-ins ---
demo(abs(X, Y))   :- Y is abs(X).
demo(min(X, Y, Z)) :- Z is min(X, Y).
demo(max(X, Y, Z)) :- Z is max(X, Y).
demo(copy_term(X, Y)) :- copy_term(X, Y).
demo(ground(X))    :- ground(X).
demo(var(X))       :- var(X).
demo(nonvar(X))    :- nonvar(X).
demo(!).

%% --- Constraint-specific reasoning (convenience layer) ---
demo(hard_constraint_holds(Name, Event, AllEvents)) :-
    check_hard(Name, [Event, AllEvents]).

demo(soft_constraint_cost(Name, Event, AllEvents, Prefs, Cost)) :-
    evaluate_soft(Name, [Event, AllEvents, Prefs], Cost).

demo(event_has_violation(Event, AllEvents, Violation)) :-
    demo(violation(_, Event, AllEvents, Violation)).

demo(event_is_valid(Event, AllEvents)) :-
    \+ demo(violation(_, Event, AllEvents, _)).

%% --- THE CORE: clause-based resolution ---
%% For user-defined goals: retrieve clause body via clause/2, prove recursively.
%% Cross-module fallback: if clause/2 cant find it locally, try schedule:demo.
demo(Goal) :-
    \+ is_builtin(Goal),
    \+ is_constraint_query(Goal),
    (   clause(Goal, Body)
    ->  demo(Body)
    ;   schedule:demo(Goal)
    ).

%% is_builtin(+Goal) — guards clause/2
is_builtin(true).
is_builtin((_ , _)).
is_builtin((_ ; _)).
is_builtin(\+ _).
is_builtin((_ -> _)).
is_builtin(_ = _).
is_builtin(_ \= _).
is_builtin(_ is _).
is_builtin(_ < _).
is_builtin(_ > _).
is_builtin(_ >= _).
is_builtin(_ =< _).
is_builtin(_ =:= _).
is_builtin(_ =\= _).
is_builtin(integer(_)).
is_builtin(number(_)).
is_builtin(atom(_)).
is_builtin(is_list(_)).
is_builtin(member(_, _)).
is_builtin(append(_, _, _)).
is_builtin(length(_, _)).
is_builtin(between(_, _, _)).
is_builtin(msort(_, _)).
is_builtin(sort(_, _)).
is_builtin(exclude(_, _, _)).
is_builtin(sum_list(_, _)).
is_builtin(findall(_, _, _)).
is_builtin(write(_)).
is_builtin(writeln(_)).
is_builtin(nl).
is_builtin(format(_, _)).
is_builtin(format(atom(_), _, _)).
is_builtin(abs(_, _)).
is_builtin(min(_, _, _)).
is_builtin(max(_, _, _)).
is_builtin(copy_term(_, _)).
is_builtin(ground(_)).
is_builtin(var(_)).
is_builtin(nonvar(_)).
is_builtin(!).

%% is_constraint_query(+Goal) — prevent infinite recursion on constraint queries
is_constraint_query(hard_constraint_holds(_, _, _)).
is_constraint_query(soft_constraint_cost(_, _, _, _, _)).
is_constraint_query(event_has_violation(_, _, _)).
is_constraint_query(event_is_valid(_, _)).

%% holds/1 — semantic alias for demo/1
holds(Proposition) :- demo(Proposition).

%% ============================================================================
%% LAYER 4b — META-INTERPRETER VARIANTS
%% ============================================================================

%% --- demo_trace/2: builds proof/explanation trees ---
demo_trace(true, true).

demo_trace((A, B), (TraceA, TraceB)) :-
    demo_trace(A, TraceA),
    demo_trace(B, TraceB).

demo_trace((A ; _B), or_left(TraceA)) :-
    demo_trace(A, TraceA).
demo_trace((_A ; B), or_right(TraceB)) :-
    demo_trace(B, TraceB).

demo_trace(\+ A, negation(A)) :-
    \+ demo(A).

demo_trace(Goal, builtin(Goal)) :-
    is_builtin(Goal),
    Goal \= true,
    Goal \= (_ , _),
    Goal \= (_ ; _),
    Goal \= (\+ _),
    demo(Goal).

demo_trace(Goal, step(Goal, BodyTrace)) :-
    \+ is_builtin(Goal),
    \+ is_constraint_query(Goal),
    (   clause(Goal, Body)
    ->  demo_trace(Body, BodyTrace)
    ;   schedule:demo_trace(Goal, BodyTrace)
    ).

%% --- demo_depth/2: depth-limited resolution ---
demo_depth(_, D) :-
    D =< 0, !, fail.

demo_depth(true, _).

demo_depth((A, B), D) :-
    demo_depth(A, D),
    demo_depth(B, D).

demo_depth((A ; _B), D) :- demo_depth(A, D).
demo_depth((_A ; B), D) :- demo_depth(B, D).

demo_depth(\+ A, D) :-
    \+ demo_depth(A, D).

demo_depth(Goal, _D) :-
    is_builtin(Goal),
    Goal \= true,
    Goal \= (_ , _),
    Goal \= (_ ; _),
    Goal \= (\+ _),
    demo(Goal).

demo_depth(Goal, D) :-
    \+ is_builtin(Goal),
    \+ is_constraint_query(Goal),
    D1 is D - 1,
    (   clause(Goal, Body)
    ->  demo_depth(Body, D1)
    ;   schedule:demo_depth(Goal, D1)
    ).

%% --- demo_all/2: collect all solutions ---
demo_all(Goal, Solutions) :-
    findall(Goal, demo(Goal), Solutions).

%% ============================================================================
%% LAYER 5 — SOLVER  (solve/2 — Central Reasoning Entry Point)
%% ============================================================================
%% Domain reasoning within solve/2 uses demo/1 for full transparency.

%% --- Solve: validate hard constraints ---
solve(validate_hard(Event, AllEvents), Violations) :-
    findall(V, demo(violation(_, Event, AllEvents, V)), Violations).

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
        demo(event_displacement_cost(OrigEvent, ModEvent, EC))
    ), Costs),
    sum_list(Costs, GCost).

%% --- Solve: priority loss h(n) ---
solve(priority_loss(ConflictingEvents, Strategy), HCost) :-
    findall(Loss, (
        member(Event, ConflictingEvents),
        demo(event_priority_loss(Event, Strategy, Loss))
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
    demo(fact(slot_step, Step)),
    demo(fact(max_slot_candidates, MaxN)),
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

%% --- Solve: reschedule ---
solve(reschedule(NewEvent, ExistingEvents, Strategy, MinH, MinM, MaxH, MaxM), Result) :-
    NewEvent = event(NewId, NewTitle, NSH, NSM, NEH, NEM, NewPriority, NewType),
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    %% Find conflicting events via demo/1
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
        %% Option 2: Keep new, move conflicts
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

validate_hard_constraints(Event, AllEvents, Violations) :-
    solve(validate_hard(Event, AllEvents), Violations).

calculate_soft_cost(Event, AllEvents, Preferences, TotalCost) :-
    solve(soft_cost(Event, AllEvents, Preferences), TotalCost).

calculate_displacement_cost(OriginalEvents, ModifiedEvents, GCost) :-
    solve(displacement_cost(OriginalEvents, ModifiedEvents), GCost).

calculate_priority_loss(ConflictingEvents, Strategy, _Priorities, HCost) :-
    solve(priority_loss(ConflictingEvents, Strategy), HCost).

calculate_heuristic(OriginalEvents, CurrentState, RemainingConflicts, Strategy, FScore) :-
    solve(heuristic(OriginalEvents, CurrentState, RemainingConflicts, Strategy), FScore).

find_best_slot(Event, AllEvents, MinH, MinM, MaxH, MaxM, BestSlot) :-
    solve(find_best_slot(Event, AllEvents, MinH, MinM, MaxH, MaxM), BestSlot).

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

find_optimal_schedule(Events, NewEvent, Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution) :-
    NewEvent = event(_, _, _, _, _, _, _, _),
    append([NewEvent], Events, InitialEvents),
    find_all_conflicts(InitialEvents, Conflicts),
    (   Conflicts = []
    ->  Solution = solution(InitialEvents, 0, [])
    ;   InitialState = state(InitialEvents, Events, 0, [], Conflicts),
        astar_search([InitialState], [], Strategy, bounds(MinH, MinM, MaxH, MaxM), MaxDepth, Solution)
    ).

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
    ;   %% Option A: Move new event
        findall(
            option(move_new, [moved_to(SH, SM, EH, EM)], Score, Description),
            (
                find_near_slot(NewStart, Duration, ExistingEvents, MinH, MinM, MaxH, MaxM, SH, SM, EH, EM, Score),
                format(atom(Description), 'Move "~w" to ~w:~w-~w:~w', [NewTitle, SH, SM, EH, EM])
            ),
            OptionAs
        ),
        %% Option B: Move conflicting events
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
        demo(fact(max_reschedule_options, MaxOpts)),
        take_n(MaxOpts, SortedOptions, Options)
    ).

%% ============================================================================
%% INTERNAL — A* Search (State-Space Reasoning)
%% ============================================================================
%% A* is procedural (queue management, state comparison). It calls solve/2
%% for domain reasoning (find_best_slot, displacement cost) which routes
%% through demo/1 for full transparency on those sub-goals.

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
%% Procedural helpers use direct Prolog calls (no benefit from meta-interpretation).

event_has_id(Id, event(Id, _, _, _, _, _, _, _)).

slot_conflicts_with_any(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM, _, _), Events),
    time_to_minutes(SH, SM, EStart),
    time_to_minutes(EH, EM, EEnd),
    Start < EEnd, End > EStart.

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
    demo(fact(slot_step, Step)),
    demo(fact(max_slot_candidates, MaxN)),
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
) :-
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
%% RESOLUTION TRACE: How demo/1 proves violation(no_overlap, Event, All, V)
%% ============================================================================
%%
%%   demo(violation(no_overlap, Event, AllEvents, V))
%%     → \+ is_builtin(violation(...))  ✓
%%     → clause(violation(no_overlap, Event, AllEvents, V), Body)
%%       Body = (time_to_minutes(SH, SM, Start), time_to_minutes(EH, EM, End),
%%               member(..., AllEvents), OtherId \= Id,
%%               time_to_minutes(OSH, OSM, OStart), time_to_minutes(OEH, OEM, OEnd),
%%               OStart < End, Start < OEnd)
%%     → demo(Body)
%%       → demo(time_to_minutes(SH, SM, Start))   ← clause/2 → schedule module
%%       → demo(time_to_minutes(EH, EM, End))      ← clause/2 → schedule module
%%       → demo(member(..., AllEvents))             ← built-in
%%       → demo(OtherId \= Id)                      ← built-in
%%       → demo(time_to_minutes(OSH, OSM, OStart))  ← clause/2 → schedule module
%%       → demo(time_to_minutes(OEH, OEM, OEnd))    ← clause/2 → schedule module
%%       → demo(OStart < End)                        ← built-in arithmetic
%%       → demo(Start < OEnd)                        ← built-in arithmetic
%%     → succeeds (if overlap exists)
%%
%% ============================================================================
%% Example Queries
%% ============================================================================
%%
%% Hard constraint (full meta-interpretation):
%%   ?- demo(violation(no_overlap, event(e1,"M",9,0,10,0,5,meeting),
%%           [event(e2,"N",9,30,10,30,3,meeting)], V)).
%%
%% Soft cost (through demo/1):
%%   ?- demo(soft_cost(preferred_time, event(e1,"M",9,0,10,0,5,meeting), [], [], Cost)).
%%
%% Convenience queries:
%%   ?- demo(hard_constraint_holds(no_overlap, Event, AllEvents)).
%%   ?- demo(event_is_valid(event(e1,"M",9,0,10,0,5,meeting), [])).
%%
%% With proof trace:
%%   ?- demo_trace(violation(no_overlap, Event, AllEvents, V), Trace).
%%
%% Via solver:
%%   ?- solve(validate_hard(event(e1,"M",9,0,10,0,5,meeting), []), Vs).
%%   ?- solve(soft_cost(event(e1,"M",9,0,10,0,5,meeting), [], []), Cost).
%%   ?- solve(heuristic(Orig, Curr, Remaining, balanced), FScore).
%%
%% Operator syntax:
%%   ?- event(e1,"M",9,0,10,0,5,meeting) satisfies positive_duration.
%%   ?- event(e1,"M",9,0,10,0,5,meeting) penalized_by soft(preferred_time, Cost).
%%
%% ============================================================================
