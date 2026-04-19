%% apps/prolog/main.pl'
%% ============================================================================
%% Schedule Assistant — Main Entry Point
%% ============================================================================
%%
%% Loads the knowledge base (kb.pl) and reasoning rules (rules.pl).
%% Provides two API layers:
%%   1. Legacy API  — backward-compatible JSON result predicates
%%   2. Reasoning API — KRR query predicates for inference
%%
%% Usage:
%%   ?- demo(conflict('evt-001', X)).          % Who conflicts with evt-001?
%%   ?- demo(valid_schedule('cal-001', S, E)).  % Is this schedule valid?
%%   ?- api_reasoning_query(conflict, 'evt-001', Result).
%% ============================================================================

:- use_module(kb).
:- use_module(rules).

%% Re-export legacy predicates (backward compatible)
:- reexport(kb, [
    event/7,
    calendar/3,
    add_event/7,
    remove_event/1,
    move_event/3,
    list_events/2,
    list_events_in_range/4
]).

:- reexport(rules, [
    events_overlap/2,
    check_overlap/4,
    check_event_conflicts/5,
    is_within_working_hours/3,
    validate_event_time/5,
    find_free_slots/5,
    slot_available/4
]).

%% Re-export KRR reasoning predicates
:- reexport(rules, [
    conflict/2,
    valid_schedule/3,
    available_at/3,
    find_available_slot/4,
    higher_priority/2,
    is_a/2,
    effective_priority/2,
    constraint_holds/3,
    all_constraints_hold/3,
    demo/1,
    explain/2
]).

%% Re-export KB knowledge predicates
:- reexport(kb, [
    event_category/2,
    event_type/2,
    priority_level/2,
    event_priority/2,
    default_priority/2,
    scheduling_constraint/1,
    constraint_applies_to/2,
    user_available/4,
    day_type/2
]).

%% ============================================================================
%% Legacy API Predicates (backward compatible — for backend integration)
%% ============================================================================

%% Check if creating an event would cause conflicts
api_check_overlap(CalendarId, Start, End, Result) :-
    check_overlap(CalendarId, Start, End, Conflicts),
    length(Conflicts, NumConflicts),
    (   NumConflicts > 0
    ->  Result = json{has_conflicts: true, conflict_count: NumConflicts, conflict_ids: Conflicts}
    ;   Result = json{has_conflicts: false, conflict_count: 0, conflict_ids: []}
    ).

%% Find available slots for a calendar
api_find_free_slots(CalendarId, StartDate, EndDate, Duration, Result) :-
    find_free_slots(CalendarId, StartDate, EndDate, Duration, Slots),
    length(Slots, NumSlots),
    Result = json{success: true, slot_count: NumSlots, slots: Slots}.

%% Validate an event before creation/update
api_validate_event(CalendarId, UserId, Start, End, Result) :-
    validate_event_time(CalendarId, UserId, Start, End, ValidationResult),
    (   ValidationResult = ok
    ->  Result = json{valid: true, message: 'Event time is valid'}
    ;   ValidationResult = overlap(Conflicts)
    ->  Result = json{valid: false, reason: 'overlap', conflicts: Conflicts}
    ;   ValidationResult = outside_hours
    ->  Result = json{valid: false, reason: 'outside_working_hours', conflicts: []}
    ;   Result = json{valid: false, reason: 'unknown', conflicts: []}
    ).

%% ============================================================================
%% Reasoning API Predicates (KRR — for inference queries)
%% ============================================================================

%% Query: Find all conflicts for an event
%%   api_find_conflicts(+EventId, -Result)
api_find_conflicts(EventId, Result) :-
    findall(
        ConflictId,
        conflict(EventId, ConflictId),
        ConflictIds
    ),
    length(ConflictIds, Count),
    Result = json{event_id: EventId, conflict_count: Count, conflicts: ConflictIds}.

%% Query: Is this schedule valid? (Inference-based)
%%   api_valid_schedule(+CalendarId, +Start, +End, -Result)
api_valid_schedule(CalendarId, Start, End, Result) :-
    (   valid_schedule(CalendarId, Start, End)
    ->  Result = json{valid: true, calendar: CalendarId, message: 'Schedule is valid per all constraints'}
    ;   %% Identify which constraints failed
        findall(
            FailedConstraint,
            (   scheduling_constraint(FailedConstraint),
                \+ constraint_holds(FailedConstraint, CalendarId, event_interval(Start, End))
            ),
            FailedConstraints
        ),
        Result = json{valid: false, calendar: CalendarId,
                      failed_constraints: FailedConstraints,
                      message: 'One or more scheduling constraints violated'}
    ).

%% Query: What slots are available? (Inference-based)
%%   api_available_slots(+CalendarId, +Duration, -Result)
api_available_slots(CalendarId, Duration, Result) :-
    findall(
        slot(Start, End),
        find_available_slot(CalendarId, Duration, Start, End),
        Slots
    ),
    length(Slots, Count),
    Result = json{calendar: CalendarId, slot_count: Count, slots: Slots}.

%% Query: Compare priority of two events
%%   api_compare_priority(+EventId1, +EventId2, -Result)
api_compare_priority(EventId1, EventId2, Result) :-
    effective_priority(EventId1, P1),
    effective_priority(EventId2, P2),
    (   P1 > P2
    ->  Winner = EventId1, Relation = higher
    ;   P1 < P2
    ->  Winner = EventId2, Relation = lower
    ;   Winner = none, Relation = equal
    ),
    Result = json{event1: EventId1, priority1: P1,
                  event2: EventId2, priority2: P2,
                  winner: Winner, relation: Relation}.

%% Query: Explain why something holds (meta-reasoning)
%%   api_explain(+Goal, -Result)
api_explain(Goal, Result) :-
    (   explain(Goal, Proof)
    ->  Result = json{goal: Goal, proven: true, proof_steps: Proof}
    ;   Result = json{goal: Goal, proven: false, proof_steps: []}
    ).

%% Query: Prove a scheduling goal via meta-interpreter
%%   api_demo(+Goal, -Result)
api_demo(Goal, Result) :-
    (   demo(Goal)
    ->  Result = json{goal: Goal, holds: true}
    ;   Result = json{goal: Goal, holds: false}
    ).

%% ============================================================================
%% Example Queries (for testing)
%% ============================================================================

%% Example: Check if two sample events overlap
example_overlap_check :-
    event('evt-001', _, _, S1, E1, _, _),
    event('evt-002', _, _, S2, E2, _, _),
    format('Event 1: ~w to ~w~n', [S1, E1]),
    format('Event 2: ~w to ~w~n', [S2, E2]),
    (   events_overlap(
            event('evt-001', _, _, S1, E1, confirmed, _),
            event('evt-002', _, _, S2, E2, confirmed, _)
        )
    ->  format('Events OVERLAP~n', [])
    ;   format('Events do NOT overlap~n', [])
    ).

%% Example: Find conflicts for a proposed meeting
example_conflict_check :-
    format('Checking for conflicts with proposed meeting 10:30-11:30 on 2024-01-20...~n', []),
    check_overlap('cal-001', '2024-01-20T10:30:00', '2024-01-20T11:30:00', Conflicts),
    (   Conflicts = []
    ->  format('No conflicts found!~n', [])
    ;   format('Conflicts found: ~w~n', [Conflicts])
    ).

%% Example: List all events
example_list_events :-
    format('Events in calendar cal-001:~n', []),
    list_events('cal-001', Events),
    forall(
        member(event(Id, _, Title, Start, End, Status, _), Events),
        format('  [~w] ~w: ~w to ~w (~w)~n', [Id, Title, Start, End, Status])
    ).

%% Example: Find free slots
example_free_slots :-
    format('Finding free slots for week of 2024-01-20...~n', []),
    find_free_slots('cal-001', '2024-01-20', '2024-01-26', 60, Slots),
    format('Available slots: ~w~n', [Slots]).

%% === NEW KRR Examples ===

%% Example: Use reasoning to find conflicts
example_reasoning_conflicts :-
    format('~n--- KRR: Reasoning about conflicts ---~n', []),
    forall(
        conflict(E1, E2),
        format('  CONFLICT: ~w <-> ~w~n', [E1, E2])
    ).

%% Example: Use meta-interpreter
example_demo :-
    format('~n--- KRR: Meta-interpreter demo ---~n', []),
    (   demo(available_at('cal-001', '2024-01-20T11:00:00', '2024-01-20T12:00:00'))
    ->  format('  11:00-12:00 is available on cal-001~n', [])
    ;   format('  11:00-12:00 is NOT available on cal-001~n', [])
    ),
    (   demo(conflict('evt-001', X))
    ->  format('  evt-001 conflicts with: ~w~n', [X])
    ;   format('  evt-001 has no conflicts~n', [])
    ).

%% Example: Priority reasoning
example_priority :-
    format('~n--- KRR: Priority reasoning ---~n', []),
    forall(
        (event(Id, _, Title, _, _, _, _), effective_priority(Id, P)),
        format('  ~w (~w): priority = ~w~n', [Id, Title, P])
    ).

%% Example: Explain reasoning
example_explain :-
    format('~n--- KRR: Explanation/proof trace ---~n', []),
    (   explain(available_at('cal-001', '2024-01-20T11:00:00', '2024-01-20T12:00:00'), Proof)
    ->  format('  Proof: ~w~n', [Proof])
    ;   format('  Could not prove availability~n', [])
    ).

%% Run all examples
run_examples :-
    format('~n=== Schedule Assistant Prolog Examples ===~n~n', []),
    example_list_events,
    format('~n', []),
    example_overlap_check,
    format('~n', []),
    example_conflict_check,
    format('~n', []),
    example_free_slots,
    example_reasoning_conflicts,
    example_demo,
    example_priority,
    example_explain,
    format('~n=== Examples Complete ===~n', []).

%% Interactive mode entry point
:- initialization((
    format('Schedule Assistant Prolog Module Loaded (KRR-Enhanced)~n', []),
    format('Run "run_examples." to see example queries~n~n', []),
    format('Legacy predicates:~n', []),
    format('  - check_overlap(CalId, Start, End, Conflicts)~n', []),
    format('  - find_free_slots(CalId, StartDate, EndDate, Duration, Slots)~n', []),
    format('  - validate_event_time(CalId, UserId, Start, End, Result)~n', []),
    format('  - list_events(CalId, Events)~n~n', []),
    format('KRR Reasoning predicates:~n', []),
    format('  - conflict(EventId1, EventId2)~n', []),
    format('  - valid_schedule(CalId, Start, End)~n', []),
    format('  - available_at(CalId, Start, End)~n', []),
    format('  - find_available_slot(CalId, Duration, Start, End)~n', []),
    format('  - higher_priority(EventId1, EventId2)~n', []),
    format('  - demo(Goal)  — meta-interpreter~n', []),
    format('  - explain(Goal, Proof)  — with proof trace~n', [])
), program).
