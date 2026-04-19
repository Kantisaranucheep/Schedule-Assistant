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
    check_conflict/6,
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
    demo/1,                        % demo(Goal) — meta-interpreter

    %% --- High-Level Black Box API (KRR Solvers) ---
    handle_add_event/8,            % handle_add_event(SH, SM, EH, EM, Events, Status, Conflicts, Violations)
    handle_suggest_times/7,        % handle_suggest_times(Dur, Events, MinSH, MinSM, MaxEH, MaxEM, Suggestions)
    explain_conflicts/6,           % explain_conflicts(SH, SM, EH, EM, Events, Explanations)

    %% --- Enhanced Meta-Interpreter with Explanation ---
    demo_explain/2,                % demo_explain(Goal, Trace) — prove + reasoning trace

    %% --- Custom Operators (KRR Syntax) ---
    conflicts_with/2,              % event(S1,E1) conflicts_with event(S2,E2)
    is_valid_in/2,                 % slot(SH,SM,EH,EM) is_valid_in context(Events)
    satisfies_all/2,               % slot(SH,SM,EH,EM) satisfies_all constraints

    %% --- Reasoning Metadata ---
    reasoning_metadata/2           % reasoning_metadata(Key, Value) — introspection
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

%% ============================================================================
%% 6. Custom Operators — Readable KRR Syntax
%% ============================================================================
%%
%% Custom operators allow expressing scheduling knowledge in a natural,
%% declarative form close to domain language:
%%
%%   event(540, 600) conflicts_with event(570, 660)
%%   slot(9, 0, 10, 0) is_valid_in context(Events)
%%   slot(9, 0, 10, 0) satisfies_all constraints
%%
%% KRR Principle: Knowledge should be readable and expressible in
%% a form close to natural language. Operators enable this.

:- op(700, xfx, conflicts_with).
:- op(700, xfx, is_valid_in).
:- op(700, xfx, satisfies_all).

%% event(StartMin, EndMin) conflicts_with event(StartMin2, EndMin2)
%% True when two time intervals (in minutes) overlap.
event(S1, E1) conflicts_with event(S2, E2) :-
    intervals_overlap(S1, E1, S2, E2).

%% slot(SH, SM, EH, EM) is_valid_in context(Events)
%% True when placing a slot at this time satisfies ALL scheduling constraints.
slot(SH, SM, EH, EM) is_valid_in context(Events) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    valid_placement(Start, End, Events).

%% slot(SH, SM, EH, EM) satisfies_all constraints
%% True when a slot satisfies all declared constraints (ignoring events).
slot(SH, SM, EH, EM) satisfies_all constraints :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    forall(
        scheduling_fact(constraint(C)),
        satisfies_constraint(C, Start, End, [])
    ).

%% ============================================================================
%% 7. Reasoning Metadata — Introspection About the Reasoning Process
%% ============================================================================
%%
%% Metadata facts describe the reasoning system itself.
%% This enables meta-level queries like "what constraints exist?"
%% or "what strategies does the system support?"
%%
%% KRR Principle: A system should be able to reason about its own knowledge.

:- dynamic reasoning_metadata/2.

reasoning_metadata(system_name, schedule_assistant).
reasoning_metadata(reasoning_type, constraint_based).
reasoning_metadata(supported_action, add_event).
reasoning_metadata(supported_action, suggest_times).
reasoning_metadata(supported_action, explain_conflicts).
reasoning_metadata(constraint_type, hard).
reasoning_metadata(constraint_type, soft).
reasoning_metadata(explanation_supported, true).
reasoning_metadata(meta_interpretation, true).

%% ============================================================================
%% 8. Enhanced Meta-Interpreter with Explanation Trace
%% ============================================================================
%%
%% demo_explain(+Goal, -Trace)
%%
%% Like demo/1 but also returns the reasoning trace — a structured term
%% describing HOW the goal was proved. This is a key KRR feature:
%% the system can explain its own reasoning.
%%
%% Trace is one of:
%%   proved(true)
%%   proved(and(TraceA, TraceB))
%%   proved(or_left(TraceA)) | proved(or_right(TraceB))
%%   proved(negation_as_failure(Goal))
%%   proved(overlap(S1-E1, S2-E2))
%%   proved(valid_placement(all_constraints_satisfied))
%%   proved(constraint(Name, satisfied))
%%   proved(from_rule(Goal, BodyTrace))
%%   proved(from_fact(Goal))
%%   disproved(valid_placement(failed_constraint(C)))

demo_explain(true, proved(true)) :- !.

demo_explain((A, B), proved(and(EA, EB))) :-
    !, demo_explain(A, EA), demo_explain(B, EB).

demo_explain((A ; _B), proved(or_left(EA))) :-
    demo_explain(A, EA), !.
demo_explain((_A ; B), proved(or_right(EB))) :-
    !, demo_explain(B, EB).

demo_explain(\+ A, proved(negation_as_failure(A))) :-
    !, \+ demo(A).

%% Scheduling-specific goals with explanation
demo_explain(intervals_overlap(S1, E1, S2, E2),
    proved(overlap(S1-E1, S2-E2))) :-
    intervals_overlap(S1, E1, S2, E2).

demo_explain(valid_placement(S, E, Evts),
    proved(valid_placement(all_constraints_satisfied))) :-
    valid_placement(S, E, Evts), !.
demo_explain(valid_placement(S, E, Evts),
    disproved(valid_placement(failed_constraint(C)))) :-
    scheduling_fact(constraint(C)),
    \+ satisfies_constraint(C, S, E, Evts), !.

demo_explain(satisfies_constraint(C, S, E, Evts),
    proved(constraint(C, satisfied))) :-
    satisfies_constraint(C, S, E, Evts).

demo_explain(conflict_reason(S1, E1, S2, E2, R),
    proved(conflict_reason(R))) :-
    conflict_reason(S1, E1, S2, E2, R).

%% Prove from declared scheduling rules
demo_explain(Goal, proved(from_rule(Goal, BodyTrace))) :-
    scheduling_rule(Goal, Body),
    demo_explain(Body, BodyTrace).

%% Prove from declared scheduling facts
demo_explain(Goal, proved(from_fact(Goal))) :-
    scheduling_fact(Goal).

%% Arithmetic goals
demo_explain(A < B, proved(A < B)) :- A < B.
demo_explain(A > B, proved(A > B)) :- A > B.
demo_explain(A >= B, proved(A >= B)) :- A >= B.
demo_explain(A =< B, proved(A =< B)) :- A =< B.

%% ============================================================================
%% 9. High-Level Black Box API — Autonomous Reasoning Solvers
%% ============================================================================
%%
%% These predicates implement the "Black Box" pattern for KRR:
%%
%%   Python says: "User wants to add this event. Here's all the data."
%%   Prolog reasons: checks constraints, detects conflicts, generates explanations
%%   Prolog returns: a complete decision — Python doesnt know HOW it was decided.
%%
%% This is the core of KRR:
%%   - Knowledge (facts + rules) is in Prolog
%%   - Reasoning (inference + constraint satisfaction) is in Prolog
%%   - Python is just the messenger
%%
%% KRR Keywords demonstrated:
%%   Solver, Facts, Rules, Constraints, Meta-interpreter, Metadata

%% ---------------------------------------------------------------------------
%% handle_add_event(+SH, +SM, +EH, +EM, +Events, -Status, -Conflicts, -Violations)
%% ---------------------------------------------------------------------------
%%
%% Autonomous solver for "Can I add this event?"
%%
%% Input:
%%   SH, SM, EH, EM  — proposed event start/end time (hours, minutes)
%%   Events           — list of existing events: [event(ID, Title, SH, SM, EH, EM), ...]
%%
%% Output (separate variables for reliable pyswip interop):
%%   Status      — atom: ok | conflict | invalid
%%   Conflicts   — list of conflict(ID, Title, SH, SM, EH, EM)  (empty if ok/invalid)
%%   Violations  — list of constraint name atoms                  (empty if ok/conflict)
%%
%% The solver internally:
%%   1. Validates hard constraints (positive_duration, within_bounds)
%%   2. Checks for overlaps with existing events
%%   3. Classifies the result and returns structured data
%%
%% Python never calls check_conflict, valid_placement, or satisfies_constraint
%% directly — the solver handles everything.

handle_add_event(SH, SM, EH, EM, Events, Status, Conflicts, Violations) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    %% Phase 1: Validate basic constraints (everything except overlap)
    findall(
        C,
        (   scheduling_fact(constraint(C)),
            C \= no_overlap,
            \+ satisfies_constraint(C, Start, End, Events)
        ),
        ViolationList
    ),
    (   ViolationList \= []
    ->  Status = invalid, Conflicts = [], Violations = ViolationList
    ;   %% Phase 2: Check for conflicts with existing events
        findall(
            conflict(ID, Title, ESH, ESM, EEH, EEM),
            (
                member(event(ID, Title, ESH, ESM, EEH, EEM), Events),
                time_to_minutes(ESH, ESM, ExStart),
                time_to_minutes(EEH, EEM, ExEnd),
                intervals_overlap(Start, End, ExStart, ExEnd)
            ),
            ConflictList
        ),
        (   ConflictList = []
        ->  Status = ok, Conflicts = [], Violations = []
        ;   Status = conflict, Conflicts = ConflictList, Violations = []
        )
    ).

%% ---------------------------------------------------------------------------
%% handle_suggest_times(+Duration, +Events, +MinSH, +MinSM, +MaxEH, +MaxEM, -Suggestions)
%% ---------------------------------------------------------------------------
%%
%% Autonomous solver for "What are the best times for an event?"
%%
%% Input:
%%   Duration          — required duration in minutes
%%   Events            — existing events on that day
%%   MinSH..MaxEM      — time bounds (earliest start, latest end)
%%
%% Output (Suggestions):
%%   List of suggestion(SH, SM, EH, EM, Score, Reason)
%%   Sorted by Score ascending (lower = better).
%%   Up to 5 suggestions returned.
%%
%% Reason is one of:
%%   ideal_time, good_buffer, outside_preferred_hours,
%%   tight_buffer, heavy_day, acceptable
%%
%% The solver internally:
%%   1. Generates all candidate slots (using granularity from knowledge base)
%%   2. Filters by constraint satisfaction (valid_placement)
%%   3. Scores each slot using soft constraint reasoning
%%   4. Ranks and returns top suggestions with explanations

handle_suggest_times(Duration, Events, MinSH, MinSM, MaxEH, MaxEM, Suggestions) :-
    time_to_minutes(MinSH, MinSM, MinStart),
    time_to_minutes(MaxEH, MaxEM, MaxEnd),
    scheduling_fact(slot_granularity(Step)),
    MaxSlotStart is MaxEnd - Duration,
    findall(
        suggestion(Score, SH, SM, EH, EM, Reason),
        (
            between(0, 1000, N),
            SlotStart is MinStart + N * Step,
            SlotStart =< MaxSlotStart,
            SlotEnd is SlotStart + Duration,
            SlotEnd =< MaxEnd,
            valid_placement(SlotStart, SlotEnd, Events),
            score_time_slot(SlotStart, SlotEnd, Events, Score, Reason),
            minutes_to_time(SlotStart, SH, SM),
            minutes_to_time(SlotEnd, EH, EM)
        ),
        AllSuggestions
    ),
    sort(AllSuggestions, Sorted),
    take_top_n(5, Sorted, Suggestions).

%% ---------------------------------------------------------------------------
%% explain_conflicts(+SH, +SM, +EH, +EM, +Events, -Explanations)
%% ---------------------------------------------------------------------------
%%
%% Explain WHY a proposed time has conflicts — returns structured explanations.
%%
%% Output (Explanations):
%%   List of explanation(Type, Detail)
%%   Type is: overlap | constraint_violation
%%   Detail provides specific information about the issue.

explain_conflicts(SH, SM, EH, EM, Events, Explanations) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End),
    findall(
        explanation(Type, Detail),
        (
            %% Check overlap conflicts
            (
                member(event(ID, Title, ESH, ESM, EEH, EEM), Events),
                time_to_minutes(ESH, ESM, ExStart),
                time_to_minutes(EEH, EEM, ExEnd),
                intervals_overlap(Start, End, ExStart, ExEnd),
                Type = overlap,
                Detail = overlaps_with(ID, Title, ESH, ESM, EEH, EEM)
            )
        ;
            %% Check constraint violations
            (
                scheduling_fact(constraint(C)),
                C \= no_overlap,
                \+ satisfies_constraint(C, Start, End, Events),
                Type = constraint_violation,
                Detail = violates(C)
            )
        ),
        Explanations
    ).

%% ============================================================================
%% 10. Slot Scoring & Classification — Soft Constraint Reasoning for Solver
%% ============================================================================
%%
%% These predicates score candidate time slots based on soft constraints.
%% They are used internally by handle_suggest_times but can also be
%% queried directly for analysis.

%% score_time_slot(+Start, +End, +Events, -Score, -Reason)
%% Score a candidate slot — lower is better.
score_time_slot(Start, End, Events, Score, Reason) :-
    slot_buffer_cost(Start, End, Events, BufCost),
    slot_preferred_time_cost(Start, PrefCost),
    slot_daily_load_cost(Events, LoadCost),
    Score is BufCost + PrefCost + LoadCost,
    classify_slot_quality(Score, BufCost, PrefCost, LoadCost, Reason).

%% Buffer proximity cost — penalty for events too close together
slot_buffer_cost(Start, End, Events, Cost) :-
    findall(1, (
        member(event(_, _, ESH, ESM, EEH, EEM), Events),
        time_to_minutes(ESH, ESM, EStart),
        time_to_minutes(EEH, EEM, EEnd),
        (   (EEnd > Start - 15, EEnd =< Start)
        ;   (EStart >= End, EStart < End + 15)
        )
    ), CloseEvents),
    length(CloseEvents, N),
    Cost is N * 3.

%% Preferred time window cost — prefer 9:00-17:00
slot_preferred_time_cost(Start, Cost) :-
    (   Start >= 540, Start =< 1020
    ->  Cost = 0
    ;   Diff is abs(Start - 780),
        Cost is min(Diff // 30, 10)
    ).

%% Daily load cost — penalty for overloaded days
slot_daily_load_cost(Events, Cost) :-
    length(Events, NumEvents),
    (   NumEvents > 8
    ->  Cost is (NumEvents - 8) * 5
    ;   NumEvents > 6
    ->  Cost is (NumEvents - 6) * 2
    ;   Cost = 0
    ).

%% classify_slot_quality(+Total, +BufCost, +PrefCost, +LoadCost, -Reason)
%% Produce a human-readable reason for the slots score.
classify_slot_quality(Total, _BufCost, _PrefCost, _LoadCost, ideal_time) :-
    Total =:= 0, !.
classify_slot_quality(_Total, BufCost, PrefCost, _LoadCost, suboptimal_time_and_tight_buffer) :-
    PrefCost > 0, BufCost > 0, !.
classify_slot_quality(_Total, _BufCost, PrefCost, _LoadCost, outside_preferred_hours) :-
    PrefCost > 0, !.
classify_slot_quality(_Total, BufCost, _PrefCost, _LoadCost, tight_buffer) :-
    BufCost > 0, !.
classify_slot_quality(_Total, _BufCost, _PrefCost, LoadCost, heavy_day) :-
    LoadCost > 0, !.
classify_slot_quality(_, _, _, _, acceptable).

%% take_top_n(+N, +List, -TopN) — take first N elements
take_top_n(_, [], []) :- !.
take_top_n(0, _, []) :- !.
take_top_n(N, [H|T], [H|Rest]) :-
    N > 0, N1 is N - 1,
    take_top_n(N1, T, Rest).
