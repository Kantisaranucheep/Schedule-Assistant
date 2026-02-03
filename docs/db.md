# Database Schema Documentation

## Overview

The Schedule Assistant uses PostgreSQL as its database. All tables use UUID primary keys and `timestamptz` for timestamps.

## Entity Relationship Diagram

```
┌──────────────────┐
│      users       │
├──────────────────┤
│ id (PK)          │
│ name             │
│ email (unique)   │
│ created_at       │
└────────┬─────────┘
         │
         │ 1:1
         ▼
┌──────────────────┐
│  user_settings   │
├──────────────────┤
│ user_id (PK,FK)  │
│ timezone         │
│ default_duration │
│ buffer_min       │
│ preferences      │
└──────────────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐      ┌──────────────────┐
│    calendars     │      │   event_types    │
├──────────────────┤      ├──────────────────┤
│ id (PK)          │      │ id (PK)          │
│ user_id (FK)     │      │ user_id (FK)     │
│ name             │      │ name             │
│ timezone         │      │ color            │
│ created_at       │      │ default_duration │
└────────┬─────────┘      └────────┬─────────┘
         │                         │
         │ 1:N                     │ 0..1:N
         ▼                         │
┌──────────────────────────────────┘
│
▼
┌──────────────────┐
│     events       │
├──────────────────┤
│ id (PK)          │
│ calendar_id (FK) │
│ type_id (FK)     │
│ title            │
│ description      │
│ location         │
│ start_at         │
│ end_at           │
│ status           │
│ created_by       │
└──────────────────┘

┌──────────────────┐
│  chat_sessions   │
├──────────────────┤
│ id (PK)          │
│ user_id (FK)     │
│ title            │
│ created_at       │
└────────┬─────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐
│  chat_messages   │
├──────────────────┤
│ id (PK)          │
│ session_id (FK)  │
│ role             │
│ content          │
│ extracted_json   │
│ action_json      │
│ confidence       │
│ created_at       │
└──────────────────┘
```

## Tables

### users

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY, DEFAULT gen_random_uuid() |
| name | text | |
| email | text | UNIQUE, NOT NULL |
| created_at | timestamptz | DEFAULT now() |

### calendars

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY, DEFAULT gen_random_uuid() |
| user_id | uuid | FOREIGN KEY -> users(id) ON DELETE CASCADE |
| name | text | NOT NULL |
| timezone | text | |
| created_at | timestamptz | DEFAULT now() |

### event_types

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY, DEFAULT gen_random_uuid() |
| user_id | uuid | FOREIGN KEY -> users(id) ON DELETE CASCADE |
| name | text | NOT NULL |
| color | text | |
| default_duration_min | int | |
| created_at | timestamptz | DEFAULT now() |

**Unique Constraint:** `(user_id, name)`

### events

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY, DEFAULT gen_random_uuid() |
| calendar_id | uuid | FOREIGN KEY -> calendars(id) ON DELETE CASCADE |
| type_id | uuid | FOREIGN KEY -> event_types(id) ON DELETE SET NULL, NULLABLE |
| title | text | NOT NULL |
| description | text | |
| location | text | |
| start_at | timestamptz | NOT NULL |
| end_at | timestamptz | NOT NULL |
| status | text | NOT NULL, DEFAULT 'confirmed', CHECK IN ('confirmed', 'tentative', 'cancelled') |
| created_by | text | NOT NULL, DEFAULT 'user', CHECK IN ('user', 'agent') |
| created_at | timestamptz | DEFAULT now() |
| updated_at | timestamptz | DEFAULT now() |

**Check Constraint:** `end_at > start_at`

**Indexes:**
- `(calendar_id, start_at)`
- `(calendar_id, start_at, end_at)`

### user_settings

| Column | Type | Constraints |
|--------|------|-------------|
| user_id | uuid | PRIMARY KEY, FOREIGN KEY -> users(id) ON DELETE CASCADE |
| timezone | text | DEFAULT 'Asia/Bangkok' |
| default_duration_min | int | DEFAULT 60 |
| buffer_min | int | DEFAULT 10 |
| preferences | jsonb | NOT NULL, DEFAULT '{}' |
| created_at | timestamptz | DEFAULT now() |
| updated_at | timestamptz | DEFAULT now() |

### chat_sessions

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY, DEFAULT gen_random_uuid() |
| user_id | uuid | FOREIGN KEY -> users(id) ON DELETE CASCADE |
| title | text | |
| created_at | timestamptz | DEFAULT now() |

### chat_messages

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PRIMARY KEY, DEFAULT gen_random_uuid() |
| session_id | uuid | FOREIGN KEY -> chat_sessions(id) ON DELETE CASCADE |
| role | text | NOT NULL, CHECK IN ('user', 'assistant', 'system', 'tool') |
| content | text | NOT NULL |
| extracted_json | jsonb | |
| action_json | jsonb | |
| confidence | numeric(4,3) | |
| created_at | timestamptz | DEFAULT now() |

**Index:** `(session_id, created_at)`

## Migrations

Migrations are managed with Alembic. Common commands:

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```
