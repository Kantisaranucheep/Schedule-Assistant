/**
 * Transform API events to frontend EventMap format
 */

import { Ev, EventMap, Kind } from "../types";
import { EventResponse } from "../services/events.api";

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
export function transformApiEventToEv(apiEvent: EventResponse): Ev {
  return {
    id: apiEvent.id,
    kind: "event" as Kind,
    allDay: apiEvent.all_day,
    startMin: dateToMinutes(apiEvent.start_time),
    endMin: dateToMinutes(apiEvent.end_time),
    title: apiEvent.title,
    color: apiEvent.color,
    location: apiEvent.location || "",
    notes: apiEvent.notes || "",
  };
}

/**
 * Transform array of API events to EventMap indexed by date key
 */
export function transformApiEventsToEventMap(apiEvents: EventResponse[]): EventMap {
  const eventMap: EventMap = {};

  for (const apiEvent of apiEvents) {
    const dateKey = getDateKey(apiEvent.start_time);
    const frontendEvent = transformApiEventToEv(apiEvent);

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
 * Merge new events into existing EventMap (for incremental updates)
 */
export function mergeEventsIntoMap(
  existingMap: EventMap,
  newEvents: EventResponse[]
): EventMap {
  const merged = { ...existingMap };
  
  for (const apiEvent of newEvents) {
    const dateKey = getDateKey(apiEvent.start_time);
    const frontendEvent = transformApiEventToEv(apiEvent);
    
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