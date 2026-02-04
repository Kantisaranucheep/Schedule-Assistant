# Prolog Rules Engine

This folder contains SWI-Prolog files for scheduling rules and constraint validation.

## Files

| File | Purpose |
|------|---------|
| `kb.pl` | Knowledge base facts (events, calendars, working hours) |
| `rules.pl` | Scheduling rules (overlap detection, free slot finding) |
| `main.pl` | Entry point that loads all modules and exports API predicates |

## How the Backend Calls Prolog

The backend integrates with Prolog via **subprocess** (default) or **HTTP service** mode.

### Subprocess Mode (Default)

The Python `PrologClient` spawns `swipl` as a subprocess:

```python
from app.integrations import PrologClient

client = PrologClient(
    mode="subprocess",
    prolog_path="/path/to/apps/prolog"
)

# Check for conflicts
result = await client.check_conflicts(
    calendar_id="cal-001",
    start_time="2024-01-20T10:00:00",
    end_time="2024-01-20T11:00:00"
)
print(result.data)  # {"has_conflicts": true, "conflicts": [...]}
```

### Service Mode (HTTP)

Optionally run Prolog as a service with SWI-Prolog's HTTP server:

```python
client = PrologClient(
    mode="service",
    service_url="http://localhost:8081"
)
```

## Available Predicates

### From `kb.pl`

```prolog
% Core facts
event(EventId, CalendarId, Title, Start, End, Status, Location).
calendar(CalendarId, OwnerId, Name).
working_hours(UserId, StartHour, EndHour).
buffer_minutes(UserId, Minutes).

% CRUD operations
add_event(Id, CalId, Title, Start, End, Status, Location).
remove_event(Id).
move_event(Id, NewStart, NewEnd).
list_events(CalId, Events).
list_events_in_range(CalId, RangeStart, RangeEnd, Events).
```

### From `rules.pl`

```prolog
% Overlap detection
events_overlap(Event1, Event2).
check_overlap(CalendarId, Start, End, ConflictingEventIds).
check_event_conflicts(EventId, CalId, Start, End, Conflicts).

% Working hours validation
is_within_working_hours(UserId, Start, End).
validate_event_time(CalId, UserId, Start, End, Result).
% Result = ok | overlap(Conflicts) | outside_hours

% Free slot finding
find_free_slots(CalendarId, StartDate, EndDate, DurationMinutes, Slots).
slot_available(CalendarId, Start, End, IsAvailable).
```

### From `main.pl` (API wrappers)

```prolog
% JSON-friendly API predicates
api_check_overlap(CalendarId, Start, End, JSONResult).
api_find_free_slots(CalendarId, StartDate, EndDate, Duration, JSONResult).
api_validate_event(CalendarId, UserId, Start, End, JSONResult).
```

## Running Locally

### Interactive Mode

```bash
cd apps/prolog
swipl main.pl
```

Then run examples:

```prolog
?- run_examples.
```

### Query from Command Line

```bash
swipl -g "check_overlap('cal-001', '2024-01-20T10:00:00', '2024-01-20T11:00:00', X), print(X)" -t halt main.pl
```

## Docker Deployment

The Prolog module can run as a Docker container:

```dockerfile
FROM swipl:stable
WORKDIR /app
COPY . /app
EXPOSE 8081
CMD ["swipl", "main.pl"]
```

Or use the included `docker-compose.yml` which includes an optional Prolog service.

## Adding New Rules

1. **Define facts** in `kb.pl`:
   ```prolog
   :- dynamic my_fact/2.
   my_fact(key, value).
   ```

2. **Define rules** in `rules.pl`:
   ```prolog
   my_rule(Input, Output) :-
       my_fact(Input, Output),
       validate(Output).
   ```

3. **Export from module** if needed:
   ```prolog
   :- module(rules, [..., my_rule/2]).
   ```

## Integration with Agent Module

The agent module can call Prolog to:

1. **Validate intents** before execution
2. **Check constraints** that are complex to express in Python
3. **Find optimal slots** using Prolog's backtracking

Example flow:

```
User: "Schedule a meeting tomorrow at 2pm"
  → Agent parses intent: {type: "create_event", time: "2024-01-21T14:00:00", ...}
  → Prolog validates: check_overlap('cal-001', '2024-01-21T14:00:00', '2024-01-21T15:00:00', [])
  → No conflicts → Backend creates event
```

## Troubleshooting

### "Module not found" error

Ensure you're in the correct directory:
```bash
cd apps/prolog
swipl main.pl
```

### "Unknown procedure" error

Check that the predicate is exported from its module:
```prolog
:- module(kb, [..., missing_predicate/2]).
```

### Performance issues

For large datasets, consider:
- Adding indexes via `index/1` directive
- Using more specific queries
- Running Prolog as a persistent service
