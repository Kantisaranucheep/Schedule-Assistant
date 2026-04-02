/**
 * Events API Service
 * Handles all event-related API calls to the backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface EventResponse {
  id: string;
  calendar_id: string;
  title: string;
  start_time: string; // ISO datetime
  end_time: string;
  all_day: boolean;
  location: string | null;
  notes: string | null;
  color: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface EventCreateRequest {
  calendar_id: string;
  title: string;
  start_time: string;
  end_time: string;
  all_day?: boolean;
  location?: string;
  notes?: string;
  color?: string;
}

export interface CalendarResponse {
  id: string;
  user_id: string;
  name: string;
  color: string;
  timezone: string;
  created_at: string;
  updated_at: string;
}

/**
 * Fetch events for a calendar within optional date range
 */
export async function fetchEvents(
  calendarId: string,
  startDate?: Date,
  endDate?: Date
): Promise<EventResponse[]> {
  const params = new URLSearchParams({ calendar_id: calendarId });
  if (startDate) params.append("start_date", startDate.toISOString());
  if (endDate) params.append("end_date", endDate.toISOString());

  const res = await fetch(`${API_BASE}/events?${params}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch events: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Create a new event
 */
export async function createEvent(
  event: EventCreateRequest,
  checkConflicts: boolean = true
): Promise<EventResponse> {
  const params = new URLSearchParams({ check_conflicts: String(checkConflicts) });
  
  const res = await fetch(`${API_BASE}/events?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail?.message || error.detail || "Failed to create event");
  }
  return res.json();
}

/**
 * Delete an event
 */
export async function deleteEvent(eventId: string, soft: boolean = true): Promise<void> {
  const params = new URLSearchParams({ soft: String(soft) });
  
  const res = await fetch(`${API_BASE}/events/${eventId}?${params}`, {
    method: "DELETE",
  });
  
  if (!res.ok) {
    throw new Error(`Failed to delete event: ${res.statusText}`);
  }
}

/**
 * Fetch calendars for a user
 */
export async function fetchCalendars(userId: string): Promise<CalendarResponse[]> {
  const params = new URLSearchParams({ user_id: userId });
  
  const res = await fetch(`${API_BASE}/calendars?${params}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch calendars: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Create a new calendar for a user
 */
export async function createCalendar(
  userId: string,
  name: string = "My Calendar",
  color: string = "#3B82F6"
): Promise<CalendarResponse> {
  const res = await fetch(`${API_BASE}/calendars`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      name,
      color,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    }),
  });
  
  if (!res.ok) {
    throw new Error(`Failed to create calendar: ${res.statusText}`);
  }
  return res.json();
}