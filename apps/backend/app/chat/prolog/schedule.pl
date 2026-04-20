%% ============================================================================
%% schedule.pl — Full Meta-Interpreter for Schedule Reasoning
%% ============================================================================
%%
%% Full meta-interpreter version of scheduler.pl. Every domain predicate is
%% resolved via clause/2 + recursive demo/1 instead of call/1. This makes
%% every resolution step transparent and controllable.
%%
%% KEY DIFFERENCE from scheduler.pl:
%%
%%   scheduler.pl   demo(Goal) :- ... call(Goal).
%%       → Wrapper: hands user-defined predicates back to Prolog.
%%
%%   schedule.pl    demo(Goal) :- clause(Goal, Body), demo(Body).
%%       → Full: retrieves each clause body and proves it recursively.
%%         Nothing is hidden. Every step passes through our code.
%%
%% Architecture (same 5 layers as scheduler.pl):
%%
%%   Layer 1 — FACTS       : Domain constants
%%   Layer 2 — RULES       : Inference rules (all :- dynamic)
%%   Layer 3 — CONSTRAINTS : Named constraint objects
%%   Layer 4 — META-INTERP : demo/1 with clause/2 (the full version)
%%   Layer 5 — SOLVER      : solve/2 routes through demo/1
%%
%% ============================================================================

:- module(schedule, [
    %% --- Same exports as scheduler.pl ---
    check_conflict/6,
    find_free_slots/7,
    find_free_ranges/6,
    find_free_days/7,
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3,
    solve/2,
    conflict/3,
    find_available_slot/4,
    valid_schedule/2,
    %% --- Full meta-interpreter predicates ---
    demo/1,
    holds/1,
    demo_trace/2,
    demo_depth/2,
    demo_all/2,
    is_builtin/1
]).

%% ============================================================================
%% LAYER 0 — CUSTOM OPERATORS  (same as scheduler.pl)
%% ============================================================================

:- op(700, xfx, overlaps_with).
:- op(700, xfx, is_free_during).
:- op(700, xfx, conflicts_with).
:- op(600, xfx, to).

%% ============================================================================
%% DYNAMIC DECLARATIONS
%% ============================================================================
%% All domain predicates MUST be dynamic so clause/2 can introspect them.
%% This is the fundamental requirement for a full meta-interpreter.

:- dynamic fact/2.
:- dynamic statement/3.
:- dynamic rule/3.
:- dynamic time_to_minutes/3.
:- dynamic minutes_to_time/3.
:- dynamic intervals_overlap/4.
:- dynamic events_overlap/4.
:- dynamic slot_is_free/3.
:- dynamic slot_conflicts_with_events/3.
:- dynamic conflict/3.
:- dynamic constraint/3.
:- dynamic check_constraint/2.
:- dynamic check_all_slot_constraints/5.
:- dynamic event_start_minutes/2.
:- dynamic (overlaps_with)/2.
:- dynamic (is_free_during)/2.
:- dynamic (conflicts_with)/2.

%% ============================================================================
%% LAYER 1 — FACTS  (Knowledge Base)
%% ============================================================================
%% Same domain constants as scheduler.pl.

fact(minutes_in_day, 1440).
fact(slot_granularity, 30).
fact(max_candidate_iterations, 1000).

statement(minutes_in_day,   domain_constant, 'Total minutes in a day (0-1439)').
statement(slot_granularity,  domain_constant, 'Granularity for candidate slot generation').
statement(overlap_rule,      inference_rule,  'Two intervals overlap iff S1 < E2 and S2 < E1').
statement(free_slot_rule,    inference_rule,  'A slot is free iff it conflicts with no event').
statement(free_range_rule,   inference_rule,  'A free range is a maximal gap between events').
statement(free_day_rule,     inference_rule,  'A day is free iff at least one slot fits').
statement(no_overlap,        constraint,      'A new event must not overlap existing events').
statement(within_bounds,     constraint,      'A slot must lie within [MinStart, MaxEnd]').
statement(positive_duration, constraint,      'End time must be strictly after start time').

rule(overlap_rule,
     intervals_overlap(_S1, _E1, _S2, _E2),
     'True when two time intervals share at least one common point').
rule(free_slot_rule,
     slot_is_free(_Start, _End, _Events),
     'True when no event in Events overlaps [Start, End]').
rule(conflict_detection_rule,
     conflict(_NewInterval, _Event, _Reason),
     'True when NewInterval conflicts with Event for Reason').

%% ============================================================================
%% LAYER 2 — RULES  (Inference Rules — all dynamic)
%% ============================================================================
%% Same declarative rules as scheduler.pl. Because they are dynamic,
%% demo/1 can retrieve their bodies via clause/2.

%% --- Time conversion rules ---
time_to_minutes(Hour, Minute, Total) :-
    integer(Hour), Hour >= 0, Hour =< 23,
    integer(Minute), Minute >= 0, Minute =< 59,
    Total is Hour * 60 + Minute.

minutes_to_time(Total, Hour, Minute) :-
    integer(Total), Total >= 0, Total =< 1439,
    Hour is Total // 60,
    Minute is Total mod 60.

%% --- Interval overlap rule ---
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.

%% --- Operator-based overlap ---
interval(S1, E1) overlaps_with interval(S2, E2) :-
    intervals_overlap(S1, E1, S2, E2).

%% --- Event overlap rule ---
events_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd) :-
    intervals_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd).

%% --- Conflict rule (reified) ---
conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), Reason) :-
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(NewStart, NewEnd, ExStart, ExEnd),
    Reason = overlap(ID, Title, SH, SM, EH, EM).

%% --- Slot freedom rule ---
slot_is_free(Start, End, Events) :-
    \+ slot_conflicts_with_events(Start, End, Events).

%% --- Operator-based slot freedom ---
slot(S, E) is_free_during Events :-
    slot_is_free(S, E, Events).

%% --- Slot conflict rule ---
%% Note: no cut (!) here — cuts dont work in meta-interpreted bodies.
%% The negation in slot_is_free already provides the existential check.
slot_conflicts_with_events(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM), Events),
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(Start, End, ExStart, ExEnd).

%% --- Operator-based conflict ---
interval(S, E) conflicts_with Events :-
    slot_conflicts_with_events(S, E, Events).

%% --- Event-start extraction ---
event_start_minutes(event(_, _, SH, SM, _, _), Minutes) :-
    time_to_minutes(SH, SM, Minutes).

%% ============================================================================
%% LAYER 3 — CONSTRAINTS  (Declarative Constraint Definitions)
%% ============================================================================
%% Same constraint objects as scheduler.pl.
%% check_constraint/2 uses demo(Condition) instead of call(Condition).

constraint(no_overlap, [Start, End, Events],
    \+ slot_conflicts_with_events(Start, End, Events)).

constraint(within_bounds, [Start, End, MinStart, MaxEnd],
    (Start >= MinStart, End =< MaxEnd)).

constraint(positive_duration, [Start, End], End > Start).

%% check_constraint/2 — routes through demo/1 (FULL meta-interpreter)
%% In scheduler.pl this uses call(Condition). Here it uses demo(Condition)
%% so every sub-goal in the constraint body is meta-interpreted.
check_constraint(Name, Args) :-
    constraint(Name, Args, Condition),
    demo(Condition).

check_all_slot_constraints(Start, End, MinStart, MaxEnd, Events) :-
    check_constraint(positive_duration, [Start, End]),
    check_constraint(within_bounds, [Start, End, MinStart, MaxEnd]),
    check_constraint(no_overlap, [Start, End, Events]).

%% ============================================================================
%% LAYER 4 — FULL META-INTERPRETER  (demo/1 with clause/2)
%% ============================================================================
%%
%% THIS is the key difference from scheduler.pl:
%%
%%   scheduler.pl:  demo(Goal) :- ... call(Goal).      ← wrapper
%%   schedule.pl:   demo(Goal) :- clause(Goal, Body), demo(Body).  ← full
%%
%% Every user-defined goal is opened up via clause/2 and its body is
%% recursively proved by demo/1. Nothing is hidden from the meta-level.

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

%% --- If-then (no else) ---
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

%% --- Arithmetic built-ins (no clauses exist — must delegate) ---
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
demo(succ(X, Y))  :- succ(X, Y).
demo(plus(X, Y, Z)) :- plus(X, Y, Z).
demo(copy_term(X, Y)) :- copy_term(X, Y).
demo(ground(X))    :- ground(X).
demo(var(X))       :- var(X).
demo(nonvar(X))    :- nonvar(X).
demo(!).

%% --- THE CORE: clause-based resolution ---
%% For any goal that is NOT a built-in, retrieve its clause with clause/2
%% and recursively prove the body. This is the FULL meta-interpreter pattern.
demo(Goal) :-
    \+ is_builtin(Goal),
    clause(Goal, Body),
    demo(Body).

%% is_builtin(+Goal) — guards clause/2 from built-in predicates
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
is_builtin(findall(_, _, _)).
is_builtin(write(_)).
is_builtin(writeln(_)).
is_builtin(nl).
is_builtin(format(_, _)).
is_builtin(format(atom(_), _, _)).
is_builtin(abs(_, _)).
is_builtin(min(_, _, _)).
is_builtin(max(_, _, _)).
is_builtin(succ(_, _)).
is_builtin(plus(_, _, _)).
is_builtin(copy_term(_, _)).
is_builtin(ground(_)).
is_builtin(var(_)).
is_builtin(nonvar(_)).
is_builtin(!).

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
    clause(Goal, Body),
    demo_trace(Body, BodyTrace).

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
    D1 is D - 1,
    clause(Goal, Body),
    demo_depth(Body, D1).

%% --- demo_all/2: collect all solutions ---
demo_all(Goal, Solutions) :-
    findall(Goal, demo(Goal), Solutions).

%% ============================================================================
%% LAYER 5 — SOLVER  (solve/2 — Central Reasoning Entry Point)
%% ============================================================================
%% Every high-level query routes through solve/2.
%% Domain reasoning within solve/2 uses demo/1 for full transparency.

%% --- Solve: detect conflicts ---
%% Uses demo(conflict(...)) so conflict resolution goes through clause/2.
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :-
    demo(time_to_minutes(NSH, NSM, NewStart)),
    demo(time_to_minutes(NEH, NEM, NewEnd)),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        demo(conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), _Reason)),
        Conflicts
    ).

%% --- Solve: find free slots (CSP) ---
solve(find_free_slots(Duration, Events, MinSH, MinSM, MaxEH, MaxEM), FreeSlots) :-
    demo(time_to_minutes(MinSH, MinSM, MinStart)),
    demo(time_to_minutes(MaxEH, MaxEM, MaxEnd)),
    demo(fact(slot_granularity, Step)),
    demo(fact(max_candidate_iterations, MaxIter)),
    MaxSlotStart is MaxEnd - Duration,
    findall(
        slot(SH, SM, EH, EM),
        (
            between(0, MaxIter, N),
            SlotStart is MinStart + N * Step,
            SlotStart =< MaxSlotStart,
            SlotEnd is SlotStart + Duration,
            demo(check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events)),
            demo(minutes_to_time(SlotStart, SH, SM)),
            demo(minutes_to_time(SlotEnd, EH, EM))
        ),
        FreeSlots
    ).

%% --- Solve: find free ranges ---
solve(find_free_ranges(Events, MinSH, MinSM, MaxEH, MaxEM), FreeRanges) :-
    demo(time_to_minutes(MinSH, MinSM, MinStart)),
    demo(time_to_minutes(MaxEH, MaxEM, MaxEnd)),
    (   Events = []
    ->  FreeRanges = [range(MinSH, MinSM, MaxEH, MaxEM)]
    ;   sort_events_by_start(Events, Sorted),
        find_gaps(Sorted, MinStart, MaxEnd, Gaps),
        convert_gaps_to_ranges(Gaps, FreeRanges)
    ).

%% --- Solve: find free days ---
solve(find_free_days(Duration, EventsByDay, SH, SM, EH, EM), FreeDays) :-
    findall(
        day(D, M, Y, Slots),
        (
            member(day(D, M, Y, DayEvents), EventsByDay),
            solve(find_free_slots(Duration, DayEvents, SH, SM, EH, EM), Slots),
            Slots \= []
        ),
        FreeDays
    ).

%% --- Solve: find an available slot (KRR-style) ---
solve(find_available_slot(Duration, Events, Bounds, Slot), Slot) :-
    Bounds = bounds(MinSH, MinSM, MaxEH, MaxEM),
    solve(find_free_slots(Duration, Events, MinSH, MinSM, MaxEH, MaxEM), Slots),
    Slots = [Slot|_].

%% --- Solve: validate a proposed schedule ---
solve(valid_schedule(SlotStart, SlotEnd, Events, MinStart, MaxEnd), Result) :-
    (   demo(check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events))
    ->  Result = valid
    ;   Result = invalid
    ).

%% ============================================================================
%% PUBLIC API — Backward-Compatible Predicates
%% ============================================================================
%% Same signatures Python calls. Internally delegate to solve/2.

check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents, Conflicts) :-
    solve(check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents), Conflicts).

find_free_slots(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeSlots) :-
    solve(find_free_slots(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM), FreeSlots).

find_free_ranges(Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeRanges) :-
    solve(find_free_ranges(Events, MinStartH, MinStartM, MaxEndH, MaxEndM), FreeRanges).

find_free_days(DurationMinutes, EventsByDay, StartHour, StartMinute, EndHour, EndMinute, FreeDays) :-
    solve(find_free_days(DurationMinutes, EventsByDay, StartHour, StartMinute, EndHour, EndMinute), FreeDays).

%% --- KRR-native predicates ---

find_available_slot(Duration, Events, Bounds, Slot) :-
    solve(find_available_slot(Duration, Events, Bounds, Slot), Slot).

valid_schedule(slot(SH, SM, EH, EM), context(Events, MinSH, MinSM, MaxEH, MaxEM)) :-
    demo(time_to_minutes(SH, SM, Start)),
    demo(time_to_minutes(EH, EM, End)),
    demo(time_to_minutes(MinSH, MinSM, Min)),
    demo(time_to_minutes(MaxEH, MaxEM, Max)),
    solve(valid_schedule(Start, End, Events, Min, Max), valid).

%% ============================================================================
%% INTERNAL HELPERS — Gap Finding for Free Ranges
%% ============================================================================
%% These are procedural helpers (sorting, list manipulation) that use
%% direct Prolog calls — they dont benefit from meta-interpretation.

sort_events_by_start(Events, Sorted) :-
    map_list_to_pairs(event_start_minutes, Events, Pairs),
    keysort(Pairs, SortedPairs),
    pairs_values(SortedPairs, Sorted).

find_gaps([], MinStart, MaxEnd, [gap(MinStart, MaxEnd)]) :-
    MinStart < MaxEnd, !.
find_gaps([], _, _, []).
find_gaps([Event|Rest], MinStart, MaxEnd, Gaps) :-
    Event = event(_, _, SH, SM, EH, EM),
    time_to_minutes(SH, SM, EventStart),
    time_to_minutes(EH, EM, EventEnd),
    (   MinStart < EventStart
    ->  GapEnd is min(EventStart, MaxEnd),
        (   MinStart < GapEnd
        ->  FirstGap = [gap(MinStart, GapEnd)]
        ;   FirstGap = []
        )
    ;   FirstGap = []
    ),
    NewMinStart is max(MinStart, EventEnd),
    find_gaps(Rest, NewMinStart, MaxEnd, RestGaps),
    append(FirstGap, RestGaps, Gaps).

convert_gaps_to_ranges([], []).
convert_gaps_to_ranges([gap(StartMin, EndMin)|Rest], [range(SH, SM, EH, EM)|RestRanges]) :-
    StartMin < EndMin,
    minutes_to_time(StartMin, SH, SM),
    minutes_to_time(EndMin, EH, EM),
    convert_gaps_to_ranges(Rest, RestRanges).
convert_gaps_to_ranges([gap(StartMin, EndMin)|Rest], RestRanges) :-
    StartMin >= EndMin,
    convert_gaps_to_ranges(Rest, RestRanges).

%% ============================================================================
%% RESOLUTION TRACE: How demo/1 proves slot_is_free(480, 540, [])
%% ============================================================================
%%
%%   demo(slot_is_free(480, 540, []))
%%     → \+ is_builtin(slot_is_free(480,540,[]))  ✓
%%     → clause(slot_is_free(480,540,[]), Body)
%%       Body = \+ slot_conflicts_with_events(480, 540, [])
%%     → demo(\+ slot_conflicts_with_events(480, 540, []))
%%       → \+ demo(slot_conflicts_with_events(480, 540, []))
%%         → clause(slot_conflicts_with_events(480,540,[]), Body2)
%%           Body2 = (member(event(_,_,SH,SM,EH,EM), []), ...)
%%         → demo(member(event(...), []))  ← built-in, delegates
%%           → member(event(...), [])  → fails (empty list)
%%         → \+ fails → succeeds
%%     → succeeds ✓
%%
%% ============================================================================
%% Example Queries
%% ============================================================================
%%
%% Full meta-interpreter (every step via clause/2):
%%   ?- demo(intervals_overlap(480, 600, 540, 660)).
%%   ?- demo(slot_is_free(480, 540, [])).
%%   ?- demo(conflict(interval(540,600), event(e1,"M",9,0,10,0), R)).
%%
%% With proof trace:
%%   ?- demo_trace(intervals_overlap(480, 600, 540, 660), Trace).
%%
%% With depth limit:
%%   ?- demo_depth(slot_is_free(480, 540, []), 10).
%%
%% Via solver (public API):
%%   ?- solve(check_conflict(9,0,10,0,[event(e1,"M",9,30,10,30)]), C).
%%   ?- solve(find_free_slots(60,[event(e1,"M",9,0,10,0)],8,0,18,0), S).
%%
%% Operator syntax:
%%   ?- interval(480,540) overlaps_with interval(500,600).
%%   ?- slot(600,660) is_free_during [event(e1,"M",9,0,10,0)].
%%
%% ============================================================================