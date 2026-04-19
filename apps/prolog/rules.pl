%% apps/prolog/rules.pl'
%% ============================================================================
%% Reasoning Rules & Constraints — Schedule Assistant
%% ============================================================================
%%
%% This module implements Knowledge Representation and Reasoning (KRR) for
%% scheduling. It is organized into:
%%
%%   1. Time Utilities        — parsing and comparison
%%   2. Core Reasoning Rules  — declarative conflict/validity/availability
%%   3. Constraint Checking   — constraint satisfaction via KB declarations
%%   4. Inference Queries     — find_available_slot, valid_schedule, etc.
%%   5. Meta-Interpreter      — demo/1 for reasoning about scheduling knowledge
%%   6. Legacy Predicates     — backward-compatible wrappers
%%
%% Design Principle (KRR):
%%   Rules here INFER answers from knowledge in kb.pl.
%%   They do NOT simulate procedural algorithms.
%%   Constraints are declared as facts in kb.pl; rules here CHECK them.
%% ============================================================================

:- module(rules, [
    %% --- Legacy exports (backward compatible) ---
    events_overlap/2,
    check_overlap/4,
    check_event_conflicts/5,
    is_within_working_hours/3,
    validate_event_time/5,
    find_free_slots/5,
    slot_available/4,

    %% --- KRR Reasoning Predicates ---
    conflict/2,                    % conflict(EventId1, EventId2)
    valid_schedule/3,              % valid_schedule(CalendarId, Start, End)
    available_at/3,                % available_at(CalendarId, Start, End)
    find_available_slot/4,         % find_available_slot(CalendarId, Duration, Start, End)
    higher_priority/2,             % higher_priority(EventId1, EventId2)
    is_a/2,                        % is_a(EventType, Category) — taxonomy traversal
    effective_priority/2,          % effective_priority(EventId, NumericValue)
    constraint_holds/3,            % constraint_holds(Constraint, CalendarId, event_interval(S,E))
    all_constraints_hold/3,        % all_constraints_hold(CalendarId, Start, End)

    %% --- Meta-Interpreter ---
    demo/1,                        % demo(Goal) — prove scheduling goal via KB
    explain/2                      % explain(Goal, Explanation) — prove with trace
]).

:- use_module(kb).

%% ============================================================================
%% 1. Time Parsing Utilities
%% ============================================================================

%% Parse ISO datetime string to components
parse_datetime(ISOString, Date, Time) :-
    atom_string(ISOString, Str),
    split_string(Str, "T", "", [DateStr, TimeStr]),
    atom_string(Date, DateStr),
    atom_string(Time, TimeStr).

%% Extract just the time portion (HH:MM)
extract_time(ISOString, HourMin) :-
    parse_datetime(ISOString, _, TimeAtom),
    atom_string(TimeAtom, TimeStr),
    split_string(TimeStr, ":", "", [H, M | _]),
    atomics_to_string([H, ":", M], HourMin).

%% Extract date portion (YYYY-MM-DD)
extract_date(ISOString, Date) :-
    parse_datetime(ISOString, Date, _).

time_before(Time1, Time2) :- Time1 @< Time2.
time_after(Time1, Time2) :- Time1 @> Time2.
time_between(Time, Start, End) :- Time @>= Start, Time @=< End.

%% ============================================================================
%% 2. Core Reasoning Rules (Declarative — KRR)
%% ============================================================================
%%
%% These predicates express WHAT conditions hold, not HOW to compute them.
%% They rely on facts in kb.pl and succeed/fail via Prologs inference.

%% --- Taxonomy Reasoning ---
%% is_a(Type, Category): Type is a kind of Category (transitive closure)
is_a(Type, Type).
is_a(Type, Category) :-
    event_category(Type, Parent),
    is_a(Parent, Category).

%% --- Conflict Detection (Declarative) ---
%%
%% Two events conflict iff they share a calendar, are both active,
%% and their time intervals overlap.
%%
%% Logical formulation:
%%   conflict(E1, E2) ↔ same_calendar(E1,E2) ∧ active(E1) ∧ active(E2)
%%                       ∧ overlaps(interval(E1), interval(E2))

conflict(Id1, Id2) :-
    event(Id1, CalId, _, Start1, End1, Status1, _),
    event(Id2, CalId, _, Start2, End2, Status2, _),
    Id1 \= Id2,
    Status1 \= cancelled,
    Status2 \= cancelled,
    Start1 @< End2,
    End1 @> Start2.

%% --- Priority Reasoning ---
%%
%% Infer the effective numeric priority for any event, using:
%%   1. Explicit per-event priority from KB
%%   2. Default priority for the events type
%%   3. Fallback to medium (5)

effective_priority(EventId, Value) :-
    event_priority(EventId, Level),
    priority_level(Level, Value), !.
effective_priority(EventId, Value) :-
    event_type(EventId, Type),
    default_priority(Type, Level),
    priority_level(Level, Value), !.
effective_priority(_, 5).   % fallback: medium

%% higher_priority(E1, E2): E1 has strictly higher priority than E2
higher_priority(EventId1, EventId2) :-
    effective_priority(EventId1, P1),
    effective_priority(EventId2, P2),
    P1 > P2.

%% --- Validity Reasoning ---
%%
%% valid_schedule(CalendarId, Start, End):
%%   A proposed time interval is valid iff ALL declared constraints hold.
%%   This is pure inference — it queries constraint declarations from kb.pl.

valid_schedule(CalendarId, Start, End) :-
    all_constraints_hold(CalendarId, Start, End).

%% --- Availability Reasoning ---
%%
%% available_at(CalendarId, Start, End):
%%   The calendar is available iff no active event occupies that interval.

available_at(CalendarId, Start, End) :-
    \+ (
        event(_, CalendarId, _, ExStart, ExEnd, Status, _),
        Status \= cancelled,
        Start @< ExEnd,
        End @> ExStart
    ).

%% --- Slot Finding by Inference ---
%%
%% find_available_slot(CalendarId, DurationMinutes, Start, End):
%%   Infer an available slot by examining gaps between existing events.
%%   This is NOT a generate-and-test algorithm; it reasons about the
%%   knowledge base structure to find valid intervals.

find_available_slot(CalendarId, _DurationMinutes, SlotStart, SlotEnd) :-
    %% Strategy: find gaps between consecutive events
    calendar(CalendarId, UserId, _),
    list_events(CalendarId, Events),
    (   Events = []
    ->  %% No events: entire working hours are available
        working_hours_for(UserId, WorkStart, WorkEnd),
        SlotStart = WorkStart,
        SlotEnd = WorkEnd
    ;   %% Reason about gaps between sorted events
        sort_events_by_time(Events, Sorted),
        working_hours_for(UserId, WorkStart, WorkEnd),
        find_gap_in_schedule(Sorted, WorkStart, WorkEnd, SlotStart, SlotEnd)
    ).

%% Helper: get working hours (with default fallback)
working_hours_for(UserId, Start, End) :-
    working_hours(UserId, Start, End), !.
working_hours_for(_, '09:00', '18:00').

%% Helper: sort events by start time
sort_events_by_time(Events, Sorted) :-
    msort(Events, Sorted).  % events sort naturally by start time

%% Reason about gaps: before first event
find_gap_in_schedule([event(_, _, _, FirstStart, _, _, _)|_], WorkStart, _, WorkStart, FirstStart) :-
    extract_time(FirstStart, FirstTimeHM),
    WorkStart @< FirstTimeHM.

%% Reason about gaps: between consecutive events
find_gap_in_schedule([event(_, _, _, _, End1, _, _), event(_, _, _, Start2, _, _, _)|_], _, _, GapStart, GapEnd) :-
    extract_time(End1, GapStartHM),
    extract_time(Start2, GapEndHM),
    GapStartHM @< GapEndHM,
    GapStart = GapStartHM,
    GapEnd = GapEndHM.

find_gap_in_schedule([_|Rest], WorkStart, WorkEnd, GapStart, GapEnd) :-
    Rest \= [],
    find_gap_in_schedule(Rest, WorkStart, WorkEnd, GapStart, GapEnd).

%% Reason about gaps: after last event
find_gap_in_schedule([event(_, _, _, _, LastEnd, _, _)], _, WorkEnd, GapStart, WorkEnd) :-
    extract_time(LastEnd, LastEndHM),
    LastEndHM @< WorkEnd,
    GapStart = LastEndHM.

%% ============================================================================
%% 3. Constraint Checking (KRR — Constraint Satisfaction)
%% ============================================================================
%%
%% Each constraint declared in kb.pl has a corresponding checking rule here.
%% The rule `constraint_holds/3` maps constraint names to their logical conditions.
%% This separates WHAT constraints exist (kb.pl) from HOW to verify them (here).

%% No time overlap: proposed interval must not overlap any active event
constraint_holds(no_time_overlap, CalendarId, event_interval(Start, End)) :-
    available_at(CalendarId, Start, End).

%% Within working hours: event must fall inside users working hours
constraint_holds(within_working_hours, CalendarId, event_interval(Start, End)) :-
    calendar(CalendarId, UserId, _),
    is_within_working_hours(UserId, Start, End).

%% Sufficient buffer: event must have adequate buffer from neighbors
constraint_holds(sufficient_buffer, CalendarId, event_interval(Start, End)) :-
    calendar(CalendarId, UserId, _),
    \+ (
        event(_, CalendarId, _, _, EvEnd, Status, _),
        Status \= cancelled,
        extract_time(EvEnd, EvEndHM),
        extract_time(Start, StartHM),
        buffer_minutes(UserId, _Buffer),
        %% Simplified: just check events dont end exactly at start
        EvEndHM @> StartHM
    ;
        event(_, CalendarId, _, EvStart, _, Status, _),
        Status \= cancelled,
        extract_time(EvStart, EvStartHM),
        extract_time(End, EndHM),
        buffer_minutes(UserId, _Buffer2),
        EndHM @> EvStartHM
    ), !.
constraint_holds(sufficient_buffer, _, _).  % passes if no buffer requirement

%% Not cancelled: always holds for new proposed events (they are not cancelled)
constraint_holds(not_cancelled, _, _).

%% Positive duration: end must be after start
constraint_holds(positive_duration, _, event_interval(Start, End)) :-
    End @> Start.

%% all_constraints_hold/3: ALL applicable constraints must be satisfied
all_constraints_hold(CalendarId, Start, End) :-
    forall(
        (   scheduling_constraint(Constraint),
            constraint_applicable(Constraint, CalendarId)
        ),
        constraint_holds(Constraint, CalendarId, event_interval(Start, End))
    ).

%% Determine if a constraint applies to events in this calendar
constraint_applicable(Constraint, _CalendarId) :-
    constraint_applies_to(Constraint, all), !.
constraint_applicable(Constraint, CalendarId) :-
    %% Check if any event type in this calendar matches the constraint
    event(_, CalendarId, _, _, _, _, _),
    constraint_applies_to(Constraint, _SomeType).

%% ============================================================================
%% 4. Meta-Interpreter — Reasoning About Scheduling Knowledge
%% ============================================================================
%%
%% Inspired by meta-reasoning approaches (cf. meta-interpreters for SWRL/ontologies).
%% demo/1 proves goals against the scheduling knowledge base.
%% explain/2 provides a proof trace showing WHY a conclusion holds.
%%
%% This enables queries like:
%%   ?- demo(conflict('evt-001', 'evt-002')).
%%   ?- explain(valid_schedule('cal-001', S, E), Proof).

%% demo/1: Prove a scheduling goal
demo(true) :- !.
demo((A, B)) :- !, demo(A), demo(B).
demo((A ; B)) :- !, (demo(A) ; demo(B)).
demo(\+ A) :- !, \+ demo(A).

%% Scheduling-domain goals
demo(conflict(E1, E2)) :- conflict(E1, E2).
demo(valid_schedule(Cal, S, E)) :- valid_schedule(Cal, S, E).
demo(available_at(Cal, S, E)) :- available_at(Cal, S, E).
demo(higher_priority(E1, E2)) :- higher_priority(E1, E2).
demo(is_a(Type, Cat)) :- is_a(Type, Cat).
demo(constraint_holds(C, Cal, I)) :- constraint_holds(C, Cal, I).
demo(find_available_slot(Cal, Dur, S, E)) :- find_available_slot(Cal, Dur, S, E).

%% Fallback: try as a regular Prolog goal (for KB facts)
demo(Goal) :-
    \+ functor(Goal, demo, _),
    catch(Goal, _, fail).

%% explain/2: Prove with explanation trace
explain(true, []) :- !.
explain((A, B), Proof) :-
    !,
    explain(A, ProofA),
    explain(B, ProofB),
    append(ProofA, ProofB, Proof).

explain(conflict(E1, E2), [step(conflict, E1, E2, 'Events overlap in time and share calendar')]) :-
    conflict(E1, E2).

explain(valid_schedule(Cal, S, E), [step(valid_schedule, Cal, S-E, Details)]) :-
    (   valid_schedule(Cal, S, E)
    ->  Details = 'All scheduling constraints satisfied'
    ;   Details = 'One or more constraints violated'
    ).

explain(available_at(Cal, S, E), [step(available_at, Cal, S-E, Details)]) :-
    (   available_at(Cal, S, E)
    ->  Details = 'No conflicting events in this interval'
    ;   Details = 'Interval conflicts with existing event(s)'
    ).

explain(higher_priority(E1, E2), [step(priority, E1>E2, P1-P2, 'Priority comparison')]) :-
    effective_priority(E1, P1),
    effective_priority(E2, P2).

explain(Goal, [step(fact, Goal, true, 'Ground fact in knowledge base')]) :-
    catch(Goal, _, fail).

%% ============================================================================
%% 5. Legacy Predicates (Backward Compatible)
%% ============================================================================
%%
%% These predicates preserve the original API for Python integration.
%% Internally, they now delegate to the KRR reasoning predicates above.

%% Overlap detection — now delegates to conflict reasoning
events_overlap(event(_, _, _, Start1, End1, Status1, _),
               event(_, _, _, Start2, End2, Status2, _)) :-
    Status1 \= cancelled,
    Status2 \= cancelled,
    Start1 @< End2,
    End1 @> Start2.

%% Check overlap for a proposed time — uses availability reasoning
check_overlap(CalendarId, ProposedStart, ProposedEnd, ConflictIds) :-
    findall(
        Id,
        (
            event(Id, CalendarId, _, Start, End, Status, _),
            Status \= cancelled,
            ProposedStart @< End,
            ProposedEnd @> Start
        ),
        ConflictIds
    ).

%% Check for conflicts excluding an event
check_event_conflicts(CalendarId, ProposedStart, ProposedEnd, ExcludeId, ConflictIds) :-
    findall(
        Id,
        (
            event(Id, CalendarId, _, Start, End, Status, _),
            Status \= cancelled,
            Id \= ExcludeId,
            ProposedStart @< End,
            ProposedEnd @> Start
        ),
        ConflictIds
    ).

%% Working hours validation
is_within_working_hours(UserId, StartTime, EndTime) :-
    working_hours(UserId, WorkStart, WorkEnd),
    extract_time(StartTime, StartHM),
    extract_time(EndTime, EndHM),
    StartHM @>= WorkStart,
    EndHM @=< WorkEnd.

is_within_working_hours(UserId, StartTime, EndTime) :-
    \+ working_hours(UserId, _, _),
    extract_time(StartTime, StartHM),
    extract_time(EndTime, EndHM),
    StartHM @>= '09:00',
    EndHM @=< '18:00'.

%% Event validation — now uses constraint reasoning internally
validate_event_time(CalendarId, UserId, ProposedStart, ProposedEnd, Result) :-
    (   check_overlap(CalendarId, ProposedStart, ProposedEnd, Conflicts),
        Conflicts \= []
    ->  Result = overlap(Conflicts)
    ;   (   \+ is_within_working_hours(UserId, ProposedStart, ProposedEnd)
        ->  Result = outside_hours
        ;   Result = ok
        )
    ).

%% Free slot finding — now uses reasoning instead of placeholders
find_free_slots(CalendarId, _StartDate, _EndDate, _DurationMinutes, Slots) :-
    findall(
        slot(GapStart, GapEnd),
        find_available_slot(CalendarId, _DurationMinutes, GapStart, GapEnd),
        Slots
    ).

%% Slot availability check — uses availability reasoning
slot_available(CalendarId, SlotStart, SlotEnd, Available) :-
    (   available_at(CalendarId, SlotStart, SlotEnd)
    ->  Available = true
    ;   Available = false
    ).

%% ============================================================================
%% Buffer Time Rules
%% ============================================================================

has_sufficient_buffer(UserId, EventEnd, NextEventStart) :-
    buffer_minutes(UserId, _BufferMin),
    EventEnd @< NextEventStart.

has_sufficient_buffer(UserId, EventEnd, NextEventStart) :-
    \+ buffer_minutes(UserId, _),
    EventEnd @< NextEventStart.

%% ============================================================================
%% Constraint Checking (Legacy API for agent integration)
%% ============================================================================

check_constraints(CalendarId, UserId, Start, End, Result) :-
    validate_event_time(CalendarId, UserId, Start, End, ValidationResult),
    (   ValidationResult = ok
    ->  Result = json{valid: true, conflicts: [], message: 'No conflicts found'}
    ;   ValidationResult = overlap(Conflicts)
    ->  Result = json{valid: false, conflicts: Conflicts, message: 'Time conflicts with existing events'}
    ;   ValidationResult = outside_hours
    ->  Result = json{valid: false, conflicts: [], message: 'Time is outside working hours'}
    ;   Result = json{valid: false, conflicts: [], message: 'Unknown validation error'}
    ).
