"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import "./SmartScheduler.css";
import {
  Kind,
  Ev,
  EventMap,
  ChatMsg,
  ChatSession,
} from "./types";
import {
  monthNames,
  RAINBOW,
  pad,
  keyOf,
  timeToMinutes,
  parseISODate,
  prettyDow,
  prettyMonth,
  nowTimeHHMM,
  roundUpTimeHHMM,
  uniq,
  tokenize,
  uid,
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
  // Month view default: Feb 2026
  const [viewYear, setViewYear] = useState(2026);
  const [viewMonth, setViewMonth] = useState(1);

  // Sidebar "today"
  const TODAY = useMemo(() => new Date(2026, 1, 2), []);

  // ===== Day/Month mode =====
  const [viewMode, setViewMode] = useState<"month" | "day">("month");
  const [selectedDay, setSelectedDay] = useState<string>(
    keyOf(new Date(2026, 1, 2))
  );

  // ===== HotKeys overlay =====
  const [hotkeysOpen, setHotkeysOpen] = useState(false);

  // ===== Chat modal =====
  const [chatOpen, setChatOpen] = useState(false);

  // Sessions + active session
  const [sessions, setSessions] = useState<ChatSession[]>([
    {
      id: "s1",
      title: "Chat 1",
      messages: [
        {
          id: "m1",
          role: "agent",
          text: "Made An Appointment For Me",
          createdAt: Date.now() - 50000,
        },
        {
          id: "m2",
          role: "agent",
          text: "Ok Sir! Who is the appointment with, and when should it be?",
          createdAt: Date.now() - 49000,
        },
        {
          id: "m3",
          role: "user",
          text: "With my advisor, tomorrow afternoon",
          tokens: tokenize("With my advisor, tomorrow afternoon"),
          createdAt: Date.now() - 48000,
        },
        {
          id: "m4",
          role: "agent",
          text: "Got it. What duration do you want? 30 or 60 minutes?",
          createdAt: Date.now() - 47000,
        },
        {
          id: "m5",
          role: "user",
          text: "30 minutes",
          tokens: tokenize("30 minutes"),
          createdAt: Date.now() - 46000,
        },
      ],
    },
    { id: "s2", title: "Chat 2", messages: [] },
    { id: "s3", title: "Chat 3", messages: [] },
    { id: "s4", title: "Chat 4", messages: [] },
    { id: "s5", title: "Chat 5", messages: [] },
  ]);
  const [activeSessionId, setActiveSessionId] = useState("s1");
  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) || sessions[0],
    [sessions, activeSessionId]
  );

  // Tokens that you will later send to AI (aggregated)
  const [tokenBuffer, setTokenBuffer] = useState<string[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [activeSession?.messages, isTyping, chatOpen]);

  function goToToday() {
    const d = new Date();
    setViewMonth(d.getMonth());
    setViewYear(d.getFullYear());
    // Optionally also reset selectedDay to today
    const k = [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getDate()).padStart(2, "0"),
    ].join("-");
    setSelectedDay(k);
    setViewMode("month");
  }

  function pushUserMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;

    const tokens = tokenize(trimmed);

    // Store tokens for later sending to AI
    setTokenBuffer((prev) => {
      const next = [...prev, ...tokens];
      console.log("TOKENS SENT (buffer):", next);
      return next;
    });

    // Save into current session as message + tokens
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeSessionId) return s;
        return {
          ...s,
          messages: [
            ...s.messages,
            {
              id: uid("msg"),
              role: "user",
              text: trimmed,
              tokens,
              createdAt: Date.now(),
            },
          ],
        };
      })
    );

    setChatInput("");

    // Simulate AI response delay
    setIsTyping(true);
    setTimeout(() => {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== activeSessionId) return s;
          return {
            ...s,
            messages: [
              ...s.messages,
              {
                id: uid("msg_ai"),
                role: "agent",
                text: "Got it! I'm simulating a 5-second wait to show off the cool loading animation. We can connect this to a real AI soon!",
                createdAt: Date.now(),
              },
            ],
          };
        })
      );
      setIsTyping(false);
    }, 5000);
  }

  function newSession() {
    const id = uid("s");
    setSessions((prev) => [
      { id, title: `Chat ${prev.length + 1}`, messages: [] },
      ...prev,
    ]);
    setActiveSessionId(id);
  }

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
  const [searchText, setSearchText] = useState("");
  const [filterOpen, setFilterOpen] = useState(false);

  const [kindFilter, setKindFilter] = useState<"all" | "event" | "task">("all");
  const [locationFilter, setLocationFilter] = useState("");
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");
  const [selectedColors, setSelectedColors] = useState<string[]>([]);

  function toggleColor(c: string) {
    setSelectedColors((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    );
  }

  const allColors = useMemo(() => {
    const colors: string[] = [];
    Object.values(events).forEach((arr) =>
      arr.forEach((ev) => colors.push(ev.color))
    );
    return uniq(colors.length ? colors : RAINBOW);
  }, [events]);

  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (searchText.trim()) n++;
    if (kindFilter !== "all") n++;
    if (fromDate) n++;
    if (toDate) n++;
    if (locationFilter.trim()) n++;
    if (selectedColors.length > 0) n++;
    return n;
  }, [searchText, kindFilter, fromDate, toDate, locationFilter, selectedColors]);

  const filteredEvents = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    const locQ = locationFilter.trim().toLowerCase();
    const from = fromDate || "0000-01-01";
    const to = toDate || "9999-12-31";

    const out: EventMap = {};

    Object.entries(events).forEach(([dateKey, arr]) => {
      if (dateKey < from || dateKey > to) return;

      const filteredArr = arr.filter((ev) => {
        if (kindFilter !== "all" && ev.kind !== kindFilter) return false;
        if (selectedColors.length > 0 && !selectedColors.includes(ev.color))
          return false;
        if (q && !ev.title.toLowerCase().includes(q)) return false;
        if (locQ && !(ev.location || "").toLowerCase().includes(locQ))
          return false;
        return true;
      });

      if (filteredArr.length > 0) out[dateKey] = filteredArr;
    });

    return out;
  }, [
    events,
    searchText,
    locationFilter,
    fromDate,
    toDate,
    kindFilter,
    selectedColors,
  ]);

  // ===== Modal state =====
  const [open, setOpen] = useState(false);
  const [modalKind, setModalKind] = useState<Kind>("event");
  const [mTitle, setMTitle] = useState("");
  const [mDate, setMDate] = useState<string>(keyOf(new Date()));
  const [mStart, setMStart] = useState("09:00");
  const [mEnd, setMEnd] = useState("09:00");
  const [mAllDay, setMAllDay] = useState(false);
  const [mLocation, setMLocation] = useState("");
  const [mNotes, setMNotes] = useState("");
  const [mColor, setMColor] = useState<string>(RAINBOW[1]);

  const realTodayKey = useMemo(() => keyOf(new Date()), []);
  const isTodaySelected = mDate === realTodayKey;

  // close on ESC
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setHotkeysOpen(false);
        setChatOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Time rules: no past time if today
  const minStart = useMemo(() => {
    if (!isTodaySelected || mAllDay) return "";
    return roundUpTimeHHMM(nowTimeHHMM(), 5);
  }, [isTodaySelected, mAllDay]);

  useEffect(() => {
    if (mAllDay) return;

    if (isTodaySelected) {
      const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
      if (mStart < ms) setMStart(ms);
      if (mEnd < ms) setMEnd(ms);
      if (mEnd < mStart) setMEnd(mStart);
    } else {
      if (mEnd < mStart) setMEnd(mStart);
    }
  }, [isTodaySelected, mAllDay, mStart, mEnd]);

  function openModal() {
    setModalKind("event");
    setMTitle("");
    setMDate(realTodayKey);
    setMStart("09:00");
    setMEnd("09:00");
    setMAllDay(false);
    setMLocation("");
    setMNotes("");
    setMColor(RAINBOW[1]);
    setOpen(true);
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

  function saveEvent(e: React.FormEvent) {
    e.preventDefault();

    const title = mTitle.trim();
    if (!title) return;

    if (mDate < realTodayKey) {
      alert("You cannot choose a past date.");
      return;
    }

    let startMinVal = 0;
    let endMinVal = 0;

    if (!mAllDay) {
      if (isTodaySelected) {
        const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
        if (mStart < ms) {
          alert("Start time cannot be in the past.");
          setMStart(ms);
          return;
        }
      }
      startMinVal = timeToMinutes(mStart);
      endMinVal = timeToMinutes(mEnd);

      if (endMinVal < startMinVal) {
        alert("End time cannot be earlier than start time.");
        setMEnd(mStart);
        return;
      }
    }

    const newItem: Ev = {
      id: nextId,
      kind: modalKind,
      allDay: mAllDay,
      startMin: startMinVal,
      endMin: endMinVal,
      title,
      color: mColor || RAINBOW[1],
      location: mLocation.trim(),
      notes: mNotes.trim(),
    };

    setNextId((x) => x + 1);

    setEvents((prev) => {
      const next: EventMap = { ...prev };
      const arr = next[mDate] ? [...next[mDate]] : [];
      arr.push(newItem);
      arr.sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
      next[mDate] = arr;
      return next;
    });

    setOpen(false);
  }

  const prettyDate = useMemo(() => {
    const dt = parseISODate(mDate);
    return `${prettyDow(dt)}, ${dt.getDate()} ${prettyMonth(dt)}`;
  }, [mDate]);

  const monthTitle = `${monthNames[viewMonth].toUpperCase()} ${viewYear}`;

  function clearAllFilters() {
    setKindFilter("all");
    setSelectedColors([]);
    setFromDate("");
    setToDate("");
    setLocationFilter("");
    setSearchText("");
  }

  // ===== DAY VIEW calculation (24 hours) =====
  const dayEvents = (filteredEvents[selectedDay] || [])
    .slice()
    .sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));

  return (
    <div className="container-fluid vh-100 p-0 d-flex flex-column overflow-hidden bg-dark">
      <div className="flex-grow-1 d-flex overflow-hidden">
        {/* SIDEBAR */}
        <Sidebar
          today={TODAY}
          todayMonthYear={todayMonthYear}
          todayWeekday={todayWeekday}
          upcoming={upcoming}
          onHotkeysClick={() => setHotkeysOpen(true)}
          onChatClick={() => setChatOpen(true)}
          onProfileClick={() => { }}
          onLogoClick={goToToday}
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
                searchText={searchText}
                setSearchText={setSearchText}
                filterOpen={filterOpen}
                setFilterOpen={setFilterOpen}
                activeFilterCount={activeFilterCount}
                kindFilter={kindFilter}
                setKindFilter={setKindFilter}
                fromDate={fromDate}
                setFromDate={setFromDate}
                toDate={toDate}
                setToDate={setToDate}
                locationFilter={locationFilter}
                setLocationFilter={setLocationFilter}
                selectedColors={selectedColors}
                allColors={allColors}
                toggleColor={toggleColor}
                clearAllFilters={clearAllFilters}
                onAddEvent={openModal}
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
            sessions={sessions}
            activeSessionId={activeSessionId}
            setActiveSessionId={setActiveSessionId}
            activeSession={activeSession}
            chatInput={chatInput}
            setChatInput={setChatInput}
            pushUserMessage={pushUserMessage}
            newSession={newSession}
            isTyping={isTyping}
            chatEndRef={chatEndRef}
          />

          {/* ===== EVENT MODAL ===== */}
          <EventModal
            isOpen={open}
            onClose={() => setOpen(false)}
            mTitle={mTitle}
            setMTitle={setMTitle}
            modalKind={modalKind}
            setModalKind={setModalKind}
            saveEvent={saveEvent}
            mDate={mDate}
            setMDate={setMDate}
            mStart={mStart}
            setMStart={setMStart}
            mEnd={mEnd}
            setMEnd={setMEnd}
            mAllDay={mAllDay}
            setMAllDay={setMAllDay}
            mLocation={mLocation}
            setMLocation={setMLocation}
            mNotes={mNotes}
            setMNotes={setMNotes}
            mColor={mColor}
            setMColor={setMColor}
            minStart={minStart}
            prettyDate={prettyDate}
            realTodayKey={realTodayKey}
            isTodaySelected={isTodaySelected}
          />
        </main>
      </div>
    </div>
  );
}
