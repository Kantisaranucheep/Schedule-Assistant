"use client";

import { useState, useEffect, useCallback } from "react";
import { EventMap, Ev, Kind } from "../types";
import { RAINBOW, timeToMinutes, nowTimeHHMM, roundUpTimeHHMM } from "../utils";
import { 
  fetchEvents, 
  createEvent, 
  fetchCalendars, 
  createCalendar,
  EventCreateRequest 
} from "../services/events.api";
import { transformApiEventsToEventMap, mergeEventsIntoMap } from "../utils/eventTransform";

// Default user ID for development (replace with actual auth)
const DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001";

export function useEvents() {
  const [events, setEvents] = useState<EventMap>({});
  const [calendarId, setCalendarId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nextLocalId, setNextLocalId] = useState(100);

  // Initialize: Get or create calendar, then load events
  useEffect(() => {
    async function initializeCalendar() {
      try {
        setLoading(true);
        setError(null);

        // Try to get existing calendars for user
        let calendars = await fetchCalendars(DEFAULT_USER_ID);
        
        let calendar;
        if (calendars.length === 0) {
          // Create default calendar if none exists
          calendar = await createCalendar(DEFAULT_USER_ID, "My Calendar");
        } else {
          calendar = calendars[0];
        }
        
        setCalendarId(calendar.id);
      } catch (err) {
        console.error("Failed to initialize calendar:", err);
        setError(err instanceof Error ? err.message : "Failed to initialize");
      } finally {
        setLoading(false);
      }
    }

    initializeCalendar();
  }, []);

  // Load events when calendarId is set
  const loadEvents = useCallback(async (startDate?: Date, endDate?: Date) => {
    if (!calendarId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const apiEvents = await fetchEvents(calendarId, startDate, endDate);
      const eventMap = transformApiEventsToEventMap(apiEvents);
      setEvents(eventMap);
    } catch (err) {
      console.error("Failed to load events:", err);
      setError(err instanceof Error ? err.message : "Failed to load events");
    } finally {
      setLoading(false);
    }
  }, [calendarId]);

  // Load events when calendar is ready
  useEffect(() => {
    if (calendarId) {
      loadEvents();
    }
  }, [calendarId, loadEvents]);

  // Add event - creates via API then updates local state
  async function addEvent(
    modalKind: Kind,
    mTitle: string,
    mDate: string,
    mStart: string,
    mEnd: string,
    mAllDay: boolean,
    mColor: string,
    mLocation: string,
    mNotes: string,
    realTodayKey: string,
    isTodaySelected: boolean
  ): Promise<{ success: boolean; error?: string }> {
    const title = mTitle.trim();
    if (!title) return { success: false, error: "Title is required" };

    if (mDate < realTodayKey) {
      return { success: false, error: "You cannot choose a past date." };
    }

    let startMinVal = 0;
    let endMinVal = 0;

    if (!mAllDay) {
      if (isTodaySelected) {
        const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
        if (mStart < ms) {
          return { success: false, error: "Start time cannot be in the past." };
        }
      }
      startMinVal = timeToMinutes(mStart);
      endMinVal = timeToMinutes(mEnd);

      if (endMinVal < startMinVal) {
        return { success: false, error: "End time cannot be earlier than start time." };
      }

      if (endMinVal - startMinVal < 5) {
        return { success: false, error: "Event duration must be at least 5 minutes." };
      }
    }

    // If we have a calendarId, create via API
    if (calendarId) {
      try {
        // Convert date and time to ISO datetime strings
        const [year, month, day] = mDate.split("-").map(Number);
        const startHour = Math.floor(startMinVal / 60);
        const startMin = startMinVal % 60;
        const endHour = Math.floor(endMinVal / 60);
        const endMin = endMinVal % 60;

        const startTime = new Date(year, month - 1, day, startHour, startMin);
        const endTime = new Date(year, month - 1, day, endHour, endMin);

        // For all-day events, set times to start/end of day
        if (mAllDay) {
          startTime.setHours(0, 0, 0, 0);
          endTime.setHours(23, 59, 59, 999);
        }

        const eventRequest: EventCreateRequest = {
          calendar_id: calendarId,
          title,
          start_time: startTime.toISOString(),
          end_time: endTime.toISOString(),
          all_day: mAllDay,
          location: mLocation.trim() || undefined,
          notes: mNotes.trim() || undefined,
          color: mColor || RAINBOW[1],
        };

        const createdEvent = await createEvent(eventRequest, true);
        
        // Merge new event into local state
        setEvents(prev => mergeEventsIntoMap(prev, [createdEvent]));
        
        return { success: true };
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to create event";
        return { success: false, error: message };
      }
    }

    // Fallback: local-only event creation (no API)
    const newItem: Ev = {
      id: nextLocalId,
      kind: modalKind,
      allDay: mAllDay,
      startMin: startMinVal,
      endMin: endMinVal,
      title,
      color: mColor || RAINBOW[1],
      location: mLocation.trim(),
      notes: mNotes.trim(),
    };

    setNextLocalId((x) => x + 1);

    setEvents((prev) => {
      const next: EventMap = { ...prev };
      const arr = next[mDate] ? [...next[mDate]] : [];
      arr.push(newItem);
      arr.sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
      next[mDate] = arr;
      return next;
    });

    return { success: true };
  }

  // Refetch events (useful after month navigation)
  const refetch = useCallback((startDate?: Date, endDate?: Date) => {
    return loadEvents(startDate, endDate);
  }, [loadEvents]);

  return { 
    events, 
    addEvent, 
    loading, 
    error, 
    calendarId,
    refetch 
  };
}