%% apps/backend/app/chat/prolog/scheduler.pl
%% ============================================================================
%% Schedule Assistant — Knowledge Base with Meta-Interpreter Architecture
%% ============================================================================
%%
%% This module implements scheduling logic using Knowledge Representation
%% and Reasoning (KR&R) with a three-layer meta-interpreter pattern:
%%
%%   Layer 1 — Knowledge Base:
%%     Domain rules expressed as rule/2 facts in human-readable form.
%%     Rules describe WHAT scheduling concepts mean, not HOW to compute them.
%%
%%   Layer 2 — Meta-Interpreter (Solver):
%%     A reasoning engine (solve/1) that interprets the knowledge base.
%%     It looks up matching rules and recursively proves sub-goals.
%%     solve_with_trace/2 can produce explanation traces.
%%
%%   Layer 3 — Computation:
%%     All arithmetic is hidden behind compute/1 predicates with
%%     descriptive names. The solver delegates ground-level work here.
%%
%% This separation means:
%%   - Knowledge is declarative and readable
%%   - Reasoning is explicit and traceable
%%   - Implementation details (math) are hidden
%% ============================================================================

:- module(scheduler, [
    check_conflict/6,
    find_free_slots/7,
    find_free_ranges/6,
    find_free_days/7,
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3,
    solve/1,
    solve_with_trace/2
]).

%% ============================================================================
%% Layer 1: Knowledge Base — Human-Readable Scheduling Rules
%% ============================================================================
%%
%% Rules are declared as:  rule(Conclusion, [Condition1, Condition2, ...])
%%
%% The meta-interpreter proves Conclusion by proving every Condition.
%% These rules encode domain knowledge in near-natural-language form.
%% ============================================================================

%% --- Core Overlap Rule ---------------------------------------------------
%% "Two time intervals overlap when each one starts before the other ends."
rule(
    intervals_overlap(interval(Start1, End1), interval(Start2, End2)),
    [ starts_before(Start1, End2),
      starts_before(Start2, End1) ]
).

%% --- Event Conflict Rule -------------------------------------------------
%% "A new event conflicts with an existing event when their intervals overlap."
rule(
    event_conflicts_with(new_event(NS, NE), existing_event(ES, EE)),
    [ intervals_overlap(interval(NS, NE), interval(ES, EE)) ]
).

%% --- Slot Availability Rules ---------------------------------------------
%% "A time slot is available when no existing event overlaps with it."
rule(
    slot_is_available(interval(Start, End), ExistingEvents),
    [ no_event_overlaps_with(interval(Start, End), ExistingEvents) ]
).

%% "A time slot has a conflict when at least one event overlaps with it."
rule(
    slot_has_conflict(interval(Start, End), ExistingEvents),
    [ some_event_overlaps_with(interval(Start, End), ExistingEvents) ]
).

%% --- Valid Candidate Rule ------------------------------------------------
%% "A candidate slot is valid when it fits within the allowed time
%%  bounds and no existing event conflicts with it."
rule(
    valid_candidate_slot(interval(Start, End), Events, bounds(Min, Max)),
    [ fits_within_bounds(interval(Start, End), bounds(Min, Max)),
      slot_is_available(interval(Start, End), Events) ]
).

%% ============================================================================
%% Layer 2: Meta-Interpreter (Solver)
%% ============================================================================
%%
%% The solver is the reasoning engine. It resolves goals by:
%%   1. Recognising trivially true goals
%%   2. Solving conjunctions (lists) left-to-right
%%   3. Handling negation-as-failure
%%   4. Looking up a matching rule and solving its body
%%   5. Delegating ground-level work to compute/1
%% ============================================================================

%% solve(+Goal)
%% Resolve a goal by reasoning over the knowledge base.

% Base case: true always succeeds
solve(true) :- !.

% Empty conjunction
solve([]) :- !.

% Conjunction: solve head, then tail
solve([Goal | Rest]) :- !,
    solve(Goal),
    solve(Rest).

% Negation-as-failure
solve(not(Goal)) :- !,
    \+ solve(Goal).

% Rule resolution: look up a matching rule and solve its body
solve(Goal) :-
    rule(Goal, Body),
    solve(Body).

% Ground computation: delegate to the computation layer
solve(Goal) :-
    compute(Goal).

%% solve_with_trace(+Goal, -Trace)
%% Solve a goal and record which rules / computations were applied.

solve_with_trace(true, []) :- !.

solve_with_trace([], []) :- !.

solve_with_trace([Goal | Rest], Trace) :- !,
    solve_with_trace(Goal, GoalTrace),
    solve_with_trace(Rest, RestTrace),
    append(GoalTrace, RestTrace, Trace).

solve_with_trace(not(Goal), [negation_holds(Goal)]) :-
    \+ solve(Goal), !.

solve_with_trace(Goal, [applied_rule(Goal, Body) | BodyTrace]) :-
    rule(Goal, Body),
    solve_with_trace(Body, BodyTrace).

solve_with_trace(Goal, [computed(Goal)]) :-
    \+ rule(Goal, _),
    compute(Goal).

%% ============================================================================
%% Layer 3: Computation — Hidden Arithmetic
%% ============================================================================
%%
%% All mathematical operations are abstracted behind descriptive names.
%% The solver delegates here; callers never see raw arithmetic.
%% ============================================================================

%% "Time value A is strictly before time value B."
compute(starts_before(A, B)) :-
    number(A), number(B),
    A < B.

%% "No event in the list overlaps with the given interval."
compute(no_event_overlaps_with(interval(Start, End), Events)) :-
    \+ (
        member(event(_, _, SH, SM, EH, EM), Events),
        time_to_minutes(SH, SM, EStart),
        time_to_minutes(EH, EM, EEnd),
        solve(intervals_overlap(interval(Start, End), interval(EStart, EEnd)))
    ).

%% "At least one event in the list overlaps with the given interval."
compute(some_event_overlaps_with(interval(Start, End), Events)) :-
    member(event(_, _, SH, SM, EH, EM), Events),
    time_to_minutes(SH, SM, EStart),
    time_to_minutes(EH, EM, EEnd),
    solve(intervals_overlap(interval(Start, End), interval(EStart, EEnd))),
    !.

%% "The interval fits within the allowed bounds."
compute(fits_within_bounds(interval(Start, End), bounds(MinStart, MaxEnd))) :-
    Start >= MinStart,
    End =< MaxEnd.

%% ============================================================================
%% Time Representation Utilities
%% ============================================================================

%% time_to_minutes(+Hour, +Minute, -TotalMinutes)
%% Converts hour:minute to total minutes from midnight.
time_to_minutes(Hour, Minute, Total) :-
    integer(Hour), Hour >= 0, Hour =< 23,
    integer(Minute), Minute >= 0, Minute =< 59,
    Total is Hour * 60 + Minute.

%% minutes_to_time(+TotalMinutes, -Hour, -Minute)
%% Converts total minutes from midnight back to hour:minute.
minutes_to_time(Total, Hour, Minute) :-
    integer(Total), Total >= 0, Total =< 1439,
    Hour is Total // 60,
    Minute is Total mod 60.

%% ============================================================================
%% Candidate Generation Helper
%% ============================================================================

%% generate_candidate_slots(+MinStart, +MaxEnd, +Duration, +Step, -Starts)
%% Produce all possible start times with the given step granularity.
generate_candidate_slots(MinStart, MaxEnd, Duration, Step, Starts) :-
    MaxStart is MaxEnd - Duration,
    findall(
        Start,
        (   between(0, 1000, N),
            Start is MinStart + N * Step,
            Start =< MaxStart
        ),
        Starts
    ).

%% ============================================================================
%% Public API — Python-Compatible Interface
%% ============================================================================
%%
%% These predicates keep the same signatures called by prolog_service.py.
%% Internally they delegate all reasoning to the meta-interpreter.
%% ============================================================================

%% events_overlap(+NewStart, +NewEnd, +ExistingStart, +ExistingEnd)
%% True when two time intervals (in minutes) overlap.
events_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd) :-
    solve(intervals_overlap(
        interval(NewStart, NewEnd),
        interval(ExistingStart, ExistingEnd)
    )).

%% slot_conflicts_with_events(+Start, +End, +Events)
%% True when the slot overlaps with at least one event.
slot_conflicts_with_events(Start, End, Events) :-
    solve(slot_has_conflict(interval(Start, End), Events)).

%% check_conflict(+NSH, +NSM, +NEH, +NEM, +ExistingEvents, -Conflicts)
%% Find all existing events that conflict with the proposed new event.
%% Returns list of conflict(ID, Title, SH, SM, EH, EM) terms.
check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents, Conflicts) :-
    time_to_minutes(NewStartH, NewStartM, NewStart),
    time_to_minutes(NewEndH, NewEndM, NewEnd),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        (   member(event(ID, Title, SH, SM, EH, EM), ExistingEvents),
            time_to_minutes(SH, SM, ExStart),
            time_to_minutes(EH, EM, ExEnd),
            solve(event_conflicts_with(
                new_event(NewStart, NewEnd),
                existing_event(ExStart, ExEnd)
            ))
        ),
        Conflicts
    ).

%% find_free_slots(+Duration, +Events, +MinSH, +MinSM, +MaxEH, +MaxEM, -FreeSlots)
%% Find all free time slots of the given duration (in minutes).
%% Returns list of slot(SH, SM, EH, EM) terms.
find_free_slots(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeSlots) :-
    time_to_minutes(MinStartH, MinStartM, MinStart),
    time_to_minutes(MaxEndH, MaxEndM, MaxEnd),
    Step = 30,
    generate_candidate_slots(MinStart, MaxEnd, DurationMinutes, Step, CandidateStarts),
    findall(
        slot(SH, SM, EH, EM),
        (   member(SlotStart, CandidateStarts),
            SlotEnd is SlotStart + DurationMinutes,
            solve(valid_candidate_slot(
                interval(SlotStart, SlotEnd),
                Events,
                bounds(MinStart, MaxEnd)
            )),
            minutes_to_time(SlotStart, SH, SM),
            minutes_to_time(SlotEnd, EH, EM)
        ),
        FreeSlots
    ).

%% find_free_ranges(+Events, +MinSH, +MinSM, +MaxEH, +MaxEM, -FreeRanges)
%% Find contiguous free time ranges (gaps between events).
%% Returns list of range(SH, SM, EH, EM) terms.
find_free_ranges(Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeRanges) :-
    time_to_minutes(MinStartH, MinStartM, MinStart),
    time_to_minutes(MaxEndH, MaxEndM, MaxEnd),
    (   Events = []
    ->  FreeRanges = [range(MinStartH, MinStartM, MaxEndH, MaxEndM)]
    ;   sort_events_by_start(Events, SortedEvents),
        find_gaps(SortedEvents, MinStart, MaxEnd, GapsInMinutes),
        convert_gaps_to_ranges(GapsInMinutes, FreeRanges)
    ).

%% find_free_days(+Duration, +EventsByDay, +SH, +SM, +EH, +EM, -FreeDays)
%% Find days where a slot of the given duration can fit.
%% EventsByDay: list of day(Day, Month, Year, Events).
%% Returns: list of day(Day, Month, Year, AvailableSlots).
find_free_days(DurationMinutes, EventsByDay, StartHour, StartMinute, EndHour, EndMinute, FreeDays) :-
    findall(
        day(D, M, Y, Slots),
        (   member(day(D, M, Y, Events), EventsByDay),
            find_free_slots(DurationMinutes, Events, StartHour, StartMinute, EndHour, EndMinute, Slots),
            Slots \= []
        ),
        FreeDays
    ).

%% ============================================================================
%% Internal Helpers — Gap Finding for Free Ranges
%% ============================================================================

sort_events_by_start(Events, Sorted) :-
    map_list_to_pairs(event_start_minutes, Events, Pairs),
    keysort(Pairs, SortedPairs),
    pairs_values(SortedPairs, Sorted).

event_start_minutes(event(_, _, SH, SM, _, _), Minutes) :-
    time_to_minutes(SH, SM, Minutes).

find_gaps([], MinStart, MaxEnd, [gap(MinStart, MaxEnd)]) :-
    MinStart < MaxEnd, !.
find_gaps([], _, _, []).

find_gaps([Event | Rest], MinStart, MaxEnd, Gaps) :-
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
convert_gaps_to_ranges([gap(StartMin, EndMin) | Rest], [range(SH, SM, EH, EM) | RestRanges]) :-
    StartMin < EndMin,
    minutes_to_time(StartMin, SH, SM),
    minutes_to_time(EndMin, EH, EM),
    convert_gaps_to_ranges(Rest, RestRanges).
convert_gaps_to_ranges([gap(StartMin, EndMin) | Rest], RestRanges) :-
    StartMin >= EndMin,
    convert_gaps_to_ranges(Rest, RestRanges).

%% ============================================================================
%% Utility: Simple conflict check between two events (for direct calls)
%% ============================================================================

check_single_conflict(NH, NM, NEH, NEM, EH, EM, EEH, EEM) :-
    time_to_minutes(NH, NM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    time_to_minutes(EH, EM, ExStart),
    time_to_minutes(EEH, EEM, ExEnd),
    solve(intervals_overlap(
        interval(NewStart, NewEnd),
        interval(ExStart, ExEnd)
    )).

%% ============================================================================
%% Example Queries
%% ============================================================================
%%
%% Check conflict:
%%   ?- check_conflict(9, 0, 10, 0, [event(e1, "Meeting", 9, 30, 10, 30)], C).
%%   C = [conflict(e1, "Meeting", 9, 30, 10, 30)]
%%
%% Find free slots:
%%   ?- find_free_slots(60, [event(e1, "M", 9, 0, 10, 0)], 8, 0, 18, 0, S).
%%   S = [slot(8, 0, 9, 0), slot(10, 0, 11, 0), ...]
%%
%% Find free ranges:
%%   ?- find_free_ranges([event(e1, "Meeting", 10, 0, 12, 0)], 8, 0, 18, 0, R).
%%   R = [range(8, 0, 10, 0), range(12, 0, 18, 0)]
%%
%% Solve with explanation trace:
%%   ?- solve_with_trace(
%%        intervals_overlap(interval(540, 600), interval(570, 630)), Trace).
%%   Trace = [applied_rule(...), computed(starts_before(540,630)),
%%            computed(starts_before(570,600))]
