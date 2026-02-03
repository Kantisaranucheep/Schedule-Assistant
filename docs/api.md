# API Documentation

## Overview

The Schedule Assistant API is a RESTful API built with FastAPI. All endpoints return JSON responses.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API uses `user_id` query parameters for user identification. Production should implement proper JWT authentication.

---

## Endpoints

### Health

#### GET /health

Check API health status.

**Response:**
```json
{
  "status": "ok"
}
```

---

### Calendars

#### GET /calendars

List calendars for a user.

**Query Parameters:**
- `user_id` (UUID, required): User ID

**Response:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "name": "Personal",
    "timezone": "Asia/Bangkok",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### POST /calendars

Create a new calendar.

**Request Body:**
```json
{
  "user_id": "uuid",
  "name": "Work",
  "timezone": "Asia/Bangkok"
}
```

**Response:** Created calendar object

---

### Events

#### GET /events

List events within a date range.

**Query Parameters:**
- `calendar_id` (UUID, required): Calendar ID
- `from` (ISO datetime, required): Start of range
- `to` (ISO datetime, required): End of range

**Response:**
```json
[
  {
    "id": "uuid",
    "calendar_id": "uuid",
    "type_id": "uuid",
    "title": "Team Meeting",
    "description": "Weekly sync",
    "location": "Room 101",
    "start_at": "2024-01-01T10:00:00Z",
    "end_at": "2024-01-01T11:00:00Z",
    "status": "confirmed",
    "created_by": "user",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### POST /events

Create a new event.

**Request Body:**
```json
{
  "calendar_id": "uuid",
  "type_id": "uuid (optional)",
  "title": "Team Meeting",
  "description": "Weekly sync (optional)",
  "location": "Room 101 (optional)",
  "start_at": "2024-01-01T10:00:00Z",
  "end_at": "2024-01-01T11:00:00Z",
  "status": "confirmed",
  "created_by": "user"
}
```

**Error Response (409 Conflict):**
```json
{
  "detail": {
    "message": "Event conflicts with existing events",
    "conflicting_event_ids": ["uuid1", "uuid2"]
  }
}
```

#### PUT /events/{event_id}

Update an existing event.

**Request Body:** Same as POST (partial updates supported)

#### DELETE /events/{event_id}

Delete an event.

**Response:** 204 No Content

---

### Availability

#### GET /availability

Get free time slots for a specific date.

**Query Parameters:**
- `calendar_id` (UUID, required): Calendar ID
- `date` (YYYY-MM-DD, required): Date to check

**Response:**
```json
{
  "date": "2024-01-01",
  "calendar_id": "uuid",
  "slots": [
    {
      "start_at": "2024-01-01T09:00:00+07:00",
      "end_at": "2024-01-01T10:00:00+07:00"
    },
    {
      "start_at": "2024-01-01T11:00:00+07:00",
      "end_at": "2024-01-01T12:00:00+07:00"
    }
  ]
}
```

---

### Chat

#### POST /chat/sessions

Create a new chat session.

**Request Body:**
```json
{
  "user_id": "uuid",
  "title": "Schedule planning (optional)"
}
```

#### GET /chat/sessions

List chat sessions for a user.

**Query Parameters:**
- `user_id` (UUID, required): User ID

#### GET /chat/sessions/{id}/messages

Get all messages in a chat session.

#### POST /chat/sessions/{id}/messages

Add a message to a chat session.

**Request Body:**
```json
{
  "role": "user",
  "content": "Schedule a meeting tomorrow at 2pm",
  "extracted_json": {},
  "action_json": {},
  "confidence": 0.95
}
```

---

### Settings

#### GET /settings

Get user settings.

**Query Parameters:**
- `user_id` (UUID, required): User ID

**Response:**
```json
{
  "user_id": "uuid",
  "timezone": "Asia/Bangkok",
  "default_duration_min": 60,
  "buffer_min": 10,
  "preferences": {
    "working_hours_start": "09:00",
    "working_hours_end": "18:00"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### PUT /settings

Update user settings.

**Query Parameters:**
- `user_id` (UUID, required): User ID

**Request Body:**
```json
{
  "timezone": "Asia/Bangkok",
  "default_duration_min": 60,
  "buffer_min": 15,
  "preferences": {
    "working_hours_start": "08:00",
    "working_hours_end": "17:00"
  }
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `204` - No Content
- `400` - Bad Request
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `500` - Internal Server Error
