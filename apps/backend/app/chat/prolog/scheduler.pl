%% apps/backend/app/chat/prolog/scheduler.pl
%% ============================================================================
%% Schedule Assistant — Knowledge-Based Reasoning Engine
%% ============================================================================
%%
%% Architecture (Knowledge Representation & Reasoning):
%%
%%   Layer 1 — FACTS (Knowledge Base)
%%       Domain constants, time boundaries, configuration knowledge.
%%
%%   Layer 2 — RULES (Inference Rules)
%%       Declarative rules that derive new knowledge from facts.
%%       e.g., "Two intervals overlap iff S1 < E2 and S2 < E1"
%%
%%   Layer 3 — CONSTRAINTS (Constraint Declarations)
%%       Named, reified constraint objects that can be inspected.
%%       e.g., constraint(no_overlap, ...), constraint(within_bounds, ...)
%%
%%   Layer 4 — META-INTERPRETER (demo/1)
%%       A lightweight prove/reason engine that traces rule application.
%%
%%   Layer 5 — SOLVER (solve/2)
%%       Central entry point: every query is dispatched through solve/2,
%%       which selects applicable rules and drives the meta-interpreter.
%%
%% Design principles:
%%   • Knowledge is separated from the inference mechanism.
%%   • Rules are declarative — they state WHAT is true, not HOW to compute it.
%%   • Constraints are first-class objects that can be queried and composed.
%%   • The meta-interpreter makes reasoning explicit and traceable.
%%   • Python calls the same exported predicates; the solver routes internally.
%% ============================================================================

:- module(scheduler, [
    check_conflict/5,
    find_free_slots/7,
    find_free_ranges/5,
    find_free_days/7,
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3,
    %% --- New KRR-aware predicates (optional for Python, useful for Prolog) ---
    solve/2,
    demo/1,
    holds/1,
    find_available_slot/4,
    valid_schedule/2,
    conflict/3
]).

%% ============================================================================
%% LAYER 0 — CUSTOM OPERATORS
%% ============================================================================
%% Operators make knowledge representation read like natural-language
%% propositions, improving declarative clarity.

:- op(700, xfx, overlaps_with).
:- op(700, xfx, is_free_during).
:- op(700, xfx, conflicts_with).
:- op(600, xfx, to).               %% e.g., 9:00 to 17:00

%% ============================================================================
%% LAYER 1 — FACTS  (Knowledge Base)
%% ============================================================================
%% Pure ground knowledge — no computation, only declarations.
%% These facts can be queried, composed, and reasoned about.

%% --- Time domain facts ---
%% fact: minutes_in_day — the upper bound of the time domain
fact(minutes_in_day, 1440).

%% fact: slot_granularity — candidate slots are generated at this step (minutes)
fact(slot_granularity, 30).

%% fact: max_candidate_iterations — safety bound on slot generation
fact(max_candidate_iterations, 1000).

%% --- Metadata: self-describing knowledge entries ---
%% statement(Name, Type, Description)
statement(minutes_in_day,   domain_constant, 'Total minutes in a day (0-1439)').
statement(slot_granularity,  domain_constant, 'Granularity for candidate slot generation').
statement(overlap_rule,      inference_rule,  'Two intervals overlap iff S1 < E2 and S2 < E1').
statement(free_slot_rule,    inference_rule,  'A slot is free iff it conflicts with no event').
statement(free_range_rule,   inference_rule,  'A free range is a maximal gap between events').
statement(free_day_rule,     inference_rule,  'A day is free iff at least one slot fits').
statement(no_overlap,        constraint,      'A new event must not overlap existing events').
statement(within_bounds,     constraint,      'A slot must lie within [MinStart, MaxEnd]').
statement(positive_duration, constraint,      'End time must be strictly after start time').

%% --- Rule metadata: name → head pattern ---
%% rule(Name, Head, Description)
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
%% LAYER 2 — RULES  (Inference Rules)
%% ============================================================================
%% Declarative rules that derive new knowledge. Each rule states a logical
%% relationship; the meta-interpreter (Layer 4) applies them.

%% --- Time conversion rules ---
%% Rule: an (Hour, Minute) pair maps to TotalMinutes iff the values are valid.
time_to_minutes(Hour, Minute, Total) :-
    integer(Hour), Hour >= 0, Hour =< 23,
    integer(Minute), Minute >= 0, Minute =< 59,
    Total is Hour * 60 + Minute.

%% Rule: TotalMinutes maps back to (Hour, Minute).
minutes_to_time(Total, Hour, Minute) :-
    integer(Total), Total >= 0, Total =< 1439,
    Hour is Total // 60,
    Minute is Total mod 60.

%% --- Interval overlap rule (the core KRR axiom) ---
%% Rule: Two intervals [S1,E1) and [S2,E2) overlap iff S1 < E2 ∧ S2 < E1.
%% This is the Resolution-simplified form of ∃t : (S1 ≤ t < E1) ∧ (S2 ≤ t < E2).
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.

%% --- Operator-based overlap (syntactic sugar via custom operator) ---
%% Allows writing: interval(S1,E1) overlaps_with interval(S2,E2).
interval(S1, E1) overlaps_with interval(S2, E2) :-
    intervals_overlap(S1, E1, S2, E2).

%% --- Event overlap rule ---
%% Rule: A new time window overlaps an existing events time window.
events_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd) :-
    intervals_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd).

%% --- Conflict rule (reified — returns a reason term) ---
%% Rule: A proposed interval conflicts with an event because of time overlap.
conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), Reason) :-
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(NewStart, NewEnd, ExStart, ExEnd),
    Reason = overlap(ID, Title, SH, SM, EH, EM).

%% --- Slot freedom rule ---
%% Rule: A slot is free during Events iff no event overlaps it.
slot_is_free(Start, End, Events) :-
    \+ slot_conflicts_with_events(Start, End, Events).

%% --- Operator-based slot freedom ---
%% Allows writing: slot(S,E) is_free_during Events.
slot(S, E) is_free_during Events :-
    slot_is_free(S, E, Events).

%% --- Slot conflict rule ---
%% Rule: A slot conflicts with events iff at least one event overlaps it.
slot_conflicts_with_events(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM), Events),
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(Start, End, ExStart, ExEnd),
    !.  % One witness suffices (existential)

%% --- Operator-based conflict ---
%% Allows writing: interval(S,E) conflicts_with Events.
interval(S, E) conflicts_with Events :-
    slot_conflicts_with_events(S, E, Events).

%% --- Event-start extraction (for sorting) ---
event_start_minutes(event(_, _, SH, SM, _, _), Minutes) :-
    time_to_minutes(SH, SM, Minutes).

%% ============================================================================
%% LAYER 3 — CONSTRAINTS  (Declarative Constraint Definitions)
%% ============================================================================
%% Constraints are named objects. Each constraint/3 declares:
%%   constraint(Name, Args, Condition)
%% The solver checks constraints by calling check_constraint/2.

%% Constraint: no_overlap — a slot must not overlap any existing event.
constraint(no_overlap, [Start, End, Events],
    \+ slot_conflicts_with_events(Start, End, Events)).

%% Constraint: within_bounds — a slot must lie within the scheduling window.
constraint(within_bounds, [Start, End, MinStart, MaxEnd],
    (Start >= MinStart, End =< MaxEnd)).

%% Constraint: positive_duration — end must be after start.
constraint(positive_duration, [Start, End],
    End > Start).

%% check_constraint(+Name, +Args)
%% Succeeds iff the named constraint is satisfied with the given arguments.
check_constraint(Name, Args) :-
    constraint(Name, Args, Condition),
    call(Condition).

%% check_all_slot_constraints(+Start, +End, +MinStart, +MaxEnd, +Events)
%% Succeeds iff ALL scheduling constraints hold for a candidate slot.
check_all_slot_constraints(Start, End, MinStart, MaxEnd, Events) :-
    check_constraint(positive_duration, [Start, End]),
    check_constraint(within_bounds,     [Start, End, MinStart, MaxEnd]),
    check_constraint(no_overlap,        [Start, End, Events]).

%% ============================================================================
%% LAYER 4 — META-INTERPRETER  (demo/1)
%% ============================================================================
%% A lightweight meta-interpreter that makes reasoning explicit.
%% demo(Goal) succeeds iff Goal is provable from the knowledge base.
%%
%% This allows queries like:
%%   ?- demo(slot_is_free(480, 540, Events)).
%%   ?- demo(conflict(interval(600,660), Event, Reason)).

%% Base case: true is always provable.
demo(true).

%% Conjunction: prove both A and B.
demo((A, B)) :-
    demo(A),
    demo(B).

%% Disjunction: prove A or B.
demo((A ; _)) :- demo(A).
demo((_ ; B)) :- demo(B).

%% Negation as failure.
demo(\+ A) :- \+ demo(A).

%% Arithmetic / built-in evaluation — delegate to Prolog.
demo(A is B)  :- A is B.
demo(A < B)   :- A < B.
demo(A > B)   :- A > B.
demo(A >= B)  :- A >= B.
demo(A =< B)  :- A =< B.
demo(A =:= B) :- A =:= B.
demo(A =\= B) :- A =\= B.

%% Member — list reasoning.
demo(member(X, L)) :- member(X, L).

%% Constraint check — prove by verifying the named constraint.
demo(check_constraint(Name, Args)) :-
    check_constraint(Name, Args).

%% Catch-all: prove an arbitrary goal by calling it.
%% This lets demo/1 work on any predicate defined in this module.
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
    Goal \= member(_, _),
    Goal \= check_constraint(_, _),
    call(Goal).

%% holds(+Proposition)
%% Semantic alias: "this proposition holds in the current knowledge base."
holds(Proposition) :- demo(Proposition).

%% ============================================================================
%% LAYER 5 — SOLVER  (solve/2 — Central Reasoning Entry Point)
%% ============================================================================
%% Every high-level query routes through solve/2.
%% solve(+Query, -Result) dispatches to the appropriate reasoning strategy.

%% --- Solve: detect conflicts ---
solve(check_conflict(NSH, NSM, NEH, NEM, Events), Conflicts) :-
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        conflict(interval(NewStart, NewEnd), event(ID, Title, SH, SM, EH, EM), _Reason),
        Conflicts
    ).

%% --- Solve: find free slots (CSP) ---
solve(find_free_slots(Duration, Events, MinSH, MinSM, MaxEH, MaxEM), FreeSlots) :-
    time_to_minutes(MinSH, MinSM, MinStart),
    time_to_minutes(MaxEH, MaxEM, MaxEnd),
    fact(slot_granularity, Step),
    fact(max_candidate_iterations, MaxIter),
    MaxSlotStart is MaxEnd - Duration,
    findall(
        slot(SH, SM, EH, EM),
        (
            between(0, MaxIter, N),
            SlotStart is MinStart + N * Step,
            SlotStart =< MaxSlotStart,
            SlotEnd is SlotStart + Duration,
            check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events),
            minutes_to_time(SlotStart, SH, SM),
            minutes_to_time(SlotEnd, EH, EM)
        ),
        FreeSlots
    ).

%% --- Solve: find free ranges ---
solve(find_free_ranges(Events, MinSH, MinSM, MaxEH, MaxEM), FreeRanges) :-
    time_to_minutes(MinSH, MinSM, MinStart),
    time_to_minutes(MaxEH, MaxEM, MaxEnd),
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

%% --- Solve: find an available slot for an event (KRR-style query) ---
solve(find_available_slot(Duration, Events, Bounds, Slot), Slot) :-
    Bounds = bounds(MinSH, MinSM, MaxEH, MaxEM),
    solve(find_free_slots(Duration, Events, MinSH, MinSM, MaxEH, MaxEM), Slots),
    Slots = [Slot|_].   %% Return the first valid slot

%% --- Solve: validate a proposed schedule ---
solve(valid_schedule(SlotStart, SlotEnd, Events, MinStart, MaxEnd), Result) :-
    (   check_all_slot_constraints(SlotStart, SlotEnd, MinStart, MaxEnd, Events)
    ->  Result = valid
    ;   Result = invalid
    ).

%% ============================================================================
%% PUBLIC API — Backward-Compatible Predicates
%% ============================================================================
%% These preserve the exact signatures Python calls.
%% Internally, they delegate to solve/2.

%% check_conflict/5 — Python entry point for conflict detection.
check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents, Conflicts) :-
    solve(check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents), Conflicts).

%% find_free_slots/7 — Python entry point for free-slot CSP.
find_free_slots(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeSlots) :-
    solve(find_free_slots(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM), FreeSlots).

%% find_free_ranges/5 — Python entry point for contiguous free ranges.
find_free_ranges(Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeRanges) :-
    solve(find_free_ranges(Events, MinStartH, MinStartM, MaxEndH, MaxEndM), FreeRanges).

%% find_free_days/7 — Python entry point for free-day inference.
find_free_days(DurationMinutes, EventsByDay, StartHour, StartMinute, EndHour, EndMinute, FreeDays) :-
    solve(find_free_days(DurationMinutes, EventsByDay, StartHour, StartMinute, EndHour, EndMinute), FreeDays).

%% --- KRR-native query predicates (usable from Prolog or future Python calls) ---

%% find_available_slot(+Duration, +Events, +Bounds, -Slot)
%% KRR query: "Is there an available slot of Duration minutes?"
find_available_slot(Duration, Events, Bounds, Slot) :-
    solve(find_available_slot(Duration, Events, Bounds, Slot), Slot).

%% valid_schedule(+slot(Start, End), +context(Events, Min, Max))
%% KRR query: "Is this schedule placement valid?"
valid_schedule(slot(SH, SM, EH, EM), context(Events, MinSH, MinSM, MaxEH, MaxEM)) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    time_to_minutes(MinSH, MinSM, Min),
    time_to_minutes(MaxEH, MaxEM, Max),
    solve(valid_schedule(Start, End, Events, Min, Max), valid).

%% conflict(+NewEvent, +ExistingEvent, -Reason)
%% KRR query: "Does NewEvent conflict with ExistingEvent? Why?"
%% (Already defined as an inference rule in Layer 2.)

%% ============================================================================
%% INTERNAL HELPERS — Gap Finding for Free Ranges
%% ============================================================================

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
%% Example Queries (KRR-style)
%% ============================================================================
%%
%% Conflict detection (via solver):
%% ?- solve(check_conflict(9, 0, 10, 0, [event(e1, "Meeting", 9, 30, 10, 30)]), C).
%%
%% Free slot reasoning (via solver):
%% ?- solve(find_free_slots(60, [event(e1, "M", 9, 0, 10, 0)], 8, 0, 18, 0), S).
%%
%% Meta-interpreter reasoning:
%% ?- demo(slot_is_free(480, 540, [])).
%% true.
%%
%% Custom operator queries:
%% ?- interval(480, 540) overlaps_with interval(500, 600).
%% true.
%%
%% ?- slot(600, 660) is_free_during [event(e1, "M", 9, 0, 10, 0)].
%% true.
%%
%% Constraint checking:
%% ?- check_constraint(no_overlap, [480, 540, []]).
%% true.
%%
%% KRR-native queries:
%% ?- find_available_slot(60, [], bounds(8, 0, 18, 0), Slot).
%% ?- valid_schedule(slot(9,0,10,0), context([], 8, 0, 18, 0)).
%% ?- conflict(interval(540,600), event(e1,"M",9,0,10,0,_,_), Reason).
