%% apps/backend/app/chat/prolog/scheduler.pl
%% ============================================================================
%% Schedule Assistant - Prolog Knowledge Base
%% ============================================================================
%% 
%% This module implements First-Order Logic predicates for:
%% - Time conflict detection using Resolution
%% - Free slot finding using Constraint Solving
%% - Logical Inference for scheduling decisions
%%
%% Knowledge Representation:
%% - Events are represented as facts with time intervals
%% - Conflicts are detected using interval overlap logic
%% - Free slots are found by constraint satisfaction over time domains
%% ============================================================================

:- module(scheduler, [
    check_conflict/5,
    find_free_slots/7,
    find_free_days/7,
    time_to_minutes/3,
    minutes_to_time/3,
    events_overlap/4,
    slot_conflicts_with_events/3
]).

%% ============================================================================
%% Knowledge Base: Time Representation
%% ============================================================================
%% 
%% Time is represented in minutes from midnight (0-1439)
%% This allows for easy arithmetic operations and comparisons
%%
%% Predicates use First-Order Logic with:
%% - Universal quantification (∀) via forall/2
%% - Existential quantification (∃) via member/2
%% - Logical connectives (∧, ∨, ¬) via Prolog's ,/;/\+

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
%% If we can't, the original query is true (conflict exists)

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
%% Problem: Find time slots of duration D that don't conflict with existing events
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
%% Find free slots:
%% ?- find_free_slots(60, [event(e1, "M", 9, 0, 10, 0)], 8, 0, 18, 0, S).
%% S = [slot(8, 0, 9, 0), slot(10, 0, 11, 0), ...]
