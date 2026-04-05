% apps/prolog/rules_chat.pl - Chat Feature Constraint Solving Rules
% Uses First Order Logic with Resolution for conflict detection and alternative finding

:- dynamic event/5.
:- dynamic working_hours/3.

% ============================================================================
% Core Predicates - Conflict Detection and Validation
% ============================================================================

% Check if two time slots overlap
% overlap(StartA, EndA, StartB, EndB)
% Uses time comparison: StartA < EndB AND EndA > StartB
overlap(StartA, EndA, StartB, EndB) :-
    StartA < EndB,
    EndA > StartB.

% Check if a proposed event conflicts with existing events in calendar
% check_conflict(CalendarId, ProposedStart, ProposedEnd, ConflictIds)
% Returns: list of event IDs that overlap with proposed time
check_conflict(CalendarId, ProposedStart, ProposedEnd, ConflictIds) :-
    findall(
        EventId,
        (
            event(EventId, CalendarId, _, Start, End),
            overlap(ProposedStart, ProposedEnd, Start, End)
        ),
        ConflictIds
    ).

% Validate time is within working hours (9 AM to 6 PM default)
within_working_hours(StartTime, EndTime, StartHour, EndHour) :-
    StartTime >= StartHour,
    EndTime =< EndHour.

% ============================================================================
% Alternative Time Finding - Preference-Based Strategies
% ============================================================================

% Helper: Extract hour from datetime (format: "HH:MM")
extract_hour_minute(TimeStr, Hour, Minute) :-
    atom_string(TimeStr, S),
    atom_codes(S, Codes),
    Codes = [H1, H2, 58|Rest],  % 58 is ':'
    atom_codes(H, [H1, H2]),
    atom_codes(M, Rest),
    atom_number(H, Hour),
    atom_number(M, Minute).

% Helper: Calculate event duration in minutes
calculate_duration(Start, End, DurationMinutes) :-
    extract_hour_minute(Start, SHour, SMin),
    extract_hour_minute(End, EHour, EMin),
    SStartMinutes is SHour * 60 + SMin,
    EEndMinutes is EHour * 60 + EMin,
    DurationMinutes is EEndMinutes - SStartMinutes.

% Helper: Check if a specific time on specific day is available
is_time_available_on_day(CalendarId, Day, StartTime, EndTime) :-
    \+ (
        event(_, CalendarId, _, ExistingStart, ExistingEnd),
        day_contains(Day, ExistingStart),
        overlap(StartTime, EndTime, ExistingStart, ExistingEnd)
    ).

% Helper: Get day from datetime
day_contains(DayDate, DateTimeStr) :-
    % Simple string comparison - assumes format YYYY-MM-DD
    atom_string(DayDate, D),
    atom_string(DateTimeStr, DT),
    atom_concat(D, _, DT).

% ============================================================================
% PREFERENCE 1: Same time, different day
% find_alternatives_same_time(EventId, CalendarId, TimeslotStart, TimeslotEnd, NumOptions, Result)
% Returns list of dates where the same time slot is available
% ============================================================================

find_alternatives_same_time(EventId, CalendarId, TimeslotStart, TimeslotEnd, NumOptions, Result) :-
    % Find N available days starting after tomorrow
    findall(
        date(Day),
        (
            between(1, 60, DayOffset),  % Search next 60 days
            date_offset_future(DayOffset, Day),
            is_time_available_on_day(CalendarId, Day, TimeslotStart, TimeslotEnd),
            \+ is_weekend(Day)  % Exclude weekends by default
        ),
        AvailableDays
    ),
    length(AvailableDays, TotalAvailable),
    MinToUse is min(NumOptions, TotalAvailable),
    take_n(MinToUse, AvailableDays, Result).

% Helper: Get future date offset days from now
date_offset_future(DayOffset, DateStr) :-
    get_today(Today),
    atom_string(Today, TodayStr),
    date_add_days(TodayStr, DayOffset, DateStr).

% Helper: Take first N elements from list
take_n(N, List, Result) :-
    length(Result, N),
    append(Result, _, List), !.

take_n(0, _, []) :- !.
take_n(_, [], []) :- !.
take_n(N, [H|T], [H|Result]) :-
    N > 0,
    N1 is N - 1,
    take_n(N1, T, Result).

% ============================================================================
% PREFERENCE 2: Specific day, find free time slots
% find_alternatives_specific_day(CalendarId, Date, Duration, NumSlots, Result)
% Returns list of [StartTime, EndTime] pairs for given date
% ============================================================================

find_alternatives_specific_day(CalendarId, Date, Duration, NumSlots, Result) :-
    % Find N free time slots on specific date
    % Working hours: 9 AM to 6 PM
    findall(
        slot(Start, End),
        (
            time_slot(Hour, Start, End),  % Generate hourly slots
            End_minutes is Hour * 60 + 60,
            Start_minutes is Hour * 60,
            SlotDuration is End_minutes - Start_minutes,
            SlotDuration >= Duration,  % Check if slot is large enough
            is_time_available_on_day(CalendarId, Date, Start, End)
        ),
        AvailableSlots
    ),
    length(AvailableSlots, TotalAvailable),
    MinToUse is min(NumSlots, TotalAvailable),
    take_n(MinToUse, AvailableSlots, Result).

% Helper: Generate working hour time slots (30 min intervals)
time_slot(Hour, Start, End) :-
    between(9, 17, Hour),
    format(atom(Start), '~w:00', [Hour]),
    EndHour is Hour + 1,
    format(atom(End), '~w:00', [EndHour]).

% ============================================================================
% PREFERENCE 3: Specific date and time - validate only
% validate_specific_datetime(CalendarId, Date, StartTime, EndTime, IsValid)
% Returns: true if no conflicts, false otherwise
% ============================================================================

validate_specific_datetime(CalendarId, Date, StartTime, EndTime, IsValid) :-
    (   is_time_available_on_day(CalendarId, Date, StartTime, EndTime),
        within_working_hours(StartTime, EndTime, 9, 18)
    ->  IsValid = true
    ;   IsValid = false
    ).

% ============================================================================
% PREFERENCE 4: Any available time
% find_alternatives_any_time(CalendarId, Duration, NumSlots, Result)
% Returns list of [StartDateTime, EndDateTime] pairs (next available slots)
% ============================================================================

find_alternatives_any_time(CalendarId, Duration, NumSlots, Result) :-
    % Find N earliest available time slots
    findall(
        slot(StartDT, EndDT),
        (
            between(0, 180, DayOffset),  % Search next 180 days
            between(9, 17, Hour),  % Working hours
            date_offset_future(DayOffset, Date),
            format(atom(StartDT), '~w-~2d:00', [Date, Hour]),
            Add is Hour + 1,
            format(atom(EndDT), '~w-~2d:00', [Date, Add]),
            is_time_available_on_day(CalendarId, Date, StartDT, EndDT)
        ),
        AvailableSlots
    ),
    length(AvailableSlots, TotalAvailable),
    MinToUse is min(NumSlots, TotalAvailable),
    take_n(MinToUse, AvailableSlots, Result).

% ============================================================================
% Main Routing Predicate
% suggest_alternative(EventId, CalendarId, PreferenceType, ConflictEventStart, ConflictEventEnd, NumOptions, Result)
% Routes to appropriate strategy based on preference type
% ============================================================================

suggest_alternative(EventId, CalendarId, PreferenceType, ConflictStart, ConflictEnd, NumOptions, Result) :-
    (   PreferenceType = 1  % Same time, different day
    ->  find_alternatives_same_time(EventId, CalendarId, ConflictStart, ConflictEnd, NumOptions, Result)

    ;   PreferenceType = 2  % Specific day (caller handles day selection)
    ->  Result = preference_requires_user_input  % Signal backend to ask user for day

    ;   PreferenceType = 3  % Specific datetime (caller handles verification)
    ->  Result = preference_requires_user_input  % Signal backend to ask user

    ;   PreferenceType = 4  % Any available time
    ->  find_alternatives_any_time(CalendarId, 60, NumOptions, Result)  % Assume 60 min duration

    ;   Result = error_invalid_preference
    ).

% ============================================================================
% Helper Predicates - Date/Time Utilities
% ============================================================================

% Get today's date (stub - backend provides this)
get_today('2024-01-15').  % Placeholder - should come from context

% Check if date is weekend
is_weekend(DateStr) :-
    day_of_week(DateStr, DayNum),
    (DayNum = 0 ; DayNum = 6).  % 0=Sunday, 6=Saturday

% Add days to date (stub - simplified for Prolog)
date_add_days(DateStr, Days, NewDateStr) :-
    atom_string(DateStr, S),
    % Simplified: just append days to string for now
    % Real implementation would use proper date arithmetic
    atom_concat(DateStr, '_', NewDateStr).

% Calculate day of week (stub)
day_of_week(_, 2).  % Placeholder - all dates return 2 (Tuesday)

% ============================================================================
% Utility Predicates for Backend Integration
% ============================================================================

% Main entry point for checking conflicts
% api_check_conflicts(CalendarId, ProposedStart, ProposedEnd, ConflictList)
api_check_conflicts(CalendarId, ProposedStart, ProposedEnd, ConflictList) :-
    check_conflict(CalendarId, ProposedStart, ProposedEnd, ConflictList).

% Main entry point for finding alternatives by preference
% api_find_alternatives(EventId, CalendarId, Preference, Start, End, Count, Result)
api_find_alternatives(EventId, CalendarId, Preference, Start, End, Count, Result) :-
    suggest_alternative(EventId, CalendarId, Preference, Start, End, Count, Result).

% ============================================================================
% Dynamic Fact Management (for runtime updates)
% ============================================================================

% Add event to knowledge base
add_event(EventId, CalendarId, Title, StartTime, EndTime) :-
    assertz(event(EventId, CalendarId, Title, StartTime, EndTime)).

% Remove event from knowledge base
remove_event(EventId) :-
    retractall(event(EventId, _, _, _, _)).

% Get all events for calendar
get_calendar_events(CalendarId, Events) :-
    findall(event(Id, Title, Start, End), event(Id, CalendarId, Title, Start, End), Events).
