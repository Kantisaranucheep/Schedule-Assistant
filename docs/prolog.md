# Prolog Integration Documentation

The Schedule Assistant uses SWI-Prolog for constraint-based scheduling logic.

## Why Prolog?

Prolog excels at:

1. **Constraint satisfaction** - Finding solutions that meet multiple constraints
2. **Backtracking** - Automatically exploring alternatives when conflicts arise
3. **Declarative rules** - Express "what" not "how"
4. **Pattern matching** - Easily match complex event structures

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Python Backend                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐          ┌──────────────────────────────┐ │
│  │ Prolog Client│          │  apps/prolog/                │ │
│  │              │          │  ├── main.pl                 │ │
│  │  ┌─────────┐ │  spawn   │  ├── kb.pl (knowledge base)  │ │
│  │  │subprocess├─┼─────────▶  └── rules.pl (constraints)  │ │
│  │  └─────────┘ │          │                              │ │
│  │       or     │          └──────────────────────────────┘ │
│  │  ┌─────────┐ │  HTTP                                     │
│  │  │ service ├─┼─────────▶ Prolog HTTP Server (optional)  │
│  │  └─────────┘ │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## Files Structure

```
apps/prolog/
├── main.pl      # Entry point, loads modules, API predicates
├── kb.pl        # Knowledge base (facts: events, calendars, working hours)
├── rules.pl     # Scheduling rules (overlap, free slots, validation)
└── README.md    # Usage documentation
```

## Knowledge Base (`kb.pl`)

Stores facts about the scheduling domain:

### Event Facts

```prolog
%% event(EventId, CalendarId, Title, Start, End, Status, Location)
event('evt-001', 'cal-001', 'Team Meeting', 
      '2024-01-20T10:00:00', '2024-01-20T11:00:00',
      confirmed, 'Room A').
```

### Calendar Facts

```prolog
%% calendar(CalendarId, OwnerId, Name)
calendar('cal-001', 'user-001', 'Work Calendar').
```

### Working Hours

```prolog
%% working_hours(UserId, StartHour, EndHour)
working_hours('user-001', 9, 18).
```

### Buffer Time

```prolog
%% buffer_minutes(UserId, Minutes)
buffer_minutes('user-001', 15).
```

## Rules (`rules.pl`)

### Overlap Detection

```prolog
%% Check if two events overlap
events_overlap(Event1, Event2) :-
    event(_, _, _, S1, E1, _, _) = Event1,
    event(_, _, _, S2, E2, _, _) = Event2,
    S1 @< E2,
    S2 @< E1.

%% Find all conflicts for a proposed time
check_overlap(CalendarId, Start, End, ConflictIds) :-
    findall(
        EventId,
        (
            event(EventId, CalendarId, _, S, E, confirmed, _),
            S @< End,
            Start @< E
        ),
        ConflictIds
    ).
```

### Free Slot Finding

```prolog
%% Find available slots within a date range
find_free_slots(CalendarId, StartDate, EndDate, Duration, Slots) :-
    % Implementation uses working hours and existing events
    % to find gaps of at least Duration minutes
    ...
```

### Working Hours Validation

```prolog
%% Check if a time is within working hours
is_within_working_hours(UserId, Start, End) :-
    working_hours(UserId, WorkStart, WorkEnd),
    extract_hour(Start, StartHour),
    extract_hour(End, EndHour),
    StartHour >= WorkStart,
    EndHour =< WorkEnd.
```

## Python Integration

### Using PrologClient

```python
from app.integrations import PrologClient

# Subprocess mode (default)
client = PrologClient(
    mode="subprocess",
    prolog_path="/path/to/apps/prolog"
)

# Check for conflicts
result = await client.check_conflicts(
    calendar_id="cal-001",
    start_time="2024-01-20T10:30:00",
    end_time="2024-01-20T11:30:00"
)

if result.success:
    if result.data["has_conflicts"]:
        print(f"Conflicts: {result.data['conflicts']}")
    else:
        print("No conflicts!")
```

### Available Methods

```python
# Check for conflicts
result = await client.check_conflicts(calendar_id, start, end)

# Find free slots
result = await client.find_free_slots(
    calendar_id, 
    start_date, 
    end_date, 
    duration_minutes
)

# Raw query
result = await client.query("event(X, 'cal-001', _, _, _, _, _)")
```

## Configuration

### Environment Variables

```bash
# Mode: "subprocess" or "service"
PROLOG_MODE=subprocess

# Path to Prolog files (subprocess mode)
PROLOG_PATH=../../apps/prolog

# Service URL (service mode)
PROLOG_SERVICE_URL=http://localhost:8081
```

### Subprocess Mode

Default mode. Spawns `swipl` process for each query.

**Pros:**
- No separate service to manage
- Simple deployment

**Cons:**
- Higher latency (process startup)
- Not ideal for high-frequency queries

### Service Mode

Runs Prolog as a persistent HTTP service.

**Pros:**
- Lower latency (no startup overhead)
- Better for production

**Cons:**
- Requires SWI-Prolog HTTP server setup
- Additional service to manage

## Docker Support

### Using with Docker Compose

The `docker-compose.yml` includes an optional Prolog service:

```yaml
prolog:
  image: swipl:stable
  volumes:
    - ../apps/prolog:/app:ro
  ports:
    - "8081:8081"
```

Uncomment and set `PROLOG_MODE=service` to use.

## Example Queries

### Interactive Testing

```bash
cd apps/prolog
swipl main.pl

?- check_overlap('cal-001', '2024-01-20T10:30:00', '2024-01-20T11:30:00', X).
X = ['evt-001'].

?- find_free_slots('cal-001', '2024-01-20', '2024-01-26', 60, Slots).
Slots = [...].

?- is_within_working_hours('user-001', '2024-01-20T10:00:00', '2024-01-20T11:00:00').
true.
```

### Command Line

```bash
# Single query
swipl -g "check_overlap('cal-001', '2024-01-20T10:00:00', '2024-01-20T11:00:00', X), print(X)" -t halt main.pl

# Run examples
swipl -g "run_examples" -t halt main.pl
```

## Syncing Data

The Prolog knowledge base can be populated from the PostgreSQL database:

```python
# In backend code
async def sync_events_to_prolog(db: AsyncSession, prolog: PrologClient):
    """Sync database events to Prolog."""
    events = await db.execute(select(Event))
    
    for event in events.scalars():
        await prolog.query(f"""
            assertz(event(
                '{event.id}',
                '{event.calendar_id}',
                '{event.title}',
                '{event.start_time.isoformat()}',
                '{event.end_time.isoformat()}',
                {event.status},
                '{event.location or ""}'
            ))
        """)
```

## Adding New Rules

1. **Define in `rules.pl`:**

```prolog
%% New rule: check if user has too many meetings
too_many_meetings_on_day(UserId, Date, Threshold) :-
    findall(E, (
        event(E, CalId, _, Start, _, confirmed, _),
        calendar(CalId, UserId, _),
        sub_string(Start, 0, 10, _, Date)
    ), Events),
    length(Events, Count),
    Count > Threshold.
```

2. **Export from module:**

```prolog
:- module(rules, [
    ...,
    too_many_meetings_on_day/3
]).
```

3. **Call from Python:**

```python
result = await prolog.query(
    f"too_many_meetings_on_day('{user_id}', '2024-01-20', 5)"
)
```

## Error Handling

The PrologClient handles errors:

| Error | Handling |
|-------|----------|
| Prolog not installed | Raises `PrologNotFoundError` |
| Query syntax error | Returns `PrologResult(success=False, error=...)` |
| Timeout | Configurable timeout, raises `TimeoutError` |
| Service unavailable | Falls back to subprocess if configured |

## Performance Tips

1. **Use specific queries** - Avoid `findall` on entire database
2. **Index facts** - Use `index/1` for frequently queried predicates
3. **Cache results** - Cache static constraint checks
4. **Batch queries** - Combine multiple checks into one query
5. **Use service mode** - For production with high query volume

## Testing

```bash
# Run Prolog unit tests (if using PlUnit)
swipl -g "run_tests" -t halt test_rules.pl

# Test from Python
cd apps/backend
pytest tests/integrations/test_prolog.py -v
```
