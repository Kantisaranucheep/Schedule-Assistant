%% apps/prolog/kb.pl
%% Knowledge Base - Facts for the Schedule Assistant
%% This file contains dynamic facts that represent calendar data

:- module(kb, [
    event/7,           % event(Id, CalendarId, Title, StartTime, EndTime, Status, CreatedBy)
    calendar/3,        % calendar(Id, UserId, Timezone)
    user_setting/3,    % user_setting(UserId, Key, Value)
    working_hours/3,   % working_hours(UserId, StartTime, EndTime)
    buffer_minutes/2   % buffer_minutes(UserId, Minutes)
]).

%% Dynamic predicates - can be modified at runtime
:- dynamic event/7.
:- dynamic calendar/3.
:- dynamic user_setting/3.
:- dynamic working_hours/3.
:- dynamic buffer_minutes/2.

%% ============================================================================
%% Sample Facts (for testing)
%% ============================================================================

%% Sample users and calendars
calendar('cal-001', 'user-001', 'Asia/Bangkok').
calendar('cal-002', 'user-001', 'Asia/Bangkok').

%% User settings
working_hours('user-001', '09:00', '18:00').
buffer_minutes('user-001', 10).
user_setting('user-001', default_duration, 60).

%% Sample events
%% event(Id, CalendarId, Title, StartTime, EndTime, Status, CreatedBy)
event('evt-001', 'cal-001', 'Team Meeting', '2024-01-20T10:00:00', '2024-01-20T11:00:00', confirmed, user).
event('evt-002', 'cal-001', 'Lunch', '2024-01-20T12:00:00', '2024-01-20T13:00:00', confirmed, user).
event('evt-003', 'cal-001', 'Project Review', '2024-01-20T14:00:00', '2024-01-20T15:30:00', confirmed, agent).
event('evt-004', 'cal-001', 'Dentist Appointment', '2024-01-21T09:00:00', '2024-01-21T10:00:00', tentative, user).

%% ============================================================================
%% Fact Management Predicates
%% ============================================================================

%% Add a new event
add_event(Id, CalendarId, Title, Start, End, Status, CreatedBy) :-
    \+ event(Id, _, _, _, _, _, _),  % Ensure no duplicate ID
    assertz(event(Id, CalendarId, Title, Start, End, Status, CreatedBy)).

%% Remove an event by ID
remove_event(Id) :-
    retract(event(Id, _, _, _, _, _, _)).

%% Update event status
update_event_status(Id, NewStatus) :-
    retract(event(Id, CalId, Title, Start, End, _, CreatedBy)),
    assertz(event(Id, CalId, Title, Start, End, NewStatus, CreatedBy)).

%% Move event to new time
move_event(Id, NewStart, NewEnd) :-
    retract(event(Id, CalId, Title, _, _, Status, CreatedBy)),
    assertz(event(Id, CalId, Title, NewStart, NewEnd, Status, CreatedBy)).

%% List all events for a calendar
list_events(CalendarId, Events) :-
    findall(
        event(Id, CalendarId, Title, Start, End, Status, CreatedBy),
        event(Id, CalendarId, Title, Start, End, Status, CreatedBy),
        Events
    ).

%% List events in a time range
list_events_in_range(CalendarId, RangeStart, RangeEnd, Events) :-
    findall(
        event(Id, CalendarId, Title, Start, End, Status, CreatedBy),
        (
            event(Id, CalendarId, Title, Start, End, Status, CreatedBy),
            Start @>= RangeStart,
            End @=< RangeEnd
        ),
        Events
    ).
