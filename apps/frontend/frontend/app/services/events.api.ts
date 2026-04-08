/**
 * Events API Service
 * Handles all event-related API calls to the backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CategoryResponse {
  id: string;
  calendar_id: string;
  name: string;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface EventResponse {
  id: string;
  calendar_id: string;
  title: string;
  start_time: string; // ISO datetime
  end_time: string;
  all_day: boolean;
  location: string | null;
  notes: string | null;
  category_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TaskResponse {
  id: string;
  calendar_id: string;
  title: string;
  date: string; // YYYY-MM-DD format
  category_id: string | null;
  location: string | null;
  notes: string | null;
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
  category_id?: string;
  timezone?: string; // IANA timezone e.g. "Asia/Bangkok"
}

export interface TaskCreateRequest {
  calendar_id: string;
  title: string;
  date: string; // YYYY-MM-DD format
  category_id?: string;
  location?: string;
  notes?: string;
}

export interface CategoryCreateRequest {
  calendar_id: string;
  name: string;
  color: string;
}

export interface TaskUpdateRequest {
  title?: string;
  date?: string;
  category_id?: string;
  location?: string;
  notes?: string;
  status?: string;
}

export interface EventUpdateRequest {
  title?: string;
  start_time?: string;
  end_time?: string;
  all_day?: boolean;
  location?: string;
  notes?: string;
  category_id?: string;
  timezone?: string;
}

/**
 * Get the user's timezone from the browser
 */
export function getUserTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/**
 * Format a local Date to ISO string preserving the local timezone offset
 * e.g., "2024-04-03T09:00:00+07:00" instead of "2024-04-03T02:00:00.000Z"
 */
export function toLocalISOString(date: Date): string {
  const offset = -date.getTimezoneOffset();
  const sign = offset >= 0 ? '+' : '-';
  const absOffset = Math.abs(offset);
  const hours = String(Math.floor(absOffset / 60)).padStart(2, '0');
  const minutes = String(absOffset % 60).padStart(2, '0');
  
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  const second = String(date.getSeconds()).padStart(2, '0');
  
  return `${year}-${month}-${day}T${hour}:${minute}:${second}${sign}${hours}:${minutes}`;
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
 * Update an event
 */
export async function updateEvent(
  eventId: string,
  event: EventUpdateRequest
): Promise<EventResponse> {
  const res = await fetch(`${API_BASE}/events/${eventId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail?.message || error.detail || "Failed to update event");
  }
  return res.json();
}

/**
 * Fetch categories for a calendar
 */
export async function fetchCategories(calendarId: string): Promise<CategoryResponse[]> {
  const params = new URLSearchParams({ calendar_id: calendarId });
  
  const res = await fetch(`${API_BASE}/categories?${params}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch categories: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Create a new category
 */
export async function createCategory(category: CategoryCreateRequest): Promise<CategoryResponse> {
  const res = await fetch(`${API_BASE}/categories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(category),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail?.message || error.detail || "Failed to create category");
  }
  return res.json();
}

/**
 * Delete a category
 */
export async function deleteCategory(categoryId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/categories/${categoryId}`, {
    method: "DELETE",
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail?.message || error.detail || "Failed to delete category");
  }
}

/**
 * Create default categories for a calendar
 */
export async function createDefaultCategories(calendarId: string): Promise<CategoryResponse[]> {
  const params = new URLSearchParams({ calendar_id: calendarId });
  
  const res = await fetch(`${API_BASE}/categories/defaults?${params}`, {
    method: "POST",
  });
  
  if (!res.ok) {
    throw new Error(`Failed to create default categories: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Fetch tasks for a calendar within optional date range
 */
export async function fetchTasks(
  calendarId: string,
  startDate?: Date,
  endDate?: Date
): Promise<TaskResponse[]> {
  const params = new URLSearchParams({ calendar_id: calendarId });
  if (startDate) params.append("start_date", startDate.toISOString().split('T')[0]);
  if (endDate) params.append("end_date", endDate.toISOString().split('T')[0]);

  const res = await fetch(`${API_BASE}/tasks?${params}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch tasks: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Create a new task
 */
export async function createTask(task: TaskCreateRequest): Promise<TaskResponse> {
  const res = await fetch(`${API_BASE}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(task),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail?.message || error.detail || "Failed to create task");
  }
  return res.json();
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string, soft: boolean = true): Promise<void> {
  const params = new URLSearchParams({ soft: String(soft) });
  
  const res = await fetch(`${API_BASE}/tasks/${taskId}?${params}`, {
    method: "DELETE",
  });
  
  if (!res.ok) {
    throw new Error(`Failed to delete task: ${res.statusText}`);
  }
}

/**
 * Update a task
 */
export async function updateTask(
  taskId: string,
  task: TaskUpdateRequest
): Promise<TaskResponse> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(task),
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail?.message || error.detail || "Failed to update task");
  }
  return res.json();
}

/**
 * Mark a task as completed
 */
export async function completeTask(taskId: string): Promise<TaskResponse> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/complete`, {
    method: "POST",
  });
  
  if (!res.ok) {
    throw new Error(`Failed to complete task: ${res.statusText}`);
  }
  return res.json();
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