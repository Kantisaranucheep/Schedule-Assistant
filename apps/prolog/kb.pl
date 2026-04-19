%% apps/prolog/kb.pl'
%% ============================================================================
%% Knowledge Base — Schedule Assistant
%% ============================================================================
%%
%% This module implements Knowledge Representation and Reasoning (KRR) for
%% calendar scheduling. Knowledge is organized into:
%%
%%   1. Domain Facts     — ground truths about events, calendars, users
%%   2. Taxonomic Knowledge — event categories, priority levels
%%   3. Constraint Declarations — what constitutes a valid schedule
%%   4. Availability Knowledge  — when users are available
%%   5. Fact Management  — KB manipulation (assert/retract)
%%
%% All knowledge is represented as Prolog facts (first-order logic atoms),
%% enabling inference and reasoning in rules.pl.
%% ============================================================================

:- module(kb, [
    %% --- Domain Facts ---
    event/7,           % event(Id, CalendarId, Title, StartTime, EndTime, Status, CreatedBy)
    calendar/3,        % calendar(Id, UserId, Timezone)
    user_setting/3,    % user_setting(UserId, Key, Value)
    working_hours/3,   % working_hours(UserId, StartTime, EndTime)
    buffer_minutes/2,  % buffer_minutes(UserId, Minutes)

    %% --- Taxonomic Knowledge ---
    event_category/2,      % event_category(EventType, ParentCategory)
    event_type/2,          % event_type(EventId, Type)
    priority_level/2,      % priority_level(Level, NumericValue)
    event_priority/2,      % event_priority(EventId, Level)
    default_priority/2,    % default_priority(EventType, Level)

    %% --- Constraint Declarations (knowledge about what is valid) ---
    scheduling_constraint/1,   % scheduling_constraint(ConstraintName)
    constraint_applies_to/2,   % constraint_applies_to(ConstraintName, EventType)

    %% --- Availability Knowledge ---
    user_available/4,      % user_available(UserId, Day, StartTime, EndTime)
    day_type/2,            % day_type(Day, Type)  e.g., weekday/weekend/holiday

    %% --- Fact Management ---
    add_event/7,
    remove_event/1,
    move_event/3,
    list_events/2,
    list_events_in_range/4
]).

%% Dynamic predicates — can be modified at runtime via reasoning
:- dynamic event/7.
:- dynamic calendar/3.
:- dynamic user_setting/3.
:- dynamic working_hours/3.
:- dynamic buffer_minutes/2.
:- dynamic event_type/2.
:- dynamic event_priority/2.
:- dynamic user_available/4.
:- dynamic day_type/2.

%% ============================================================================
%% 1. Domain Facts (Ground Truths)
%% ============================================================================

%% Calendars — ownership relation between users and calendars
calendar('cal-001', 'user-001', 'Asia/Bangkok').
calendar('cal-002', 'user-001', 'Asia/Bangkok').

%% User preference facts
working_hours('user-001', '09:00', '18:00').
buffer_minutes('user-001', 10).
user_setting('user-001', default_duration, 60).

%% Events — the core scheduled activities
event('evt-001', 'cal-001', 'Team Meeting',        '2024-01-20T10:00:00', '2024-01-20T11:00:00', confirmed, user).
event('evt-002', 'cal-001', 'Lunch',                '2024-01-20T12:00:00', '2024-01-20T13:00:00', confirmed, user).
event('evt-003', 'cal-001', 'Project Review',       '2024-01-20T14:00:00', '2024-01-20T15:30:00', confirmed, agent).
event('evt-004', 'cal-001', 'Dentist Appointment',  '2024-01-21T09:00:00', '2024-01-21T10:00:00', tentative, user).

%% ============================================================================
%% 2. Taxonomic Knowledge (Event Categories & Priorities)
%% ============================================================================
%%
%% Category hierarchy: models an "is-a" relationship.
%%   event_category(ChildType, ParentCategory).
%%
%% This allows reasoning like:
%%   "Is a 'meeting' a kind of 'work' activity?" → Yes, via the taxonomy.

event_category(meeting, work).
event_category(class, academic).
event_category(study, academic).
event_category(exam, academic).
event_category(deadline, academic).
event_category(exercise, personal).
event_category(social, personal).
event_category(appointment, personal).
event_category(travel, personal).
event_category(party, social_event).
event_category(work, obligation).
event_category(academic, obligation).
event_category(personal, lifestyle).
event_category(social_event, lifestyle).

%% Priority levels — ordered symbolic values with numeric weights.
%% These are domain knowledge facts, not computed values.
priority_level(critical, 10).
priority_level(high, 8).
priority_level(medium, 5).
priority_level(low, 3).
priority_level(optional, 1).

%% Default priority per event type — domain expertise as facts.
default_priority(exam, critical).
default_priority(deadline, critical).
default_priority(meeting, high).
default_priority(class, high).
default_priority(appointment, high).
default_priority(work, medium).
default_priority(study, medium).
default_priority(exercise, low).
default_priority(social, low).
default_priority(party, optional).
default_priority(travel, medium).

%% Per-event type and priority (populated at runtime)
event_type('evt-001', meeting).
event_type('evt-002', social).
event_type('evt-003', meeting).
event_type('evt-004', appointment).

event_priority('evt-001', high).
event_priority('evt-002', low).
event_priority('evt-003', high).
event_priority('evt-004', high).

%% ============================================================================
%% 3. Constraint Declarations (Knowledge About What Is Valid)
%% ============================================================================
%%
%% Constraints are declared as FACTS — they represent domain knowledge
%% about what constitutes a valid schedule. Rules in rules.pl CHECK these
%% constraints; the KB only DECLARES them.
%%
%%   scheduling_constraint(Name)          — a named constraint exists
%%   constraint_applies_to(Name, Type)    — which event types it governs

scheduling_constraint(no_time_overlap).
scheduling_constraint(within_working_hours).
scheduling_constraint(sufficient_buffer).
scheduling_constraint(not_cancelled).
scheduling_constraint(positive_duration).

%% Which constraints apply to which event types
%% 'all' means the constraint applies universally
constraint_applies_to(no_time_overlap, all).
constraint_applies_to(within_working_hours, work).
constraint_applies_to(within_working_hours, academic).
constraint_applies_to(sufficient_buffer, all).
constraint_applies_to(not_cancelled, all).
constraint_applies_to(positive_duration, all).

%% ============================================================================
%% 4. Availability Knowledge
%% ============================================================================
%%
%% Explicit user availability windows, beyond just working_hours.
%% user_available(UserId, DayPattern, StartTime, EndTime)
%%   DayPattern can be: weekday, weekend, monday, tuesday, ..., or a date atom.

user_available('user-001', weekday, '09:00', '18:00').
user_available('user-001', weekend, '10:00', '16:00').

day_type(monday, weekday).
day_type(tuesday, weekday).
day_type(wednesday, weekday).
day_type(thursday, weekday).
day_type(friday, weekday).
day_type(saturday, weekend).
day_type(sunday, weekend).

%% ============================================================================
%% 5. Fact Management Predicates
%% ============================================================================

%% Add a new event to the knowledge base
add_event(Id, CalendarId, Title, Start, End, Status, CreatedBy) :-
    \+ event(Id, _, _, _, _, _, _),
    assertz(event(Id, CalendarId, Title, Start, End, Status, CreatedBy)).

%% Remove an event from the knowledge base
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
