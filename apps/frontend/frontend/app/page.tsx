"use client";

import React, { useState, useMemo, useEffect } from "react";
import "./SmartScheduler.css";
import {
  Ev,
  EventMap,
  FilterCriteria,
} from "./types";
import {
  monthNames,
  RAINBOW,
  keyOf,
  addDaysISO,
  dayHeaderLabel,
} from "./utils";

import Sidebar from "./components/Sidebar";
import MonthNavigation from "./components/MonthNavigation";
import FilterBar from "./components/FilterBar";
import MonthGrid from "./components/MonthGrid";
import DayView from "./components/DayView";
import HotkeysModal from "./components/Modals/HotkeysModal";
import ChatModal from "./components/Modals/ChatModal";
import EventModal from "./components/Modals/EventModal";

export default function Home() {
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
        color: RAINBOW[3],
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
        color: RAINBOW[0],
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
        color: RAINBOW[5],
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
    selectedColors: [],
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
        if (filters.selectedColors.length > 0 && !filters.selectedColors.includes(ev.color))
          return false;
        if (q && !ev.title.toLowerCase().includes(q)) return false;
        if (locQ && !(ev.location || "").toLowerCase().includes(locQ))
          return false;
        return true;
      });

      if (filteredArr.length > 0) out[dateKey] = filteredArr;
    });

    return out;
  }, [events, filters]);

  // close on ESC
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setEventModalOpen(false);
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
    const eventWithId = { ...newItem, id: nextId };
    setNextId((x) => x + 1);

    setEvents((prev) => {
      const next: EventMap = { ...prev };
      const arr = next[date] ? [...next[date]] : [];
      arr.push(eventWithId);
      arr.sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
      next[date] = arr;
      return next;
    });

    setEventModalOpen(false);
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
                onFilterChange={setFilters}
                onAddEvent={() => setEventModalOpen(true)}
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
            />
          ) : (
            <DayView
              dayEvents={dayEvents}
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
            onClose={() => setEventModalOpen(false)}
            onSave={onSaveEvent}
            events={events}
          />
        </main>
      </div>
    </div>
  );
}
