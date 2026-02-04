%% apps/prolog/rules.pl
%% Rules and Constraints for the Schedule Assistant
%% This file contains logical rules for scheduling constraints

:- module(rules, [
    events_overlap/2,
    check_overlap/4,
    check_event_conflicts/5,
    is_within_working_hours/3,
    validate_event_time/5,
    find_free_slots/5,
    slot_available/4
]).

:- use_module(kb).

%% ============================================================================
%% Time Parsing Utilities
%% ============================================================================

%% Parse ISO datetime string to components
%% parse_datetime('2024-01-20T10:00:00', Date, Time)
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

%% Compare times (as HH:MM strings)
time_before(Time1, Time2) :-
    Time1 @< Time2.

time_after(Time1, Time2) :-
    Time1 @> Time2.

time_between(Time, Start, End) :-
    Time @>= Start,
    Time @=< End.

%% ============================================================================
%% Overlap Detection Rules
%% ============================================================================

%% Check if two events overlap
%% Two events overlap if: start1 < end2 AND end1 > start2
events_overlap(event(_, _, _, Start1, End1, Status1, _), 
               event(_, _, _, Start2, End2, Status2, _)) :-
    Status1 \= cancelled,
    Status2 \= cancelled,
    Start1 @< End2,
    End1 @> Start2.

%% Check if a proposed time range overlaps with existing events
%% Returns list of conflicting event IDs
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

%% Check for conflicts, optionally excluding an event (for updates)
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

%% ============================================================================
%% Working Hours Validation
%% ============================================================================

%% Check if a time is within working hours
is_within_working_hours(UserId, StartTime, EndTime) :-
    working_hours(UserId, WorkStart, WorkEnd),
    extract_time(StartTime, StartHM),
    extract_time(EndTime, EndHM),
    StartHM @>= WorkStart,
    EndHM @=< WorkEnd.

%% Default working hours if not set
is_within_working_hours(UserId, StartTime, EndTime) :-
    \+ working_hours(UserId, _, _),
    extract_time(StartTime, StartHM),
    extract_time(EndTime, EndHM),
    StartHM @>= '09:00',
    EndHM @=< '18:00'.

%% ============================================================================
%% Event Validation
%% ============================================================================

%% Validate a proposed event time
%% Returns: ok, overlap(ConflictIds), or outside_hours
validate_event_time(CalendarId, UserId, ProposedStart, ProposedEnd, Result) :-
    (   check_overlap(CalendarId, ProposedStart, ProposedEnd, Conflicts),
        Conflicts \= []
    ->  Result = overlap(Conflicts)
    ;   (   \+ is_within_working_hours(UserId, ProposedStart, ProposedEnd)
        ->  Result = outside_hours
        ;   Result = ok
        )
    ).

%% ============================================================================
%% Free Slot Finding
%% ============================================================================

%% Check if a specific slot is available
slot_available(CalendarId, SlotStart, SlotEnd, Available) :-
    check_overlap(CalendarId, SlotStart, SlotEnd, Conflicts),
    (   Conflicts = []
    ->  Available = true
    ;   Available = false
    ).

%% Find free slots in a date range
%% This is a simplified version - actual implementation would need
%% proper datetime arithmetic
find_free_slots(CalendarId, _StartDate, _EndDate, _DurationMinutes, Slots) :-
    %% Get all events for the calendar
    list_events(CalendarId, Events),
    
    %% For now, return placeholder slots
    %% In a real implementation, this would:
    %% 1. Generate candidate time slots
    %% 2. Filter out overlapping slots
    %% 3. Filter by working hours
    %% 4. Apply buffer time
    (   Events = []
    ->  Slots = [slot('09:00', '10:00'), slot('10:00', '11:00'), slot('14:00', '15:00')]
    ;   Slots = [slot('09:00', '10:00'), slot('16:00', '17:00')]
    ).

%% ============================================================================
%% Buffer Time Rules
%% ============================================================================

%% Check if there's enough buffer between events
has_sufficient_buffer(UserId, EventEnd, NextEventStart) :-
    buffer_minutes(UserId, BufferMin),
    %% In real implementation, would calculate time difference
    %% For now, just check they're not the same
    EventEnd @< NextEventStart.

%% Default buffer check
has_sufficient_buffer(UserId, EventEnd, NextEventStart) :-
    \+ buffer_minutes(UserId, _),
    EventEnd @< NextEventStart.

%% ============================================================================
%% Constraint Checking (for agent integration)
%% ============================================================================

%% Main constraint check predicate for the agent
%% check_constraints(+CalendarId, +UserId, +Start, +End, -Result)
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
