"use client";

import { useState, useMemo } from "react";
import { Ev } from "../types";
import { monthNames, keyOf, addDaysISO, dayHeaderLabel } from "../utils";

export function useCalendarView(filteredEvents: Record<string, Ev[]>) {
  const [viewYear, setViewYear] = useState(new Date().getFullYear());
  const [viewMonth, setViewMonth] = useState(new Date().getMonth());
  const [viewMode, setViewMode] = useState<"month" | "day">("month");
  const [selectedDay, setSelectedDay] = useState<string>(keyOf(new Date()));

  const TODAY = useMemo(() => new Date(), []);

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

  const monthTitle = `${monthNames[viewMonth].toUpperCase()} ${viewYear}`;

  // Upcoming uses FILTERED events
  const upcoming = useMemo(() => {
    const todayKey = keyOf(TODAY);
    const list: Array<{ dateKey: string } & Ev> = [];

    Object.keys(filteredEvents).forEach((dateKey) => {
      if (dateKey < todayKey) return;
      filteredEvents[dateKey].forEach((ev) => list.push({ dateKey, ...ev }));
    });

    list.sort((a, b) => {
      if (a.dateKey !== b.dateKey) return a.dateKey.localeCompare(b.dateKey);
      return (a.startMin ?? 0) - (b.startMin ?? 0);
    });

    return list;
  }, [filteredEvents, TODAY]);

  const todayWeekday = useMemo(
    () => TODAY.toLocaleDateString("en-US", { weekday: "short" }),
    [TODAY]
  );
  const todayMonthYear = useMemo(
    () => `${monthNames[TODAY.getMonth()]} ${TODAY.getFullYear()}`,
    [TODAY]
  );

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

    // CHANGED: 35 cells (5 rows) instead of 42 (6 rows)
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

  // ===== DAY VIEW calculation (24 hours) =====
  const dayEvents = (filteredEvents[selectedDay] || [])
    .slice()
    .sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));

  return {
    viewYear,
    viewMonth,
    viewMode,
    setViewMode,
    selectedDay,
    setSelectedDay,
    TODAY,
    goToToday,
    prevMonth,
    nextMonth,
    monthTitle,
    upcoming,
    todayWeekday,
    todayMonthYear,
    cells,
    dayEvents,
  };
}