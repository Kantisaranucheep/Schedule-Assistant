"use client";

import { useState, useEffect, useCallback } from "react";
import { EventMap, Ev, Kind, EventCategory } from "../types";
import { RAINBOW, timeToMinutes, nowTimeHHMM, roundUpTimeHHMM } from "../utils";
import { 
  fetchEvents, 
  fetchTasks,
  fetchCategories,
  createDefaultCategories,
  createEvent, 
  createTask,
  updateEvent,
  updateTask,
  fetchCalendars, 
  createCalendar,
  EventCreateRequest,
  TaskCreateRequest,
  EventUpdateRequest,
  TaskUpdateRequest,
  CategoryResponse,
  getUserTimezone,
  toLocalISOString
} from "../services/events.api";
import { 
  transformApiEventsToEventMap, 
  transformApiTasksToEventMap,
  mergeEventsAndTasks,
  mergeEventsIntoMap 
} from "../utils/eventTransform";

// Default user ID for development (replace with actual auth)
const DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001";

export function useEvents() {
  const [events, setEvents] = useState<EventMap>({});
  const [calendarId, setCalendarId] = useState<string | null>(null);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
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
          // Create default categories for new calendar
          const defaultCats = await createDefaultCategories(calendar.id);
          setCategories(defaultCats);
        } else {
          calendar = calendars[0];
          // Load existing categories
          const existingCats = await fetchCategories(calendar.id);
          if (existingCats.length === 0) {
            // Create default categories if none exist
            const defaultCats = await createDefaultCategories(calendar.id);
            setCategories(defaultCats);
          } else {
            setCategories(existingCats);
          }
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
      
      // Fetch both events and tasks in parallel
      const [apiEvents, apiTasks] = await Promise.all([
        fetchEvents(calendarId, startDate, endDate),
        fetchTasks(calendarId, startDate, endDate)
      ]);
      
      const eventMap = transformApiEventsToEventMap(apiEvents, categories);
      const taskMap = transformApiTasksToEventMap(apiTasks, categories);
      const mergedMap = mergeEventsAndTasks(eventMap, taskMap);
      
      setEvents(mergedMap);
    } catch (err) {
      console.error("Failed to load events:", err);
      setError(err instanceof Error ? err.message : "Failed to load events");
    } finally {
      setLoading(false);
    }
  }, [calendarId, categories]);

  // Load events when calendar is ready
  useEffect(() => {
    if (calendarId && categories.length > 0) {
      loadEvents();
    }
  }, [calendarId, categories, loadEvents]);

  // Add event or task - creates via API then updates local state
  async function addEvent(
    modalKind: Kind,
    mTitle: string,
    mDate: string,
    mStart: string,
    mEnd: string,
    mAllDay: boolean,
    mCategoryId: string,
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

    // If we have a calendarId, create via API
    if (calendarId) {
      try {
        if (modalKind === "task") {
          // Create task
          const taskRequest: TaskCreateRequest = {
            calendar_id: calendarId,
            title,
            date: mDate,
            category_id: mCategoryId || undefined,
            location: mLocation.trim() || undefined,
            notes: mNotes.trim() || undefined,
          };

          await createTask(taskRequest);
          
          // Reload events to get updated data
          await loadEvents();
          
          return { success: true };
        } else {
          // Create event
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
            start_time: toLocalISOString(startTime),
            end_time: toLocalISOString(endTime),
            all_day: mAllDay,
            location: mLocation.trim() || undefined,
            notes: mNotes.trim() || undefined,
            category_id: mCategoryId || undefined,
            timezone: getUserTimezone(),
          };

          const createdEvent = await createEvent(eventRequest, true);
          
          // Merge new event into local state
          setEvents(prev => mergeEventsIntoMap(prev, [createdEvent], categories));
          
          return { success: true };
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to create event";
        return { success: false, error: message };
      }
    }

    // Fallback: local-only event creation (no API)
    const category = categories.find(c => c.id === mCategoryId);
    const color = category?.color || RAINBOW[1];

    const newItem: Ev = {
      id: nextLocalId,
      kind: modalKind,
      allDay: modalKind === "task" ? true : mAllDay,
      startMin: modalKind === "task" ? 0 : timeToMinutes(mStart),
      endMin: modalKind === "task" ? 0 : timeToMinutes(mEnd),
      title,
      categoryId: mCategoryId,
      color: color,
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

  // Update an event or task
  async function editEvent(
    eventId: string,
    originalDateKey: string,
    modalKind: Kind,
    mTitle: string,
    mDate: string,
    mStart: string,
    mEnd: string,
    mAllDay: boolean,
    mCategoryId: string,
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

    // Only update via API if it's a UUID (API-created event)
    if (!eventId.includes("-")) {
      return { success: false, error: "Cannot update local-only events" };
    }

    try {
      if (modalKind === "task") {
        // Update task
        const taskUpdate: TaskUpdateRequest = {
          title,
          date: mDate,
          category_id: mCategoryId || undefined,
          location: mLocation.trim() || undefined,
          notes: mNotes.trim() || undefined,
        };

        await updateTask(eventId, taskUpdate);
        
        // Reload events to get updated data
        await loadEvents();
        
        return { success: true };
      } else {
        // Update event
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

        const eventUpdate: EventUpdateRequest = {
          title,
          start_time: toLocalISOString(startTime),
          end_time: toLocalISOString(endTime),
          all_day: mAllDay,
          location: mLocation.trim() || undefined,
          notes: mNotes.trim() || undefined,
          category_id: mCategoryId || undefined,
          timezone: getUserTimezone(),
        };

        await updateEvent(eventId, eventUpdate);
        
        // Reload events to get updated data
        await loadEvents();
        
        return { success: true };
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update";
      return { success: false, error: message };
    }
  }

  // Convert CategoryResponse to EventCategory for frontend
  const frontendCategories: EventCategory[] = categories.map(c => ({
    id: c.id,
    name: c.name,
    color: c.color,
  }));

  // Refetch events (useful after month navigation)
  const refetch = useCallback((startDate?: Date, endDate?: Date) => {
    return loadEvents(startDate, endDate);
  }, [loadEvents]);

  return { 
    events, 
    addEvent,
    editEvent,
    loading, 
    error, 
    calendarId,
    categories: frontendCategories,
    refetch 
  };
}