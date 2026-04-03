"use client";

import React, { useState, useMemo, useEffect } from "react";
import "./SmartScheduler.css";
import {
  Ev,
  EventMap,
  FilterCriteria,
  EventCategory,
} from "./types";
import {
  monthNames,
  RAINBOW,
  keyOf,
  addDaysISO,
  dayHeaderLabel,
  parseISODate,
} from "./utils";

import Sidebar from "./components/Sidebar";
import MonthNavigation from "./components/MonthNavigation";
import FilterBar from "./components/FilterBar";
import MonthGrid from "./components/MonthGrid";
import DayView from "./components/DayView";
import HotkeysModal from "./components/Modals/HotkeysModal";
import ChatModal from "./components/Modals/ChatModal";
import EventModal from "./components/Modals/EventModal";
import ViewEventModal from "./components/Modals/ViewEventModal";

export default function Home() {
  // --- Categories State ---
  const [categories, setCategories] = useState<EventCategory[]>([
    { id: "cat-urgent", name: "Urgent / Important", color: "#ff3b30" },
    { id: "cat-work", name: "Work", color: "#ff9500" },
    { id: "cat-personal", name: "Personal", color: "#ffcc00" },
    { id: "cat-health", name: "Health / Fitness", color: "#34c759" },
    { id: "cat-reminder", name: "Reminder", color: "#00c7be" },
    { id: "cat-meetings", name: "Meetings / Appointments", color: "#007aff" },
    { id: "cat-social", name: "Social / Fun", color: "#af52de" },
  ]);

  function handleAddCategory(cat: EventCategory) {
    setCategories((prev) => [...prev, cat]);
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
  const [hotkeysOpen, setHotkeysOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [eventModalOpen, setEventModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<{ event: Ev; dateKey: string } | null>(null);
  const [viewingEvent, setViewingEvent] = useState<{ event: Ev; dateKey: string } | null>(null);

  // Events store
  const [events, setEvents] = useState<EventMap>({
    "2026-02-02": [
      {
        id: 1,
        kind: "event",
        allDay: false,
        startMin: 600,
        endMin: 630,
        title: "Training",
        color: "#34c759",
        categoryId: "cat-health",
        location: "Gym",
        notes: "",
      },
      {
        id: 2,
        kind: "event",
        allDay: false,
        startMin: 660,
        endMin: 720,
        title: "Transfer window opens",
        color: "#ff3b30",
        categoryId: "cat-urgent",
        location: "Office",
        notes: "",
      },
    ],
    "2026-02-03": [
      {
        id: 3,
        kind: "task",
        allDay: false,
        startMin: 540,
        endMin: 600,
        title: "First Division",
        color: "#007aff",
        categoryId: "cat-meetings",
        location: "Library",
        notes: "",
      },
    ],
  });

  const [nextId, setNextId] = useState(100);

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
        setHotkeysOpen(false);
        setChatOpen(false);
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

  function onSaveEvent(newItem: Ev, date: string) {
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

    if (editingEvent) {
      setEvents((prev) => {
        const next: EventMap = { ...prev };
        const oldDate = editingEvent.dateKey;

        // Remove from old date
        if (next[oldDate]) {
          next[oldDate] = next[oldDate].filter(e => e.id !== editingEvent.event.id);
          if (next[oldDate].length === 0) delete next[oldDate];
        }
        // Add to new date
        const arr = next[date] ? [...next[date]] : [];
        const updated = { ...newItem, id: editingEvent.event.id };
        arr.push(updated);
        arr.sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
        next[date] = arr;
        return next;
      });
    } else {
      let allocatedIds = targetDates.length;
      let startId = nextId;
      setNextId((x) => x + allocatedIds);

      setEvents((prev) => {
        const next: EventMap = { ...prev };
        targetDates.forEach((d, idx) => {
          const eventWithId = { ...newItem, id: startId + idx };
          const arr = next[d] ? [...next[d]] : [];
          arr.push(eventWithId);
          arr.sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
          next[d] = arr;
        });
        return next;
      });
    }

    setEventModalOpen(false);
    setEditingEvent(null);
  }

  function onDeleteEvent(dateKey: string, eventId: number) {
    setEvents((prev) => {
      const next: EventMap = { ...prev };
      if (!next[dateKey]) return next;
      next[dateKey] = next[dateKey].filter(e => e.id !== eventId);
      if (next[dateKey].length === 0) delete next[dateKey];
      return next;
    });
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

  return (
    <div className="container-fluid vh-100 p-0 d-flex flex-column overflow-hidden bg-dark">
      <div className="flex-grow-1 d-flex overflow-hidden">
        {/* SIDEBAR */}
        <Sidebar
          filteredEvents={filteredEvents}
          onHotkeysClick={() => setHotkeysOpen(true)}
          onChatClick={() => setChatOpen(true)}
          onProfileClick={() => { }}
          onLogoClick={goToToday}
          onEventClick={(dateKey) => {
            setSelectedDay(dateKey);
            setViewMode("day");
          }}
          onViewEvent={onViewEvent}
        />

        {/* MAIN */}
        <main className="flex-grow-1 d-flex flex-column bg-white text-dark overflow-hidden">
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

          {/* ===== HOTKEYS OVERLAY ===== */}
          <HotkeysModal isOpen={hotkeysOpen} onClose={() => setHotkeysOpen(false)} />

          {/* ===== CHAT MODAL ===== */}
          <ChatModal
            isOpen={chatOpen}
            onClose={() => setChatOpen(false)}
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
