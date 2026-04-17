/**
 * Transform API events to frontend EventMap format
 */

import { Ev, EventMap, Kind } from "../types";
import { EventResponse, TaskResponse, CategoryResponse } from "../services/events.api";

/**
 * Convert ISO datetime to minutes from midnight in LOCAL timezone
 */
function dateToMinutes(dateStr: string): number {
  const date = new Date(dateStr);
  // getHours/getMinutes already return local time
  return date.getHours() * 60 + date.getMinutes();
}

/**
 * Get date key (YYYY-MM-DD) from ISO datetime in LOCAL timezone
 */
function getDateKey(dateStr: string): string {
  const date = new Date(dateStr);
  // Use local date components, not UTC
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

/**
 * Transform a single API event to frontend Ev format
 */
export function transformApiEventToEv(
  apiEvent: EventResponse,
  categories: CategoryResponse[]
): Ev {
  // Find the category to get its color
  const category = categories.find(c => c.id === apiEvent.category_id);
  const color = category?.color || "#3B82F6"; // Default blue if no category

  return {
    id: apiEvent.id,
    kind: "event" as Kind,
    allDay: apiEvent.all_day,
    startMin: dateToMinutes(apiEvent.start_time),
    endMin: dateToMinutes(apiEvent.end_time),
    title: apiEvent.title,
    color: color,
    categoryId: apiEvent.category_id || undefined,
    location: apiEvent.location || "",
    notes: apiEvent.notes || "",
    collaborators: apiEvent.collaborator_usernames || [],
  };
}

/**
 * Transform a single API task to frontend Ev format
 */
export function transformApiTaskToEv(
  apiTask: TaskResponse,
  categories: CategoryResponse[]
): Ev {
  // Find the category to get its color
  const category = categories.find(c => c.id === apiTask.category_id);
  const color = category?.color || "#3B82F6"; // Default blue if no category

  return {
    id: apiTask.id,
    kind: "task" as Kind,
    allDay: true, // Tasks are always "all day"
    startMin: 0,
    endMin: 0,
    title: apiTask.title,
    color: color,
    categoryId: apiTask.category_id || undefined,
    location: apiTask.location || "",
    notes: apiTask.notes || "",
  };
}

/**
 * Transform array of API events to EventMap indexed by date key
 */
export function transformApiEventsToEventMap(
  apiEvents: EventResponse[],
  categories: CategoryResponse[]
): EventMap {
  const eventMap: EventMap = {};

  for (const apiEvent of apiEvents) {
    const dateKey = getDateKey(apiEvent.start_time);
    const frontendEvent = transformApiEventToEv(apiEvent, categories);

    if (!eventMap[dateKey]) {
      eventMap[dateKey] = [];
    }
    eventMap[dateKey].push(frontendEvent);
  }

  // Sort events within each day by start time
  for (const dateKey of Object.keys(eventMap)) {
    eventMap[dateKey].sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
  }

  return eventMap;
}

/**
 * Transform array of API tasks to EventMap indexed by date key
 */
export function transformApiTasksToEventMap(
  apiTasks: TaskResponse[],
  categories: CategoryResponse[]
): EventMap {
  const eventMap: EventMap = {};

  for (const apiTask of apiTasks) {
    const dateKey = apiTask.date; // Tasks already have YYYY-MM-DD format
    const frontendTask = transformApiTaskToEv(apiTask, categories);

    if (!eventMap[dateKey]) {
      eventMap[dateKey] = [];
    }
    eventMap[dateKey].push(frontendTask);
  }

  return eventMap;
}

/**
 * Merge events and tasks into a single EventMap
 */
export function mergeEventsAndTasks(
  events: EventMap,
  tasks: EventMap
): EventMap {
  const merged: EventMap = { ...events };

  for (const [dateKey, taskList] of Object.entries(tasks)) {
    if (!merged[dateKey]) {
      merged[dateKey] = [];
    }
    merged[dateKey] = [...merged[dateKey], ...taskList];
    // Sort by kind (tasks first) then by start time
    merged[dateKey].sort((a, b) => {
      if (a.kind === "task" && b.kind !== "task") return -1;
      if (a.kind !== "task" && b.kind === "task") return 1;
      return (a.startMin ?? 0) - (b.startMin ?? 0);
    });
  }

  return merged;
}

/**
 * Merge new events into existing EventMap (for incremental updates)
 */
export function mergeEventsIntoMap(
  existingMap: EventMap,
  newEvents: EventResponse[],
  categories: CategoryResponse[]
): EventMap {
  const merged = { ...existingMap };
  
  for (const apiEvent of newEvents) {
    const dateKey = getDateKey(apiEvent.start_time);
    const frontendEvent = transformApiEventToEv(apiEvent, categories);
    
    if (!merged[dateKey]) {
      merged[dateKey] = [];
    }
    
    // Check if event already exists (by ID)
    const existingIndex = merged[dateKey].findIndex(e => e.id === frontendEvent.id);
    if (existingIndex >= 0) {
      merged[dateKey][existingIndex] = frontendEvent;
    } else {
      merged[dateKey].push(frontendEvent);
    }
    
    // Sort by start time
    merged[dateKey].sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
  }
  
  return merged;
}