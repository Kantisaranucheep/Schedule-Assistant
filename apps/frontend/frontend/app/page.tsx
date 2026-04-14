"use client";

import React, { useState, useMemo, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import "./SmartScheduler.css";
import {
  Ev,
  EventMap,
  FilterCriteria,
  EventCategory,
  NotificationSettings,
  NotificationTimePreference,
} from "./types";
import {
  monthNames,
  RAINBOW,
  keyOf,
  addDaysISO,
  dayHeaderLabel,
  parseISODate,
} from "./utils";
import { deleteEvent, deleteTask } from "./services/events.api";
import { fetchUserSettings, saveUserSettings } from "./services/settings.api";

import Sidebar from "./components/Sidebar";
import MonthNavigation from "./components/MonthNavigation";
import FilterBar from "./components/FilterBar";
import MonthGrid from "./components/MonthGrid";
import DayView from "./components/DayView";
import NotificationModal from "./components/Modals/NotificationModal";
import EmailModal from "./components/Modals/EmailModal";
import EventModal from "./components/Modals/EventModal";
import ViewEventModal from "./components/Modals/ViewEventModal";
import { useEvents } from "./hooks/useEvents";
import { useInvitations } from "./hooks/useInvitations";



export default function Home() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const session = localStorage.getItem("scheduler_auth_session");
    if (!session) {
      router.replace("/login");
      return;
    }
    setAuthChecked(true);
  }, [router]);
  
  // Events and categories from API
  const { 
    events: apiEvents, 
    addEvent: apiAddEvent, 
    editEvent: apiEditEvent, 
    addCategory: apiAddCategory,
    removeCategory: apiDeleteCategory,
    loading, 
    error, 
    calendarId, 
    categories, 
    refetch 
  } = useEvents();

  const { invitations, acceptInvitation, declineInvitation, refresh: refetchInvitations } = useInvitations();

  // Local events overlay (for immediate UI updates before API sync)
  const [localEvents, setLocalEvents] = useState<EventMap>({});
  const [nextId, setNextId] = useState(100000); // Start high to avoid conflicts with API IDs

  // Merge API events with local events
  const events = useMemo(() => {
    const merged: EventMap = { ...apiEvents };
    Object.entries(localEvents).forEach(([dateKey, evts]) => {
      if (!merged[dateKey]) {
        merged[dateKey] = [];
      }
      merged[dateKey] = [...merged[dateKey], ...evts];
      merged[dateKey].sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
    });
    return merged;
  }, [apiEvents, localEvents]);

  async function handleAddCategory(cat: EventCategory): Promise<string | undefined> {
    try {
      const newCat = await apiAddCategory(cat.name, cat.color);
      return newCat.id;
    } catch (err) {
      console.error("Failed to add category:", err);
      alert("Failed to add category");
      return undefined;
    }
  }

  async function handleDeleteCategory(catId: string) {
    try {
      await apiDeleteCategory(catId);
    } catch (err) {
      console.error("Failed to delete category:", err);
      alert("Failed to delete category");
    }
  }

  // Month view default: current month
  const [viewYear, setViewYear] = useState(new Date().getFullYear());
  const [viewMonth, setViewMonth] = useState(new Date().getMonth());

  // Sidebar "today"
  const TODAY = useMemo(() => new Date(), []);

  // ===== Day/Month mode =====
  const [viewMode, setViewMode] = useState<"month" | "day">("month");
  const [selectedDay, setSelectedDay] = useState<string>(
    keyOf(new Date())
  );

  // ===== Modals visibility =====
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    windowEnabled: true,
    emailEnabled: false,
    notificationTimes: [],
  });
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [eventModalOpen, setEventModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<{ event: Ev; dateKey: string } | null>(null);
  const [viewingEvent, setViewingEvent] = useState<{ event: Ev; dateKey: string } | null>(null);
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  // Load settings from backend on mount
  useEffect(() => {
    async function loadSettings() {
      let userId = "";
      try {
        const sessionItem = localStorage.getItem("scheduler_auth_session");
        if (sessionItem) {
          const sessionData = JSON.parse(sessionItem);
          userId = sessionData.user_id;
        }
      } catch (e) {
        console.error("Error reading session", e);
      }
      
      if (!userId) return;

      const settings = await fetchUserSettings(userId);
      if (settings) {
        setNotificationSettings({
          windowEnabled: settings.window_notifications_enabled,
          emailEnabled: settings.notifications_enabled,
          notificationTimes: settings.notification_times || [],
        });
        setUserEmail(settings.notification_email || "");
      }
      setSettingsLoaded(true);
    }
    loadSettings();
  }, []);

  // Save settings to backend when they change
  const saveSettingsToBackend = useCallback(async (
    newSettings: NotificationSettings,
    email: string
  ) => {
    if (!settingsLoaded) return; // Don't save during initial load
    
    let userId = "";
    try {
      const sessionItem = localStorage.getItem("scheduler_auth_session");
      if (sessionItem) {
        const sessionData = JSON.parse(sessionItem);
        userId = sessionData.user_id;
      }
    } catch (e) {
      console.error("Error reading session", e);
    }

    if (!userId) return;

    await saveUserSettings(userId, {
      notifications_enabled: newSettings.emailEnabled,
      window_notifications_enabled: newSettings.windowEnabled,
      notification_email: email || null,
      notification_times: newSettings.notificationTimes,
    });
  }, [settingsLoaded]);

  // Handle notification settings update
  const handleUpdateNotificationSettings = useCallback((newSettings: NotificationSettings) => {
    setNotificationSettings(newSettings);
    saveSettingsToBackend(newSettings, userEmail);
  }, [userEmail, saveSettingsToBackend]);

  // Handle email update
  const handleUpdateEmail = useCallback((email: string) => {
    setUserEmail(email);
    saveSettingsToBackend(notificationSettings, email);
  }, [notificationSettings, saveSettingsToBackend]);

  // ===== Filters =====
  const [filters, setFilters] = useState<FilterCriteria>({
    searchText: "",
    kindFilter: "all",
    locationFilter: "",
    fromDate: "",
    toDate: "",
    selectedCategories: [],
  });

  const filteredEvents = useMemo(() => {
    const q = filters.searchText.trim().toLowerCase();
    const locQ = filters.locationFilter.trim().toLowerCase();
    const from = filters.fromDate || "0000-01-01";
    const to = filters.toDate || "9999-12-31";

    const out: EventMap = {};

    Object.entries(events).forEach(([dateKey, arr]) => {
      if (dateKey < from || dateKey > to) return;

      const filteredArr = arr.filter((ev) => {
        if (filters.kindFilter !== "all" && ev.kind !== filters.kindFilter) return false;
        if (filters.selectedCategories.length > 0) {
          // check if event's categoryId or color matches selected categories
          const catMatch = filters.selectedCategories.some(catId => {
            if (ev.categoryId === catId) return true;
            const fallbackCat = categories.find(c => c.id === catId);
            if (fallbackCat && fallbackCat.color === ev.color && !ev.categoryId) return true;
            return false;
          });
          if (!catMatch) return false;
        }

        if (q && !ev.title.toLowerCase().includes(q)) return false;
        if (locQ && !(ev.location || "").toLowerCase().includes(locQ))
          return false;
        return true;
      });

      if (filteredArr.length > 0) out[dateKey] = filteredArr;
    });

    return out;
  }, [events, filters, categories]);

  // close on ESC
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setEventModalOpen(false);
        setEditingEvent(null);
        setViewingEvent(null);
        setNotificationsOpen(false);
        setEmailModalOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function goToToday() {
    const d = new Date();
    setViewMonth(d.getMonth());
    setViewYear(d.getFullYear());
    const k = [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getDate()).padStart(2, "0"),
    ].join("-");
    setSelectedDay(k);
    setViewMode("month");
  }

  function prevMonth() {
    let m = viewMonth - 1;
    let y = viewYear;
    if (m < 0) {
      m = 11;
      y = y - 1;
    }
    setViewMonth(m);
    setViewYear(y);
  }
  function nextMonth() {
    let m = viewMonth + 1;
    let y = viewYear;
    if (m > 11) {
      m = 0;
      y = y + 1;
    }
    setViewMonth(m);
    setViewYear(y);
  }

  // Calendar cells (35) use FILTERED events
  const cells = useMemo(() => {
    const first = new Date(viewYear, viewMonth, 1);
    const startDow = first.getDay();
    const last = new Date(viewYear, viewMonth + 1, 0);
    const daysInMonth = last.getDate();
    const prevLast = new Date(viewYear, viewMonth, 0);
    const prevDays = prevLast.getDate();

    const out: Array<{
      date: Date;
      muted: boolean;
      key: string;
      isToday: boolean;
      dayEvents: Ev[];
    }> = [];

    for (let i = 0; i < 35; i++) {
      let d: Date;
      let muted = false;

      if (i < startDow) {
        const day = prevDays - (startDow - 1 - i);
        d = new Date(viewYear, viewMonth - 1, day);
        muted = true;
      } else if (i >= startDow + daysInMonth) {
        const day = i - (startDow + daysInMonth) + 1;
        d = new Date(viewYear, viewMonth + 1, day);
        muted = true;
      } else {
        const day = i - startDow + 1;
        d = new Date(viewYear, viewMonth, day);
      }

      const k = keyOf(d);
      const dayEvents = (filteredEvents[k] || [])
        .slice()
        .sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));

      const isToday =
        !muted &&
        d.getFullYear() === TODAY.getFullYear() &&
        d.getMonth() === TODAY.getMonth() &&
        d.getDate() === TODAY.getDate();

      out.push({ date: d, muted, key: k, isToday, dayEvents });
    }

    return out;
  }, [filteredEvents, viewYear, viewMonth, TODAY]);

  async function onSaveEvent(newItem: Ev, date: string) {
    const realTodayKey = keyOf(new Date());
    const isTodaySelected = date === realTodayKey;

    // Convert time from minutes to HH:MM format
    const startMinToTime = (mins: number) => {
      const h = Math.floor(mins / 60);
      const m = mins % 60;
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    };

    // If editing an existing API event (has UUID), use update
    if (editingEvent && typeof editingEvent.event.id === "string" && editingEvent.event.id.includes("-")) {
      // Use the ORIGINAL event's kind to determine which API to call
      const originalKind = editingEvent.event.kind;
      
      const result = await apiEditEvent(
        editingEvent.event.id,
        editingEvent.dateKey,
        originalKind,
        newItem.title,
        date,
        startMinToTime(newItem.startMin ?? 0),
        startMinToTime(newItem.endMin ?? 0),
        newItem.allDay,
        newItem.categoryId || "",
        newItem.location || "",
        newItem.notes || "",
        newItem.collaborators || [],
        realTodayKey,
        isTodaySelected
      );

      if (!result.success) {
        alert(result.error || "Failed to update");
        return;
      }

      setEventModalOpen(false);
      setEditingEvent(null);
      return;
    }

    // For recurring events, create multiple events
    let targetDates: string[] = [date];
    if (!editingEvent && newItem.isRecurring && newItem.recurEndDate && newItem.recurDays && newItem.recurDays.length > 0) {
      targetDates = [];
      let current = date;
      const end = newItem.recurEndDate;
      const days = new Set(newItem.recurDays);
      let limit = 0;
      while (current <= end && limit < 1000) {
        const d = parseISODate(current);
        if (days.has(d.getDay())) {
          targetDates.push(current);
        }
        current = addDaysISO(current, 1);
        limit++;
      }
      if (targetDates.length === 0) targetDates = [date];
    }

    // Create event via API for each target date
    for (const targetDate of targetDates) {
      const result = await apiAddEvent(
        newItem.kind,
        newItem.title,
        targetDate,
        startMinToTime(newItem.startMin ?? 0),
        startMinToTime(newItem.endMin ?? 0),
        newItem.allDay,
        newItem.categoryId || "",
        newItem.location || "",
        newItem.notes || "",
        newItem.collaborators || [],
        realTodayKey,
        targetDate === realTodayKey
      );

      if (!result.success) {
        console.error("Failed to save event:", result.error);
        alert(result.error || "Failed to save event");
        return;
      }
    }

    setEventModalOpen(false);
    setEditingEvent(null);
  }

  async function onDeleteEvent(dateKey: string, eventId: number | string) {
    // Only delete from API if it's a UUID (API-created event)
    if (typeof eventId === "string" && eventId.includes("-")) {
      try {
        // Find the event to determine if it's a task or event
        const event = apiEvents[dateKey]?.find(e => e.id === eventId);
        if (event?.kind === "task") {
          await deleteTask(eventId);
        } else {
          await deleteEvent(eventId);
        }
        // Refresh events from API
        await refetch();
      } catch (err) {
        console.error("Failed to delete:", err);
        alert("Failed to delete event");
      }
    } else {
      // Local-only event, just remove from local state
      setLocalEvents((prev) => {
        const next: EventMap = { ...prev };
        if (!next[dateKey]) return next;
        next[dateKey] = next[dateKey].filter(e => e.id !== eventId);
        if (next[dateKey].length === 0) delete next[dateKey];
        return next;
      });
    }
  }

  function onEditClick(dateKey: string, ev: Ev) {
    setEditingEvent({ event: ev, dateKey });
    setEventModalOpen(true);
  }

  function onViewEvent(dateKey: string, ev: Ev) {
    setViewingEvent({ event: ev, dateKey });
  }

  function onAddEventClick() {
    setEditingEvent(null);
    setEventModalOpen(true);
  }

  const monthTitle = `${monthNames[viewMonth].toUpperCase()} ${viewYear}`;

  // ===== DAY VIEW calculation (24 hours) =====
  const dayEvents = (filteredEvents[selectedDay] || [])
    .slice()
    .sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));

  if (!authChecked) {
    return null;
  }

  return (
    <div className="container-fluid vh-100 p-0 d-flex flex-column overflow-hidden bg-dark">
      <div className="flex-grow-1 d-flex overflow-hidden">
        {/* SIDEBAR */}
        <Sidebar
          filteredEvents={filteredEvents}
          onNotificationsClick={() => setNotificationsOpen(true)}
          onChatClick={() => router.push('/chat')}
          onProfileClick={() => setEmailModalOpen(true)}
          onLogoClick={goToToday}
          onEventClick={(dateKey) => {
            setSelectedDay(dateKey);
            setViewMode("day");
          }}
          onViewEvent={onViewEvent}
        />

        {/* MAIN */}
        <main className="flex-grow-1 d-flex flex-column bg-white text-dark overflow-hidden">
          {/* Loading/Error State */}
          {loading && (
            <div className="position-absolute top-0 end-0 m-3 p-2 bg-info text-white rounded shadow" style={{ zIndex: 1000 }}>
              Loading events...
            </div>
          )}
          {error && (
            <div className="position-absolute top-0 end-0 m-3 p-3 bg-danger text-white rounded shadow" style={{ zIndex: 1000 }}>
              Error: {error}
            </div>
          )}
          {/* SHARED HEADER */}
          <div className="d-flex align-items-center justify-content-between px-3 border-bottom border-light-subtle bg-white" style={{ minHeight: 60 }}>
            {/* Left: Navigation */}
            {viewMode === "month" ? (
              <MonthNavigation
                onPrev={prevMonth}
                onNext={nextMonth}
                title={monthTitle}
              />
            ) : (
              <div className="d-flex align-items-center gap-3">
                <button
                  className="btn btn-outline-secondary btn-sm rounded-circle d-flex align-items-center justify-content-center shadow-sm"
                  style={{ width: 32, height: 32 }}
                  onClick={() => setSelectedDay(addDaysISO(selectedDay, -1))}
                  aria-label="Previous day"
                >
                  ‹
                </button>
                <div className="h4 mb-0 fw-bold text-dark letter-spacing-n1" style={{ fontFamily: "var(--font-geist-sans), sans-serif" }}>
                  {dayHeaderLabel(selectedDay)}
                </div>
                <button
                  className="btn btn-outline-secondary btn-sm rounded-circle d-flex align-items-center justify-content-center shadow-sm"
                  style={{ width: 32, height: 32 }}
                  onClick={() => setSelectedDay(addDaysISO(selectedDay, 1))}
                  aria-label="Next day"
                >
                  ›
                </button>
              </div>
            )}

            {/* Right: Search, Filter, Add & View Toggle */}
            <div className="d-flex align-items-center gap-2">
              <FilterBar
                events={events}
                categories={categories}
                onFilterChange={setFilters}
                onAddEvent={onAddEventClick}
              />
              {viewMode === "day" && (
                <button
                  className="btn btn-dark btn-sm rounded-pill px-4 fw-bold shadow-sm transition-all hover-scale"
                  onClick={() => setViewMode("month")}
                  type="button"
                  style={{ fontSize: 12, height: 36 }}
                >
                  Month View
                </button>
              )}
            </div>
          </div>

          {/* ===== SWITCH MONTH / DAY ===== */}
          {viewMode === "month" ? (
            <MonthGrid
              cells={cells}
              onSelectDay={setSelectedDay}
              setViewMode={setViewMode}
              onViewEvent={onViewEvent}
            />
          ) : (
            <DayView
              dayEvents={dayEvents}
              selectedDay={selectedDay}
              onViewEvent={onViewEvent}
            />
          )}

          {/* ===== NOTIFICATION SETTINGS OVERLAY ===== */}
          <NotificationModal
            isOpen={notificationsOpen}
            onClose={() => setNotificationsOpen(false)}
            settings={notificationSettings}
            onUpdateSettings={handleUpdateNotificationSettings}
            userEmail={userEmail}
            onEmailClick={() => {
              setNotificationsOpen(false);
              setEmailModalOpen(true);
            }}
            invitations={invitations}
            onAcceptInvitation={async (id) => {
              await acceptInvitation(id);
              refetch();
            }}
            onDeclineInvitation={declineInvitation}
          />

          {/* ===== EMAIL SETTINGS OVERLAY ===== */}
          <EmailModal 
            isOpen={emailModalOpen}
            onClose={() => setEmailModalOpen(false)}
            email={userEmail}
            onUpdateEmail={handleUpdateEmail}
          />

          {/* ===== EVENT MODAL ===== */}
          <EventModal
            isOpen={eventModalOpen}
            onClose={() => {
              setEventModalOpen(false);
              setEditingEvent(null);
            }}
            onSave={onSaveEvent}
            events={events}
            editingEvent={editingEvent}
            categories={categories}
            onAddCategory={handleAddCategory}
            onDeleteCategory={handleDeleteCategory}
          />

          {/* ===== VIEW EVENT MODAL ===== */}
          <ViewEventModal
            isOpen={viewingEvent !== null}
            onClose={() => setViewingEvent(null)}
            eventData={viewingEvent}
            onEdit={onEditClick}
            onDelete={onDeleteEvent}
          />
        </main>
      </div>
    </div>
  );
}
