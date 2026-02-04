%% apps/prolog/main.pl
%% Main entry point for the Schedule Assistant Prolog module
%% Load this file to access all predicates

:- use_module(kb).
:- use_module(rules).

%% Re-export commonly used predicates
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

%% ============================================================================
%% API Predicates (for backend integration)
%% ============================================================================

%% Check if creating an event would cause conflicts
%% api_check_overlap(+CalendarId, +Start, +End, -JSONResult)
api_check_overlap(CalendarId, Start, End, Result) :-
    check_overlap(CalendarId, Start, End, Conflicts),
    length(Conflicts, NumConflicts),
    (   NumConflicts > 0
    ->  Result = json{has_conflicts: true, conflict_count: NumConflicts, conflict_ids: Conflicts}
    ;   Result = json{has_conflicts: false, conflict_count: 0, conflict_ids: []}
    ).

%% Find available slots for a calendar
%% api_find_free_slots(+CalendarId, +StartDate, +EndDate, +Duration, -JSONResult)
api_find_free_slots(CalendarId, StartDate, EndDate, Duration, Result) :-
    find_free_slots(CalendarId, StartDate, EndDate, Duration, Slots),
    length(Slots, NumSlots),
    Result = json{success: true, slot_count: NumSlots, slots: Slots}.

%% Validate an event before creation/update
%% api_validate_event(+CalendarId, +UserId, +Start, +End, -JSONResult)
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
    format('~n=== Examples Complete ===~n', []).

%% Interactive mode entry point
:- initialization((
    format('Schedule Assistant Prolog Module Loaded~n', []),
    format('Run "run_examples." to see example queries~n', []),
    format('Available predicates:~n', []),
    format('  - check_overlap(CalId, Start, End, Conflicts)~n', []),
    format('  - find_free_slots(CalId, StartDate, EndDate, Duration, Slots)~n', []),
    format('  - validate_event_time(CalId, UserId, Start, End, Result)~n', []),
    format('  - list_events(CalId, Events)~n', [])
), program).
