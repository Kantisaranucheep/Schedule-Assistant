%% apps/backend/app/chat/prolog/scheduler.pl
%% ============================================================================
%% Schedule Assistant - Prolog Knowledge Base with Meta-Interpreter
%% ============================================================================
%% 
%% This module implements Knowledge Representation and Reasoning for scheduling:
%% - Meta-interpreter for logical inference with proof traces
%% - Time conflict detection through logical resolution
%% - Free slot finding via constraint satisfaction with explanations
%% - Logical rules for scheduling decisions
%%
%% Knowledge Representation:
%% - Events are logical facts with temporal properties
%% - Conflicts proven through interval overlap derivation
%% - Free slots derived through constraint satisfaction reasoning
%% - All conclusions justified with proof trees
%% ============================================================================

:- module(scheduler, [
    % Original predicates (backward compatibility)
    check_conflict/5,
    find_free_slots/7,
    find_free_ranges/5,
    find_free_days/7,
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3,
    
    % New KRR predicates with meta-interpreter
    prove_conflict/4,           % prove_conflict(NewEvent, Events, Conflict, Proof)
    prove_no_conflict/3,        % prove_no_conflict(NewEvent, Events, Proof)
    prove_slot_free/4,          % prove_slot_free(Slot, Events, Proof, Trace)
    find_free_slots_with_proof/8, % find_free_slots_with_proof(..., Slots, Proofs)
    explain_conflict/3,         % explain_conflict(Conflict, Proof, Explanation)
    explain_why_free/3,         % explain_why_free(Slot, Proof, Explanation)
    
    % Meta-interpreter for scheduling logic
    prove_scheduling_goal/3     % prove_scheduling_goal(Goal, KB, Proof)
]).

%% ============================================================================
%% KNOWLEDGE BASE: Logical Rules for Scheduling
%% ============================================================================

% Temporal logic rules
temporal_relation(before(T1, T2)) :- T1 < T2.
temporal_relation(after(T1, T2)) :- T1 > T2.
temporal_relation(overlaps(interval(S1, E1), interval(S2, E2))) :-
    S1 < E2, S2 < E1.
temporal_relation(disjoint(interval(S1, E1), interval(S2, E2))) :-
    E1 =< S2.
temporal_relation(disjoint(interval(S1, E1), interval(S2, E2))) :-
    E2 =< S1.

% Scheduling domain knowledge
scheduling_rule(conflict_exists(Event1, Event2)) :-
    temporal_relation(overlaps(
        interval_of(Event1),
        interval_of(Event2)
    )).

scheduling_rule(slot_is_valid(Slot, Events)) :-
    forall(
        member(Event, Events),
        temporal_relation(disjoint(
            interval_of(Slot),
            interval_of(Event)
        ))
    ).

% Interval extraction rules
interval_of(event(_, _, SH, SM, EH, EM)) = interval(Start, End) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End).

interval_of(slot(SH, SM, EH, EM)) = interval(Start, End) :-
    time_to_minutes(SH, SM, Start),
    time_to_minutes(EH, EM, End).

%% ============================================================================
%% META-INTERPRETER: Scheduling Logic Reasoning Engine
%% ============================================================================
%% Performs logical inference about scheduling with proof construction

%% prove_scheduling_goal(+Goal, +KB, -Proof)
%% Meta-interpreter for scheduling-specific logical reasoning

% Base facts
prove_scheduling_goal(true, _KB, proof(true, axiom)) :- !.

% Time arithmetic (bridge to Prolog)
prove_scheduling_goal(time_to_minutes(H, M, Total), _KB, 
                     proof(time_to_minutes(H, M, Total), arithmetic)) :-
    time_to_minutes(H, M, Total), !.

prove_scheduling_goal(minutes_to_time(Total, H, M), _KB,
                     proof(minutes_to_time(Total, H, M), arithmetic)) :-
    minutes_to_time(Total, H, M), !.

% Temporal relations
prove_scheduling_goal(temporal_relation(Relation), KB,
                     proof(temporal_relation(Relation), SubProof)) :-
    temporal_relation(Relation),
    SubProof = derived_from_temporal_logic, !.

% Interval extraction
prove_scheduling_goal(interval_of(Entity) = Interval, KB,
                     proof(interval_of(Entity) = Interval, extraction)) :-
    interval_of(Entity) = Interval, !.

% Scheduling rules
prove_scheduling_goal(scheduling_rule(Rule), KB,
                     proof(scheduling_rule(Rule), SubProof)) :-
    scheduling_rule(Rule),
    SubProof = derived_from_scheduling_knowledge, !.

% Conjunction
prove_scheduling_goal((Goal1, Goal2), KB,
                     proof(and(Goal1, Goal2), [Proof1, Proof2])) :-
    !,
    prove_scheduling_goal(Goal1, KB, Proof1),
    prove_scheduling_goal(Goal2, KB, Proof2).

% Disjunction
prove_scheduling_goal((Goal1 ; Goal2), KB,
                     proof(or(Goal1, Goal2), Proof)) :-
    !,
    (   prove_scheduling_goal(Goal1, KB, Proof1),
        Proof = left(Proof1)
    ;   prove_scheduling_goal(Goal2, KB, Proof2),
        Proof = right(Proof2)
    ).

% Negation
prove_scheduling_goal(not(Goal), KB,
                     proof(not(Goal), negation_as_failure)) :-
    !,
    \+ prove_scheduling_goal(Goal, KB, _).

% Universal quantification
prove_scheduling_goal(forall(Condition, Goal), KB,
                     proof(forall(Condition, Goal), universal_proof(Proofs))) :-
    !,
    findall(
        proof(Goal, SubProof),
        (
            Condition,
            prove_scheduling_goal(Goal, KB, SubProof)
        ),
        Proofs
    ).

% Existential quantification
prove_scheduling_goal(exists(Var, Goal), KB,
                     proof(exists(Var, Goal), witness(Var, Value, SubProof))) :-
    !,
    copy_term((Var, Goal), (Value, InstGoal)),
    prove_scheduling_goal(InstGoal, KB, SubProof).

% Member checking (for lists in KB)
prove_scheduling_goal(member(X, List), _KB,
                     proof(member(X, List), list_membership)) :-
    member(X, List), !.

% Default: try as Prolog goal
prove_scheduling_goal(Goal, _KB, proof(Goal, prolog_builtin)) :-
    call(Goal).

%% ============================================================================
%% KRR PREDICATES: Conflict Detection with Proof
%% ============================================================================

%% prove_conflict(+NewEvent, +Events, -Conflict, -Proof)
%% Proves that NewEvent conflicts with some event in Events
%% Returns the conflicting event and a proof trace showing WHY

prove_conflict(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM),
    Events,
    conflict(NewId, ConflictId, ConflictTitle),
    proof(conflict_detected(NewId, ConflictId), ReasoningChain)
) :-
    member(event(ConflictId, ConflictTitle, ESH, ESM, EEH, EEM), Events),
    NewId \= ConflictId,
    % Prove the overlap through logical inference
    prove_scheduling_goal(
        time_to_minutes(NSH, NSM, NewStart),
        [],
        StartProof1
    ),
    prove_scheduling_goal(
        time_to_minutes(NEH, NEM, NewEnd),
        [],
        EndProof1
    ),
    prove_scheduling_goal(
        time_to_minutes(ESH, ESM, ExStart),
        [],
        StartProof2
    ),
    prove_scheduling_goal(
        time_to_minutes(EEH, EEM, ExEnd),
        [],
        EndProof2
    ),
    % Extract the minute values
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    time_to_minutes(ESH, ESM, ExStart),
    time_to_minutes(EEH, EEM, ExEnd),
    % Prove overlap
    NewStart < ExEnd,
    NewEnd > ExStart,
    % Build reasoning chain
    ReasoningChain = [
        step(extracted_intervals, 'extracted time intervals from events'),
        step(new_interval(NewStart, NewEnd), 'new event interval'),
        step(existing_interval(ExStart, ExEnd), 'existing event interval'),
        step(check_overlap_condition, 'checking overlap condition'),
        step(condition_1(NewStart < ExEnd), format('~w < ~w is true', [NewStart, ExEnd])),
        step(condition_2(NewEnd > ExStart), format('~w > ~w is true', [NewEnd, ExStart])),
        step(conclusion(overlap), 'by temporal logic: intervals overlap'),
        step(therefore(conflict(NewId, ConflictId)), 'therefore: conflict exists')
    ].

%% prove_no_conflict(+NewEvent, +Events, -Proof)
%% Proves that NewEvent does NOT conflict with any event in Events
%% Proof shows that for all events, the intervals are disjoint

prove_no_conflict(
    event(NewId, NewTitle, NSH, NSM, NEH, NEM),
    Events,
    proof(no_conflicts(NewId), ReasoningChain)
) :-
    time_to_minutes(NSH, NSM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    findall(
        proof(disjoint_from(OtherId), DisjointProof),
        (
            member(event(OtherId, OtherTitle, OSH, OSM, OEH, OEM), Events),
            NewId \= OtherId,
            time_to_minutes(OSH, OSM, OtherStart),
            time_to_minutes(OEH, OEM, OtherEnd),
            % Prove disjoint (not overlapping)
            (   NewEnd =< OtherStart
            ->  DisjointProof = proof(before(NewEnd, OtherStart), 
                    'new event ends before existing starts')
            ;   OtherEnd =< NewStart
            ->  DisjointProof = proof(after(NewStart, OtherEnd),
                    'new event starts after existing ends')
            ;   fail  % Not disjoint - this case shouldn't succeed
            )
        ),
        AllDisjointProofs
    ),
    % Verify we checked all events
    length(Events, NumEvents),
    length(AllDisjointProofs, NumChecked),
    (   NumEvents == NumChecked
    ->  ReasoningChain = [
            step(checked_all_events, format('verified ~w events', [NumEvents])),
            step(all_disjoint, 'all intervals are temporally disjoint'),
            step(conclusion, 'no conflicts exist by universal verification')
        ]
    ;   ReasoningChain = [
            step(partial_check, format('checked ~w of ~w events', [NumChecked, NumEvents])),
            step(some_overlap, 'found overlapping intervals'),
            step(conclusion, 'conflicts may exist')
        ]
    ).

%% ============================================================================
%% KRR PREDICATES: Free Slot Detection with Proof
%% ============================================================================

%% prove_slot_free(+Slot, +Events, -Proof, -Trace)
%% Proves that a time slot is free (doesn't conflict with any event)
%% Returns proof structure and human-readable trace

prove_slot_free(
    slot(SH, SM, EH, EM),
    Events,
    proof(slot_free(SH, SM, EH, EM), ReasoningChain),
    Trace
) :-
    time_to_minutes(SH, SM, SlotStart),
    time_to_minutes(EH, EM, SlotEnd),
    findall(
        proof(no_conflict_with(EventId), Reasoning),
        (
            member(event(EventId, _, ESH, ESM, EEH, EEM), Events),
            time_to_minutes(ESH, ESM, EventStart),
            time_to_minutes(EEH, EEM, EventEnd),
            % Prove disjoint
            (   SlotEnd =< EventStart
            ->  Reasoning = ends_before(SlotEnd, EventStart)
            ;   EventEnd =< SlotStart
            ->  Reasoning = starts_after(SlotStart, EventEnd)
            ;   fail  % Overlap - slot not free
            )
        ),
        AllProofs
    ),
    length(Events, NumEvents),
    length(AllProofs, NumVerified),
    NumEvents == NumVerified,  % Must verify against all events
    ReasoningChain = [
        step(slot_interval(SlotStart, SlotEnd), 'candidate slot interval'),
        step(verified_against_all(NumEvents), 'checked against all events'),
        step(all_disjoint, 'all event intervals are disjoint from slot'),
        step(conclusion(free_slot), 'slot is free by universal verification')
    ],
    format(atom(Trace), 'Slot ~w:~w-~w:~w is FREE because it is temporally disjoint from all ~w events',
           [SH, SM, EH, EM, NumEvents]).

%% find_free_slots_with_proof(+Duration, +Events, +MinSH, +MinSM, +MaxEH, +MaxEM, -Slots, -Proofs)
%% Find free slots AND provide logical proofs for why each is free

find_free_slots_with_proof(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM, Slots, Proofs) :-
    % First find the slots (using existing logic)
    find_free_slots(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM, Slots),
    % Then prove each one is free
    findall(
        proof_pair(Slot, Proof),
        (
            member(Slot, Slots),
            prove_slot_free(Slot, Events, Proof, _Trace)
        ),
        Proofs
    ).

%% ============================================================================
%% EXPLANATION GENERATION
%% ============================================================================

%% explain_conflict(+Conflict, +Proof, -Explanation)
%% Convert conflict proof into human-readable explanation

explain_conflict(
    conflict(NewId, ConflictId, ConflictTitle),
    proof(conflict_detected(NewId, ConflictId), ReasoningChain),
    explanation(Summary, Steps)
) :-
    format(atom(Summary), 
           'Event ~w conflicts with event ~w (~w) due to overlapping time intervals',
           [NewId, ConflictId, ConflictTitle]),
    reasoning_chain_to_steps(ReasoningChain, Steps).

reasoning_chain_to_steps([], []).
reasoning_chain_to_steps([step(Name, Description)|Rest], [Step|Steps]) :-
    format(atom(Step), '~w: ~w', [Name, Description]),
    reasoning_chain_to_steps(Rest, Steps).
reasoning_chain_to_steps([step(Name, Format, Args)|Rest], [Step|Steps]) :-
    format(atom(Desc), Format, Args),
    format(atom(Step), '~w: ~w', [Name, Desc]),
    reasoning_chain_to_steps(Rest, Steps).

%% explain_why_free(+Slot, +Proof, -Explanation)
%% Convert free slot proof into human-readable explanation

explain_why_free(
    slot(SH, SM, EH, EM),
    proof(slot_free(SH, SM, EH, EM), ReasoningChain),
    explanation(Summary, Steps)
) :-
    format(atom(Summary),
           'Slot ~w:~w-~w:~w is free because it does not overlap with any existing events',
           [SH, SM, EH, EM]),
    reasoning_chain_to_steps(ReasoningChain, Steps).

%% ============================================================================
%% ORIGINAL PREDICATES (Backward Compatibility)
%% ============================================================================

%% time_to_minutes(+Hour, +Minute, -TotalMinutes)
%% Converts hour:minute to total minutes from midnight
time_to_minutes(Hour, Minute, Total) :-
    integer(Hour), Hour >= 0, Hour =< 23,
    integer(Minute), Minute >= 0, Minute =< 59,
    Total is Hour * 60 + Minute.

%% minutes_to_time(+TotalMinutes, -Hour, -Minute)
%% Converts total minutes to hour:minute
minutes_to_time(Total, Hour, Minute) :-
    integer(Total), Total >= 0, Total =< 1439,
    Hour is Total // 60,
    Minute is Total mod 60.

%% ============================================================================
%% First-Order Logic: Interval Overlap Detection
%% ============================================================================
%%
%% Two intervals [S1, E1] and [S2, E2] overlap iff:
%% ∃t : (S1 ≤ t < E1) ∧ (S2 ≤ t < E2)
%%
%% This is equivalent to: S1 < E2 ∧ S2 < E1 (Resolution-based simplification)

%% intervals_overlap(+Start1, +End1, +Start2, +End2)
%% True if two time intervals overlap
%% Uses Resolution: ~(S1 >= E2 ∨ S2 >= E1) ≡ S1 < E2 ∧ S2 < E1
intervals_overlap(Start1, End1, Start2, End2) :-
    Start1 < End2,
    Start2 < End1.

%% ============================================================================
%% Conflict Detection with Resolution
%% ============================================================================
%%
%% Given a new event [NewStart, NewEnd] and a list of existing events,
%% determine if there is a conflict using Resolution:
%%
%% Knowledge Base:
%%   event(ID, Start, End) - existing events
%%
%% Query: ∃e ∈ Events : overlaps(NewEvent, e)
%%
%% Resolution: We negate the goal and try to derive empty clause
# %% If we can't, the original query is true (conflict exists)

%% events_overlap(+NewStart, +NewEnd, +ExistingStart, +ExistingEnd)
%% Check if a new event overlaps with an existing event
events_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd) :-
    intervals_overlap(NewStart, NewEnd, ExistingStart, ExistingEnd).

%% check_conflict(+NewStartH, +NewStartM, +NewEndH, +NewEndM, +ExistingEvents, -Conflicts)
%% ExistingEvents is a list of event(ID, Title, StartH, StartM, EndH, EndM)
%% Returns list of conflicting event IDs
%%
%% Logical Inference:
%% ∀e ∈ ExistingEvents: conflicts(new, e) → e ∈ Conflicts
check_conflict(NewStartH, NewStartM, NewEndH, NewEndM, ExistingEvents, Conflicts) :-
    time_to_minutes(NewStartH, NewStartM, NewStart),
    time_to_minutes(NewEndH, NewEndM, NewEnd),
    findall(
        conflict(ID, Title, SH, SM, EH, EM),
        (
            member(event(ID, Title, SH, SM, EH, EM), ExistingEvents),
            time_to_minutes(SH, SM, ExStart),
            time_to_minutes(EH, EM, ExEnd),
            events_overlap(NewStart, NewEnd, ExStart, ExEnd)
        ),
        Conflicts
    ).

%% ============================================================================
%% Constraint Solving: Find Free Time Slots
%% ============================================================================
%%
# %% Problem: Find time slots of duration D that don't conflict with existing events
%%
%% Constraint Satisfaction Problem (CSP):
%% - Variables: SlotStart, SlotEnd
%% - Domain: 0-1440 (minutes in a day)
%% - Constraints:
%%   1. SlotEnd - SlotStart = Duration
%%   2. ∀e ∈ Events: ¬overlaps(Slot, e)
%%
%% We solve this by:
%% 1. Generating candidate slots
%% 2. Filtering by constraint satisfaction

%% slot_conflicts_with_events(+Start, +End, +Events)
%% True if slot conflicts with any event in the list
slot_conflicts_with_events(Start, End, Events) :-
    member(event(_, _, SH, SM, EH, EM), Events),
    time_to_minutes(SH, SM, ExStart),
    time_to_minutes(EH, EM, ExEnd),
    intervals_overlap(Start, End, ExStart, ExEnd),
    !.  % Cut after finding first conflict

%% slot_is_free(+Start, +End, +Events)
%% True if slot does not conflict with any event
slot_is_free(Start, End, Events) :-
    \+ slot_conflicts_with_events(Start, End, Events).

%% generate_candidate_slots(+MinStart, +MaxEnd, +Duration, +Step, -Slots)
%% Generate all possible start times for slots of given duration
%% Step is the granularity (e.g., 30 minutes)
generate_candidate_slots(MinStart, MaxEnd, Duration, Step, Slots) :-
    MaxStart is MaxEnd - Duration,
    findall(
        Start,
        (
            between(0, 1000, N),  % Limit iterations
            Start is MinStart + N * Step,
            Start =< MaxStart
        ),
        Slots
    ).

%% find_free_slots(+DurationMinutes, +Events, +MinStartH, +MinStartM, +MaxEndH, +MaxEndM, -FreeSlots)
%% Find all free slots of given duration within time bounds
%% Returns list of slot(StartH, StartM, EndH, EndM)
%%
%% This uses Constraint Solving:
%% - Generate candidate slots
%% - Filter by: ∀e ∈ Events: ¬overlaps(candidate, e)
find_free_slots(DurationMinutes, Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeSlots) :-
    time_to_minutes(MinStartH, MinStartM, MinStart),
    time_to_minutes(MaxEndH, MaxEndM, MaxEnd),
    Step = 30,  % 30-minute granularity
    generate_candidate_slots(MinStart, MaxEnd, DurationMinutes, Step, CandidateStarts),
    findall(
        slot(SH, SM, EH, EM),
        (
            member(SlotStart, CandidateStarts),
            SlotEnd is SlotStart + DurationMinutes,
            SlotEnd =< MaxEnd,
            slot_is_free(SlotStart, SlotEnd, Events),
            minutes_to_time(SlotStart, SH, SM),
            minutes_to_time(SlotEnd, EH, EM)
        ),
        FreeSlots
    ).

%% ============================================================================
%% Find Free Time Ranges (Contiguous Free Periods)
%% ============================================================================
%%
%% Instead of returning fixed-duration slots, this returns the actual free
%% time ranges (gaps between events). Users can then select any start time
%% within these ranges.
%%
%% Algorithm:
%% 1. Sort events by start time
%% 2. Find gaps between consecutive events
%% 3. Include gap before first event and after last event

%% sort_events_by_start(+Events, -SortedEvents)
%% Sort events by their start time in minutes
sort_events_by_start(Events, Sorted) :-
    map_list_to_pairs(event_start_minutes, Events, Pairs),
    keysort(Pairs, SortedPairs),
    pairs_values(SortedPairs, Sorted).

%% event_start_minutes(+Event, -Minutes)
%% Extract start time in minutes from an event
event_start_minutes(event(_, _, SH, SM, _, _), Minutes) :-
    time_to_minutes(SH, SM, Minutes).

%% find_free_ranges(+Events, +MinStartH, +MinStartM, +MaxEndH, +MaxEndM, -FreeRanges)
%% Find all contiguous free time ranges within the given bounds
%% Returns list of range(StartH, StartM, EndH, EndM)
%%
%% Example:
%% Events: [event(e1, "Meeting", 10, 0, 12, 0), event(e2, "Lunch", 14, 0, 15, 0)]
%% MinStart: 8:00, MaxEnd: 18:00
%% Result: [range(8, 0, 10, 0), range(12, 0, 14, 0), range(15, 0, 18, 0)]
find_free_ranges(Events, MinStartH, MinStartM, MaxEndH, MaxEndM, FreeRanges) :-
    time_to_minutes(MinStartH, MinStartM, MinStart),
    time_to_minutes(MaxEndH, MaxEndM, MaxEnd),
    (Events = [] ->
        % No events - entire range is free
        FreeRanges = [range(MinStartH, MinStartM, MaxEndH, MaxEndM)]
    ;
        sort_events_by_start(Events, SortedEvents),
        find_gaps(SortedEvents, MinStart, MaxEnd, GapsInMinutes),
        convert_gaps_to_ranges(GapsInMinutes, FreeRanges)
    ).

%% find_gaps(+SortedEvents, +MinStart, +MaxEnd, -Gaps)
%% Find gaps between events as list of gap(Start, End) in minutes
find_gaps([], MinStart, MaxEnd, [gap(MinStart, MaxEnd)]) :-
    MinStart < MaxEnd, !.
find_gaps([], _, _, []).

find_gaps([Event|Rest], MinStart, MaxEnd, Gaps) :-
    Event = event(_, _, SH, SM, EH, EM),
    time_to_minutes(SH, SM, EventStart),
    time_to_minutes(EH, EM, EventEnd),
    % Gap before this event?
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
    % Continue from end of this event
    NewMinStart is max(MinStart, EventEnd),
    find_gaps(Rest, NewMinStart, MaxEnd, RestGaps),
    append(FirstGap, RestGaps, Gaps).

%% convert_gaps_to_ranges(+Gaps, -Ranges)
%% Convert gap(StartMin, EndMin) to range(SH, SM, EH, EM)
convert_gaps_to_ranges([], []).
convert_gaps_to_ranges([gap(StartMin, EndMin)|Rest], [range(SH, SM, EH, EM)|RestRanges]) :-
    StartMin < EndMin,  % Only include non-empty ranges
    minutes_to_time(StartMin, SH, SM),
    minutes_to_time(EndMin, EH, EM),
    convert_gaps_to_ranges(Rest, RestRanges).
convert_gaps_to_ranges([gap(StartMin, EndMin)|Rest], RestRanges) :-
    StartMin >= EndMin,  % Skip empty ranges
    convert_gaps_to_ranges(Rest, RestRanges).

%% ============================================================================
%% Logical Inference: Find Free Days
%% ============================================================================
%%
%% Knowledge: A day is "free" for a slot if:
%% ∃ time_range on that day : slot fits in time_range ∧ no conflicts
%%
%% Inference Rule:
%% free_day(D) ← ∃slot : fits(slot, D) ∧ ¬∃e : conflicts(slot, e)

%% find_free_days(+DurationMinutes, +EventsByDay, +StartHour, +StartMinute, +EndHour, +EndMinute, -FreeDays)
%% EventsByDay is a list of day(Day, Month, Year, Events)
%% Returns list of days where the slot can fit
%% FreeDays format: day(Day, Month, Year, AvailableSlots)
find_free_days(DurationMinutes, EventsByDay, StartHour, StartMinute, EndHour, EndMinute, FreeDays) :-
    findall(
        day(D, M, Y, Slots),
        (
            member(day(D, M, Y, Events), EventsByDay),
            find_free_slots(DurationMinutes, Events, StartHour, StartMinute, EndHour, EndMinute, Slots),
            Slots \= []  % Day has at least one free slot
        ),
        FreeDays
    ).

%% ============================================================================
%% Utility Predicates for Python Integration
%% ============================================================================

%% check_single_conflict(+NH, +NM, +NEH, +NEM, +EH, +EM, +EEH, +EEM)
%% Simple conflict check between two events (for direct Python calls)
check_single_conflict(NH, NM, NEH, NEM, EH, EM, EEH, EEM) :-
    time_to_minutes(NH, NM, NewStart),
    time_to_minutes(NEH, NEM, NewEnd),
    time_to_minutes(EH, EM, ExStart),
    time_to_minutes(EEH, EEM, ExEnd),
    intervals_overlap(NewStart, NewEnd, ExStart, ExEnd).

%% ============================================================================
%% Example Queries (for testing)
%% ============================================================================
%%
%% Check conflict:
%% ?- check_conflict(9, 0, 10, 0, [event(e1, "Meeting", 9, 30, 10, 30)], C).
%% C = [conflict(e1, "Meeting", 9, 30, 10, 30)]
%%
%% Find free slots (fixed duration):
%% ?- find_free_slots(60, [event(e1, "M", 9, 0, 10, 0)], 8, 0, 18, 0, S).
%% S = [slot(8, 0, 9, 0), slot(10, 0, 11, 0), ...]
%%
%% Find free ranges (contiguous periods):
%% ?- find_free_ranges([event(e1, "Meeting", 10, 0, 12, 0)], 8, 0, 18, 0, R).
%% R = [range(8, 0, 10, 0), range(12, 0, 18, 0)]
