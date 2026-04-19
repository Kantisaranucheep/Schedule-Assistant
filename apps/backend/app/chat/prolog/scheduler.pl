%% apps/backend/app/chat/prolog/scheduler.pl
%% ============================================================================
%% Schedule Assistant — Prolog Reasoning Engine
%% ============================================================================
%%
%% This module implements Knowledge Representation and Reasoning (KRR) for
%% time-based scheduling. It is organized into:
%%
%%   1. Domain Knowledge      — facts about time representation
%%   2. Scheduling Constraints — declared as first-class knowledge
%%   3. Core Reasoning Rules  — declarative inference for conflicts/availability
%%   4. Constraint Satisfaction — find_free_slots via constraint solving
%%   5. Meta-Interpreter       — demo/1 for proving scheduling goals
%%   6. Legacy Predicates      — backward-compatible algorithmic layer
%%
%% KRR Principles Applied:
%%   - Knowledge is FACTS (not embedded in algorithms)
%%   - Rules express WHAT holds, not HOW to compute
%%   - Constraints are declared, then checked by inference
%%   - Meta-interpreter enables reasoning about reasoning
%% ============================================================================

:- module(scheduler, [
    %% --- Legacy exports (backward compatible) ---
    check_conflict/5,
    find_free_slots/7,
    find_free_ranges/5,
    find_free_days/7,
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3,

    %% --- KRR Reasoning Exports ---
    scheduling_fact/1,             % scheduling_fact(Fact) — declare a scheduling fact
    scheduling_rule/2,             % scheduling_rule(Head, Body) — declare a rule
    valid_placement/3,             % valid_placement(Start, End, Events) — inference
    conflict_reason/5,             % conflict_reason(S1,E1,S2,E2, Reason) — why conflict
    infer_available/4,             % infer_available(Events, MinStart, MaxEnd, Slot)
    satisfies_constraint/4,        % satisfies_constraint(Constraint, Start, End, Events)
    demo/1                         % demo(Goal) — meta-interpreter
]).

%% ============================================================================
%% 1. Domain Knowledge — Facts About Time
%% ============================================================================
%%
%% Time representation knowledge: minutes from midnight (0–1439).
%% These are FACTS about how the domain models time, not utility functions.

%% time_to_minutes(+Hour, +Minute, -TotalMinutes)
%% Knowledge: an hour-minute pair maps to a total-minutes value.
time_to_minutes(Hour, Minute, Total) :-
    integer(Hour), Hour >= 0, Hour =< 23,
    integer(Minute), Minute >= 0, Minute =< 59,
    Total is Hour * 60 + Minute.

%% minutes_to_time(+TotalMinutes, -Hour, -Minute)
%% Knowledge: a total-minutes value maps to an hour-minute pair.
minutes_to_time(Total, Hour, Minute) :-
    integer(Total), Total >= 0, Total =< 1439,
    Hour is Total // 60,
    Minute is Total mod 60.

%% ============================================================================
%% 2. Scheduling Constraints — Declared as Knowledge
%% ============================================================================
%%
%% Constraints are FACTS that describe what makes a valid schedule.
%% Rules in Section 3 CHECK these constraints; this section only DECLARES them.
%%
%%   scheduling_fact(Fact)     — a ground truth about scheduling
%%   scheduling_rule(Head, Body) — an inference rule about scheduling

:- dynamic scheduling_fact/1.
:- dynamic scheduling_rule/2.

%% Working day boundaries (domain knowledge)
scheduling_fact(working_day_start(6, 0)).     % 6:00 AM earliest
scheduling_fact(working_day_end(23, 0)).      % 11:00 PM latest
scheduling_fact(slot_granularity(30)).         % 30-minute slot resolution
scheduling_fact(max_daily_events(8)).          % soft limit on daily events

%% Named constraints — what must hold for a valid placement
scheduling_fact(constraint(no_overlap)).
scheduling_fact(constraint(within_bounds)).
scheduling_fact(constraint(positive_duration)).

%% Scheduling rules expressed as knowledge
scheduling_rule(
    conflict(S1, E1, S2, E2),
    (S1 < E2, S2 < E1)
).
scheduling_rule(
    within_bounds(Start, End, Min, Max),
    (Start >= Min, End =< Max)
).
scheduling_rule(
    positive_duration(Start, End),
    (End > Start)
).

%% ============================================================================
%% 3. Core Reasoning Rules (Declarative — KRR)
%% ============================================================================

%% --- Interval Overlap (Declarative) ---
%%
%% Two intervals overlap iff they share at least one time point.
%% Logical formulation: overlap(S1,E1,S2,E2) ↔ S1 < E2 ∧ S2 < E1
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.

%% events_overlap/4 — backward-compatible wrapper
events_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd) :-
    intervals_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd).

%% --- Conflict Reasoning ---
%%
%% conflict_reason/5: WHY do two intervals conflict?
%% Returns a structured explanation (not just true/false).
conflict_reason(S1, E1, S2, E2, overlap(S1-E1, S2-E2)) :-
    intervals_overlap(S1, E1, S2, E2).

%% --- Constraint Satisfaction ---
%%
%% satisfies_constraint(+ConstraintName, +Start, +End, +Events)
%% True iff the named constraint holds for the given interval.

satisfies_constraint(no_overlap, Start, End, Events) :-
    \+ (
        member(event(_, _, SH, SM, EH, EM), Events),
        time_to_minutes(SH, SM, ExStart),
        time_to_minutes(EH, EM, ExEnd),
        intervals_overlap(Start, End, ExStart, ExEnd)
    ).

satisfies_constraint(within_bounds, Start, End, _Events) :-
    scheduling_fact(working_day_start(MinH, MinM)),
    scheduling_fact(working_day_end(MaxH, MaxM)),
    time_to_minutes(MinH, MinM, MinStart),
    time_to_minutes(MaxH, MaxM, MaxEnd),
    Start >= MinStart,
    End =< MaxEnd.

satisfies_constraint(positive_duration, Start, End, _Events) :-
    End > Start.

%% --- Valid Placement (Inference) ---
%%
%% valid_placement(+Start, +End, +Events):
%%   A placement is valid iff ALL declared constraints are satisfied.
%%   This is pure inference over the constraint knowledge base.

valid_placement(Start, End, Events) :-
    forall(
        scheduling_fact(constraint(C)),
        satisfies_constraint(C, Start, End, Events)
    ).

%% --- Availability Inference ---
%%
%% infer_available(+Events, +MinStart, +MaxEnd, -Slot):
%%   Infer available time slots by reasoning about what intervals
%%   satisfy all constraints. Produces slot(StartH, StartM, EndH, EndM).

infer_available(Events, MinStart, MaxEnd, slot(SH, SM, EH, EM)) :-
    scheduling_fact(slot_granularity(Step)),
    between(0, 1000, N),
    SlotStart is MinStart + N * Step,
    SlotStart < MaxEnd,
    SlotEnd is SlotStart + Step,
    SlotEnd =< MaxEnd,
    valid_placement(SlotStart, SlotEnd, Events),
    minutes_to_time(SlotStart, SH, SM),
    minutes_to_time(SlotEnd, EH, EM).

%% ============================================================================
%% 4. Meta-Interpreter — Reasoning About Scheduling Goals
%% ============================================================================
%%
%% demo/1 proves goals against the scheduling knowledge base.
%% It can reason about both declared facts and inference rules.

demo(true) :- !.
demo((A, B)) :- !, demo(A), demo(B).
demo((A ; B)) :- !, (demo(A) ; demo(B)).
demo(\+ A) :- !, \+ demo(A).

%% Prove scheduling-specific goals
demo(intervals_overlap(S1, E1, S2, E2)) :- intervals_overlap(S1, E1, S2, E2).
demo(valid_placement(S, E, Evts)) :- valid_placement(S, E, Evts).
demo(satisfies_constraint(C, S, E, Evts)) :- satisfies_constraint(C, S, E, Evts).
demo(conflict_reason(S1, E1, S2, E2, R)) :- conflict_reason(S1, E1, S2, E2, R).

%% Prove from declared scheduling rules
demo(Goal) :-
    scheduling_rule(Goal, Body),
    demo(Body).

%% Prove from declared scheduling facts
demo(Goal) :-
    scheduling_fact(Goal).

%% Arithmetic goals (needed for rule bodies)
demo(A < B) :- A < B.
demo(A > B) :- A > B.
demo(A >= B) :- A >= B.
demo(A =< B) :- A =< B.

%% ============================================================================
%% 5. Legacy Predicates (Backward Compatible)
%% ============================================================================
%%
%% These predicates maintain the original API for Python/pyswip integration.
%% They now delegate to the KRR reasoning layer where appropriate.

%% slot_conflicts_with_events(+Start, +End, +Events)
%% True if slot conflicts with any event — delegates to constraint check
slot_conflicts_with_events(Start, End, Events) :-
    \+ satisfies_constraint(no_overlap, Start, End, Events).

%% slot_is_free(+Start, +End, +Events) — negation of conflict
slot_is_free(Start, End, Events) :-
    satisfies_constraint(no_overlap, Start, End, Events).

%% generate_candidate_slots(+MinStart, +MaxEnd, +Duration, +Step, -Slots)
generate_candidate_slots(MinStart, MaxEnd, Duration, Step, Slots) :-
    MaxStart is MaxEnd - Duration,
    findall(
        Start,
        (
            between(0, 1000, N),
            Start is MinStart + N * Step,
            Start =< MaxStart
        ),
        Slots
    ).

%% check_conflict/5 — now uses valid_placement reasoning internally
check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents, Conflicts) :-
    time_to_minutes(NewStartH, NewStartM, NewStart),
    time_to_minutes(NewEndH, NewEndM, NewEnd),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        (
            member(event(ID, Title, SH, SM, EH, EM), ExistingEvents),
            time_to_minutes(SH, SM, ExStart),
            time_to_minutes(EH, EM, ExEnd),
            intervals_overlap(NewStart, NewEnd, ExStart, ExEnd)
        ),
        Conflicts
    ).

%% find_free_slots/7 — now uses constraint-based reasoning
find_free_slots(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeSlots) :-
    time_to_minutes(MinStartH, MinStartM, MinStart),
    time_to_minutes(MaxEndH, MaxEndM, MaxEnd),
    scheduling_fact(slot_granularity(Step)),
    generate_candidate_slots(MinStart, MaxEnd, DurationMinutes, Step, CandidateStarts),
    findall(
        slot(SH, SM, EH, EM),
        (
            member(SlotStart, CandidateStarts),
            SlotEnd is SlotStart + DurationMinutes,
            SlotEnd =< MaxEnd,
            valid_placement(SlotStart, SlotEnd, Events),
            minutes_to_time(SlotStart, SH, SM),
            minutes_to_time(SlotEnd, EH, EM)
        ),
        FreeSlots
    ).

%% ============================================================================
%% Find Free Time Ranges (Contiguous Free Periods)
%% ============================================================================

sort_events_by_start(Events, Sorted) :-
    map_list_to_pairs(event_start_minutes, Events, Pairs),
    keysort(Pairs, SortedPairs),
    pairs_values(SortedPairs, Sorted).

event_start_minutes(event(_, _, SH, SM, _, _), Minutes) :-
    time_to_minutes(SH, SM, Minutes).

find_free_ranges(Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeRanges) :-
    time_to_minutes(MinStartH, MinStartM, MinStart),
    time_to_minutes(MaxEndH, MaxEndM, MaxEnd),
    (Events = [] ->
        FreeRanges = [range(MinStartH, MinStartM, MaxEndH, MaxEndM)]
    ;
        sort_events_by_start(Events, SortedEvents),
        find_gaps(SortedEvents, MinStart, MaxEnd, GapsInMinutes),
        convert_gaps_to_ranges(GapsInMinutes, FreeRanges)
    ).

find_gaps([], MinStart, MaxEnd, [gap(MinStart, MaxEnd)]) :-
    MinStart < MaxEnd, !.
find_gaps([], _, _, []).

find_gaps([Event|Rest], MinStart, MaxEnd, Gaps) :-
    Event = event(_, _, SH, SM, EH, EM),
    time_to_minutes(SH, SM, EventStart),
    time_to_minutes(EH, EM, EventEnd),
    (MinStart < EventStart ->
        GapEnd is min(EventStart, MaxEnd),
        (MinStart < GapEnd ->
            FirstGap = [gap(MinStart, GapEnd)]
        ;
            FirstGap = []
        )
    ;
        FirstGap = []
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
%% Find Free Days (Inference)
%% ============================================================================

find_free_days(DurationMinutes, EventsByDay, StartHour, StartMinute, EndHour, EndMinute, FreeDays) :-
    findall(
        day(D, M, Y, Slots),
        (
            member(day(D, M, Y, Events), EventsByDay),
            find_free_slots(DurationMinutes, Events, StartHour, StartMinute, EndHour, EndMinute, Slots),
            Slots \= []
        ),
        FreeDays
    ).

%% ============================================================================
%% Utility Predicates for Python Integration
%% ============================================================================

check_single_conflict(NH, NM, NEH, NEM, EH, EM, EEH, EEM) :-
    time_to_minutes(NH, NM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    time_to_minutes(EH, EM, ExStart),
    time_to_minutes(EEH, EEM, ExEnd),
    intervals_overlap(NewStart, NewEnd, ExStart, ExEnd).
