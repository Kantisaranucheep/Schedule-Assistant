"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import "./SmartScheduler.css";
type Kind = "event" | "task";

type Ev = {
  id: number;
  kind: Kind;
  allDay: boolean;
  startMin: number;
  endMin: number;
  title: string;
  color: string; // color = category
  location: string;
  notes: string;
};

type EventMap = Record<string, Ev[]>;

const monthNames = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const RAINBOW = [
  "#ff3b30",
  "#ff9500",
  "#ffcc00",
  "#34c759",
  "#00c7be",
  "#007aff",
  "#af52de"
];

// --- class name helpers (so TS stops complaining) ---
const kindPill = "kindPill";
const kindPillActive = "kindPillActive";

const colorDot = "colorDot";
const colorDotActive = "colorDotActive";

const cell = "cell";
const mutedDay = "mutedDay";
const today = "today";

const dayBlockSmall = "dayBlockSmall";
const dayBlockInnerSmall = "dayBlockInnerSmall";

const hkOverlay = "hkOverlay";
const hkShow = "hkShow";

const chatOverlay = "chatOverlay";
const chatShow = "chatShow";
const chatItem = "chatItem";
const chatItemActive = "chatItemActive";

const bubbleRow = "bubbleRow";
const bubbleRowRight = "bubbleRowRight";
const bubbleRowLeft = "bubbleRowLeft";
const bubble = "bubble";
const bubbleUser = "bubbleUser";
const bubbleAgent = "bubbleAgent";

const overlay = "overlay";
const overlayShow = "overlayShow";

const pill = "pill";
const pillActive = "pillActive";

const swatch = "swatch";
const swatchSelected = "swatchSelected";


function pad(n: number) { return String(n).padStart(2, "0"); }
function keyOf(d: Date) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }

function minutesToLabel(mins: number) {
  let h = Math.floor(mins / 60);
  const m = mins % 60;
  const ap = h >= 12 ? "PM" : "AM";
  let hh = h % 12;
  if (hh === 0) hh = 12;
  return `${pad(hh)}:${pad(m)}${ap}`;
}

function timeToMinutes(t: string) {
  const [hh, mm] = t.split(":").map(Number);
  return hh * 60 + mm;
}

function parseISODate(iso: string) {
  const [y, mo, da] = iso.split("-").map(Number);
  return new Date(y, mo - 1, da);
}

function prettyDow(d: Date) { return d.toLocaleDateString("en-US", { weekday: "long" }); }
function prettyMonth(d: Date) { return d.toLocaleDateString("en-US", { month: "long" }); }

function formatUpcomingDate(iso: string) {
  const [y, mo, d] = iso.split("-").map(Number);
  const dt = new Date(y, mo - 1, d);
  const dd = dt.getDate();
  const mname = monthNames[dt.getMonth()].slice(0, 3);
  return `${dd} ${mname} ${dt.getFullYear()}`;
}

function nowTimeHHMM() {
  const now = new Date();
  return `${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

function roundUpTimeHHMM(hhmm: string, stepMin = 5) {
  const [h, m] = hhmm.split(":").map(Number);
  let total = h * 60 + m;
  total = Math.ceil(total / stepMin) * stepMin;
  if (total > 23 * 60 + 59) total = 23 * 60 + 59;
  const hh = Math.floor(total / 60);
  const mm = total % 60;
  return `${pad(hh)}:${pad(mm)}`;
}

function uniq(arr: string[]) {
  return Array.from(new Set(arr));
}

function addDaysISO(iso: string, delta: number) {
  const d = parseISODate(iso);
  d.setDate(d.getDate() + delta);
  return keyOf(d);
}

function dayHeaderLabel(iso: string) {
  const d = parseISODate(iso);
  const dd = d.getDate();
  const m = monthNames[d.getMonth()].toUpperCase();
  const y = d.getFullYear();
  return `${dd} ${m} ${y}`;
}

/** Very simple tokenizer placeholder:
 *  - split by spaces/punctuation
 *  - returns array of "tokens"
 * Later you can replace with a real tokenizer (BPE etc.)
 */
function tokenize(text: string): string[] {
  return text
    .trim()
    .split(/[\s]+|(?=[,.!?;:(){}\[\]])|(?<=[,.!?;:(){}\[\]])/g)
    .map(t => t.trim())
    .filter(Boolean);
}

type ChatRole = "user" | "agent";
type ChatMsg = {
  id: string;
  role: ChatRole;
  text: string;
  tokens?: string[];
  createdAt: number;
};

type ChatSession = {
  id: string;
  title: string;
  messages: ChatMsg[];
};

function uid(prefix = "id") {
  return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now()}`;
}

export default function Home() {
  // Month view default: Feb 2026
  const [viewYear, setViewYear] = useState(2026);
  const [viewMonth, setViewMonth] = useState(1);

  // Sidebar "today"
  const TODAY = useMemo(() => new Date(2026, 1, 2), []);

  // ===== Day/Month mode =====
  const [viewMode, setViewMode] = useState<"month" | "day">("month");
  const [selectedDay, setSelectedDay] = useState<string>(keyOf(new Date(2026, 1, 2)));

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
        { id: "m1", role: "agent", text: "Made An Appointment For Me", createdAt: Date.now() - 50000 },
        { id: "m2", role: "agent", text: "Ok Sir! Who is the appointment with, and when should it be?", createdAt: Date.now() - 49000 },
        { id: "m3", role: "user", text: "With my advisor, tomorrow afternoon", tokens: tokenize("With my advisor, tomorrow afternoon"), createdAt: Date.now() - 48000 },
        { id: "m4", role: "agent", text: "Got it. What duration do you want? 30 or 60 minutes?", createdAt: Date.now() - 47000 },
        { id: "m5", role: "user", text: "30 minutes", tokens: tokenize("30 minutes"), createdAt: Date.now() - 46000 },
      ],
    },
    { id: "s2", title: "Chat 2", messages: [] },
    { id: "s3", title: "Chat 3", messages: [] },
    { id: "s4", title: "Chat 4", messages: [] },
    { id: "s5", title: "Chat 5", messages: [] },
  ]);
  const [activeSessionId, setActiveSessionId] = useState("s1");
  const activeSession = useMemo(
    () => sessions.find(s => s.id === activeSessionId) || sessions[0],
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

  function pushUserMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;

    const tokens = tokenize(trimmed);

    // Store tokens for later sending to AI
    setTokenBuffer(prev => {
      const next = [...prev, ...tokens];
      console.log("TOKENS SENT (buffer):", next);
      return next;
    });

    // Save into current session as message + tokens
    setSessions(prev => prev.map(s => {
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
          }
        ],
      };
    }));

    setChatInput("");

    // Simulate AI response delay
    setIsTyping(true);
    setTimeout(() => {
      setSessions(prev => prev.map(s => {
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
            }
          ],
        };
      }));
      setIsTyping(false);
    }, 5000);
  }

  function newSession() {
    const id = uid("s");
    setSessions(prev => [{ id, title: `Chat ${prev.length + 1}`, messages: [] }, ...prev]);
    setActiveSessionId(id);
  }

  // Events store
  const [events, setEvents] = useState<EventMap>({
    "2026-02-02": [
      { id: 1, kind: "event", allDay: false, startMin: 600, endMin: 630, title: "Training", color: RAINBOW[3], location: "Gym", notes: "" },
      { id: 2, kind: "event", allDay: false, startMin: 660, endMin: 720, title: "Transfer window opens", color: RAINBOW[0], location: "Office", notes: "" }
    ],
    "2026-02-03": [
      { id: 3, kind: "task", allDay: false, startMin: 540, endMin: 600, title: "First Division", color: RAINBOW[5], location: "Library", notes: "" }
    ]
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
    setSelectedColors(prev =>
      prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]
    );
  }

  const allColors = useMemo(() => {
    const colors: string[] = [];
    Object.values(events).forEach(arr => arr.forEach(ev => colors.push(ev.color)));
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

      const filteredArr = arr.filter(ev => {
        if (kindFilter !== "all" && ev.kind !== kindFilter) return false;
        if (selectedColors.length > 0 && !selectedColors.includes(ev.color)) return false;
        if (q && !ev.title.toLowerCase().includes(q)) return false;
        if (locQ && !(ev.location || "").toLowerCase().includes(locQ)) return false;
        return true;
      });

      if (filteredArr.length > 0) out[dateKey] = filteredArr;
    });

    return out;
  }, [events, searchText, locationFilter, fromDate, toDate, kindFilter, selectedColors]);

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
    if (m < 0) { m = 11; y = y - 1; }
    setViewMonth(m);
    setViewYear(y);
  }
  function nextMonth() {
    let m = viewMonth + 1;
    let y = viewYear;
    if (m > 11) { m = 0; y = y + 1; }
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

  const todayWeekday = useMemo(() => TODAY.toLocaleDateString("en-US", { weekday: "short" }), [TODAY]);
  const todayMonthYear = useMemo(() => `${monthNames[TODAY.getMonth()]} ${TODAY.getFullYear()}`, [TODAY]);

  // Calendar cells (42) use FILTERED events
  const cells = useMemo(() => {
    const first = new Date(viewYear, viewMonth, 1);
    const startDow = first.getDay();
    const last = new Date(viewYear, viewMonth + 1, 0);
    const daysInMonth = last.getDate();
    const prevLast = new Date(viewYear, viewMonth, 0);
    const prevDays = prevLast.getDate();

    const out: Array<{ date: Date; muted: boolean; key: string; isToday: boolean; dayEvents: Ev[] }> = [];

    // CHANGED: 35 cells (5 rows) instead of 42 (6 rows)
    for (let i = 0; i < 35; i++) {
      let d: Date;
      let muted = false;

      if (i < startDow) {
        const day = prevDays - (startDow - 1 - i);
        d = new Date(viewYear, viewMonth - 1, day);
        muted = true;
      } else if (i >= startDow + daysInMonth) {
        const day = (i - (startDow + daysInMonth)) + 1;
        d = new Date(viewYear, viewMonth + 1, day);
        muted = true;
      } else {
        const day = (i - startDow) + 1;
        d = new Date(viewYear, viewMonth, day);
      }

      const k = keyOf(d);
      const dayEvents = (filteredEvents[k] || []).slice().sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));

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
      const arr = (next[mDate] ? [...next[mDate]] : []);
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
  const dayEvents = (filteredEvents[selectedDay] || []).slice().sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));

  const HOUR_PX = 56;              // height per hour (adjust 48–64)
  const DAY_START = 0;
  const DAY_END = 24 * 60;
  const HOURS = Array.from({ length: 25 }, (_, i) => i);

  function clamp(n: number, a: number, b: number) { return Math.max(a, Math.min(b, n)); }

  interface EventPortion {
    hour: number;
    start: number; // minutes within hour (0-60)
    end: number;   // minutes within hour (0-60)
    event: Ev;
  }

  function splitEventByHours(ev: Ev): EventPortion[] {
    const startTotal = ev.startMin ?? 0;
    const endTotal = ev.endMin ?? 0;
    const portions: EventPortion[] = [];

    const startHour = Math.floor(startTotal / 60);
    const endHour = Math.floor(endTotal / 60);

    for (let h = startHour; h <= endHour; h++) {
      if (h < 0 || h > 23) continue;
      const hStart = h * 60;
      const hEnd = (h + 1) * 60;

      const pStart = Math.max(startTotal, hStart);
      const pEnd = Math.min(endTotal, hEnd);

      if (pStart < pEnd) {
        portions.push({
          hour: h,
          start: pStart - hStart,
          end: pEnd - hStart,
          event: ev,
        });
      }
    }
    return portions;
  }

  function blockStyle(ev: Ev) {
    const start = clamp(ev.startMin, DAY_START, DAY_END);
    const end = clamp(ev.endMin, start, DAY_END);
    const total = DAY_END - DAY_START;

    const topPct = ((start - DAY_START) / total) * 100;
    const hPct = Math.max(1, ((end - start) / total) * 100);
    return { top: `${topPct}%`, height: `${hPct}%` };
  }

  return (
    <div className="container-fluid vh-100 p-0 d-flex flex-column overflow-hidden bg-dark">
      <div className="flex-grow-1 d-flex overflow-hidden">
        {/* SIDEBAR */}
        <aside className="d-flex flex-column gap-1 border-end border-dark bg-dark text-white" style={{ width: 300, minWidth: 300, backgroundColor: "#212529" }}>
          <div className="d-flex align-items-center gap-3 p-3">
            <div className="d-flex align-items-center justify-content-center rounded bg-secondary bg-opacity-25 text-white-50 fw-bold" style={{ width: 32, height: 32, fontSize: 12 }}>17</div>
            <div className="fw-semibold text-white">Smart Scheduler</div>
          </div>

          <div className="p-3">
            <div className="text-uppercase small text-info fw-bold letter-spacing-2 mb-1">Today</div>
            <div className="text-white-50 mb-0" style={{ fontSize: 14 }}>{todayMonthYear}</div>
            <div className="d-flex align-items-baseline gap-2">
              <div className="display-1 fw-bold lh-1" style={{ color: "#fd7e14" }}>{TODAY.getDate()}</div>
              <div className="small text-white-50">{todayWeekday}</div>
            </div>
          </div>

          <div className="px-3 flex-grow-1 overflow-auto">
            {/* Dashed separator */}
            <div className="border-top border-secondary border-dashed my-3 opacity-50" />

            {upcoming.length === 0 ? (
              <div className="small text-white-50">No matching events</div>
            ) : (
              <div className="d-flex flex-column gap-3">
                {upcoming.map((item) => {
                  const label = item.allDay ? "ALL DAY" : minutesToLabel(item.startMin);
                  return (
                    <div className="d-flex gap-2 align-items-start" key={`${item.dateKey}-${item.id}`}>
                      <div className="rounded-circle flex-shrink-0 mt-1" style={{ width: 8, height: 8, background: item.color }} />
                      <div className="d-flex flex-column overflow-hidden">
                        <div className="small text-white-50 font-monospace" style={{ fontSize: 11 }}>
                          {label}
                        </div>
                        <div className="text-white fw-bold text-uppercase small text-truncate" style={{ fontSize: 12, letterSpacing: "0.5px" }}>{item.title}</div>
                        <div className="small text-white-50 text-uppercase" style={{ fontSize: 10 }}>
                          {item.kind}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="p-3 mt-auto">
            {/* Dashed separator */}
            <div className="border-top border-secondary border-dashed mb-3 opacity-50" />

            <div className="d-flex align-items-center justify-content-center gap-4">
              {/* HotKeys */}
              <button
                type="button"
                className="btn btn-dark rounded-circle d-flex align-items-center justify-content-center border border-secondary p-0"
                style={{ width: 40, height: 40 }}
                title="HotKeys"
                onClick={() => setHotkeysOpen(true)}
              >
                <span className="small text-white-50">⌘</span>
              </button>

              {/* Chat button (middle) */}
              <button
                type="button"
                className="btn btn-primary rounded-circle d-flex align-items-center justify-content-center shadow p-0"
                style={{ width: 48, height: 48, background: "#5a4ad1", borderColor: "#5a4ad1" }}
                title="Chat"
                onClick={() => setChatOpen(true)}
              >
                <span className="fs-5">🤖</span>
              </button>

              {/* Profile */}
              <button
                type="button"
                className="btn btn-dark rounded-circle d-flex align-items-center justify-content-center border border-secondary p-0"
                style={{ width: 40, height: 40 }}
                title="Profile"
              >
                <span className="small text-white-50">👤</span>
              </button>
            </div>
          </div>
        </aside>

        {/* MAIN */}
        <main className="flex-grow-1 d-flex flex-column bg-light text-dark overflow-hidden">
          {/* ONLY show month header when in month view */}
          {viewMode === "month" && (
            <div className="d-flex align-items-center justify-content-between px-4 py-3 border-bottom border-light-subtle bg-white">
              {/* Left: Month Navigation */}
              <div className="d-flex align-items-center gap-3">
                <button className="btn btn-link text-dark text-decoration-none p-0 fw-bold fs-4" onClick={prevMonth}>&lt;</button>
                <div className="text-uppercase fw-bold fs-4 ls-1">{monthTitle}</div>
                <button className="btn btn-link text-dark text-decoration-none p-0 fw-bold fs-4" onClick={nextMonth}>&gt;</button>
              </div>

              {/* Right: Search & Filter */}
              <div className="d-flex align-items-center justify-content-end gap-2" style={{ width: 340 }}>
                <div className="position-relative flex-grow-1">
                  <input
                    className="form-control border border-secondary-subtle bg-light text-dark rounded-pill ps-4"
                    placeholder="Search events..."
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    style={{ fontSize: 13, height: 36, fontFamily: 'var(--font-geist-sans)' }}
                  />
                  <span className="position-absolute end-0 top-50 translate-middle-y me-3 text-secondary">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                  </span>
                </div>

                <div className="position-relative">
                  <button
                    className={`btn d-flex align-items-center justify-content-center p-0 position-relative shadow-sm transition-all ${filterOpen || activeFilterCount > 0 ? 'btn-dark' : 'btn-light border border-secondary-subtle text-dark'}`}
                    style={{ width: 36, height: 36, borderRadius: 10 }}
                    title="Filter"
                    onClick={() => setFilterOpen(v => !v)}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
                    {activeFilterCount > 0 && <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger border border-light p-1" style={{ width: 8, height: 8 }}> </span>}
                  </button>

                  {filterOpen && (
                    <div className="position-absolute end-0 top-100 mt-2 p-4 bg-white rounded-4 shadow-xl border border-light-subtle z-3" style={{ width: 320, fontFamily: 'var(--font-geist-sans)' }}>
                      <div className="d-flex align-items-center justify-content-between mb-4">
                        <div className="fw-bold small text-uppercase text-secondary letter-spacing-2">Filters</div>
                        {activeFilterCount > 0 && <span className="badge bg-primary bg-opacity-10 text-primary rounded-pill small">{activeFilterCount} Active</span>}
                      </div>

                      <div className="mb-4">
                        <label className="small fw-bold text-dark mb-2 d-block">Type</label>
                        <div className="d-flex gap-2 p-1 bg-light rounded-pill border">
                          {(["all", "event", "task"] as const).map(k => (
                            <button
                              key={k}
                              className={`flex-grow-1 btn btn-sm rounded-pill fw-semibold small ${kindFilter === k ? 'btn-white shadow-sm text-dark' : 'text-muted border-0 hover-bg-gray'}`}
                              onClick={() => setKindFilter(k)}
                              type="button"
                              style={{ transition: 'all 0.2s', fontSize: 11 }}
                            >
                              {k === 'all' ? 'All' : k.charAt(0).toUpperCase() + k.slice(1)}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="mb-4">
                        <label className="small fw-bold text-dark mb-2 d-block">Date Range</label>
                        <div className="d-flex align-items-center gap-2">
                          <input type="date" className="form-control form-control-sm rounded-3 bg-light border-0" value={fromDate} onChange={(e) => setFromDate(e.target.value)} style={{ fontSize: 12 }} />
                          <span className="text-muted small">to</span>
                          <input type="date" className="form-control form-control-sm rounded-3 bg-light border-0" value={toDate} onChange={(e) => setToDate(e.target.value)} style={{ fontSize: 12 }} />
                        </div>
                      </div>

                      <div className="mb-4">
                        <label className="small fw-bold text-dark mb-2 d-block">Location</label>
                        <input
                          className="form-control form-control-sm rounded-3 bg-light border-0"
                          placeholder="Filter by location..."
                          value={locationFilter}
                          onChange={(e) => setLocationFilter(e.target.value)}
                          style={{ fontSize: 12 }}
                        />
                      </div>

                      <div className="mb-4">
                        <label className="small fw-bold text-dark mb-2 d-block">Color Tag</label>
                        <div className="d-flex gap-2 flex-wrap">
                          {allColors.map((c) => (
                            <button
                              key={c}
                              type="button"
                              className={`rounded-circle d-flex align-items-center justify-content-center transition-all ${selectedColors.includes(c) ? 'ring-2 ring-offset-1' : 'opacity-75 hover-opacity-100'}`}
                              style={{
                                width: 28,
                                height: 28,
                                background: c,
                                cursor: 'pointer',
                                border: selectedColors.includes(c) ? `2px solid ${c}` : '2px solid transparent', // Fallback
                                boxShadow: selectedColors.includes(c) ? '0 0 0 2px white, 0 0 0 4px #e5e7eb' : 'none',
                                transform: selectedColors.includes(c) ? 'scale(1.1)' : 'scale(1)'
                              }}
                              onClick={() => toggleColor(c)}
                              title={c}
                            >
                              {selectedColors.includes(c) && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="d-flex justify-content-end gap-2 pt-3 border-top border-light py-1">
                        <button type="button" className="btn btn-sm text-secondary hover-text-dark fw-medium" onClick={clearAllFilters}>
                          Reset
                        </button>
                        <button type="button" className="btn btn-sm btn-dark rounded-pill px-4 fw-bold shadow-sm" onClick={() => setFilterOpen(false)}>
                          Apply
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="position-relative">
                  <button
                    className="btn btn-light border border-secondary-subtle text-dark rounded-3 d-flex align-items-center justify-content-center p-0 shadow-sm"
                    style={{ width: 36, height: 36 }}
                    title="Add Event"
                    onClick={openModal}
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ===== SWITCH MONTH / DAY ===== */}
          {viewMode === "month" ? (
            <section className="flex-grow-1 d-flex flex-column overflow-hidden bg-white">
              <div className="d-grid gap-0 border-bottom border-light-subtle" style={{ gridTemplateColumns: "repeat(7, 1fr)" }}>
                <div className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle" style={{ fontSize: 11, letterSpacing: 1 }}>Sunday</div>
                <div className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle" style={{ fontSize: 11, letterSpacing: 1 }}>Monday</div>
                <div className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle" style={{ fontSize: 11, letterSpacing: 1 }}>Tuesday</div>
                <div className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle" style={{ fontSize: 11, letterSpacing: 1 }}>Wednesday</div>
                <div className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle" style={{ fontSize: 11, letterSpacing: 1 }}>Thursday</div>
                <div className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle" style={{ fontSize: 11, letterSpacing: 1 }}>Friday</div>
                <div className="text-center py-2 small fw-bold text-uppercase text-secondary" style={{ fontSize: 11, letterSpacing: 1 }}>Saturday</div>
              </div>

              <div className="flex-grow-1 d-grid gap-0 overflow-hidden" style={{ gridTemplateColumns: "repeat(7, 1fr)", gridAutoRows: "1fr" }}>
                {cells.map((c, idx) => {
                  const shown = c.dayEvents.slice(0, 3);
                  const moreCount = Math.max(0, c.dayEvents.length - shown.length);

                  return (
                    <div
                      key={`${c.key}-${idx}`}
                      className={[
                        "p-2 border-end border-bottom position-relative overflow-hidden",
                        c.muted ? "bg-light text-muted" : "bg-white",
                        c.isToday ? "bg-primary bg-opacity-10 shadow-inset" : ""
                      ].join(" ")}
                      style={{ minHeight: 80, cursor: 'pointer' }}
                      onClick={() => {
                        setSelectedDay(c.key);
                        setViewMode("day");
                      }}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          setSelectedDay(c.key);
                          setViewMode("day");
                        }
                      }}
                    >
                      <div className={`p-2 fw-bold small ${c.muted ? "text-secondary opacity-50" : "text-dark"}`}>{c.date.getDate()}</div>

                      <div className="d-flex flex-column gap-1 mt-1">
                        {shown.map((ev) => (
                          <div key={ev.id} className="d-flex align-items-center gap-1 px-2 py-1 rounded-3 border overflow-hidden shadow-sm" style={{ borderLeft: `3px solid ${ev.color}`, backgroundColor: `color-mix(in srgb, ${ev.color} 15%, #ffffff)`, borderColor: `color-mix(in srgb, ${ev.color} 30%, #dee2e6)` }}>
                            <div className="text-truncate small fw-semibold text-dark flex-grow-1" style={{ fontSize: 11 }}>{ev.title}</div>
                            {ev.startMin !== undefined && !ev.allDay && <div className="small text-secondary text-nowrap" style={{ fontSize: 10 }}>{minutesToLabel(ev.startMin)}</div>}
                          </div>
                        ))}
                        {moreCount > 0 && <div className="px-2 small text-secondary fw-bold" style={{ fontSize: 11 }}>+{moreCount} more</div>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          ) : (
            <section className="flex-grow-1 d-flex flex-column overflow-hidden bg-white">
              <div className="d-flex align-items-center justify-content-between p-3 border-bottom">
                <div className="d-flex align-items-center gap-2">
                  <button
                    className="btn btn-outline-secondary btn-sm rounded-3"
                    onClick={() => setSelectedDay(addDaysISO(selectedDay, -1))}
                    aria-label="Previous day"
                  >
                    ‹
                  </button>

                  <div className="h5 mb-0 fw-bold">{dayHeaderLabel(selectedDay)}</div>

                  <button
                    className="btn btn-outline-secondary btn-sm rounded-3"
                    onClick={() => setSelectedDay(addDaysISO(selectedDay, 1))}
                    aria-label="Next day"
                  >
                    ›
                  </button>
                </div>

                <button
                  className="btn btn-outline-secondary btn-sm rounded-pill px-3 fw-bold"
                  onClick={() => setViewMode("month")}
                  type="button"
                >
                  Month View
                </button>
              </div>



              <div className="d-flex flex-column flex-grow-1 overflow-hidden bg-white">
                {/* Minute Header */}
                <div className="d-flex border-bottom bg-light bg-opacity-75" style={{ height: 26 }}>
                  <div style={{ width: 80, fontSize: 10, fontWeight: 600 }} className="border-end bg-light d-flex align-items-center justify-content-center text-muted">min</div>
                  <div className="flex-grow-1 d-flex">
                    {[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60].map(m => (
                      <div key={m} className="flex-grow-1 text-center text-muted border-end d-flex align-items-center justify-content-center" style={{ fontSize: 10, flexBasis: 0, fontWeight: 500, fontFamily: 'var(--font-geist-sans), sans-serif' }}>
                        {`:${String(m).padStart(2, "0")}`}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="d-flex flex-column flex-grow-1">
                  {HOURS.map(h => {
                    const timedEvents = dayEvents.filter(e => !e.allDay && ((e.endMin ?? 0) - (e.startMin ?? 0)) < 720);
                    const allPortions = timedEvents.flatMap(splitEventByHours);
                    const rowPortions = allPortions.filter(p => p.hour === h);

                    // Vertical stacking within row if minutes overlap
                    const stacks: EventPortion[][] = [];
                    rowPortions.sort((a, b) => a.start - b.start).forEach(p => {
                      let placed = false;
                      for (const s of stacks) {
                        const last = s[s.length - 1];
                        if (p.start < last.end) {
                          s.push(p);
                          placed = true;
                          break;
                        }
                      }
                      if (!placed) stacks.push([p]);
                    });

                    return (
                      <div key={h} className="d-flex border-bottom border-light-subtle flex-grow-1" style={{ borderBottomStyle: "solid", borderBottomWidth: 1, borderColor: "#f0f0f0", minHeight: 0 }}>
                        {/* Hour Label */}
                        <div className="d-flex align-items-center justify-content-end pe-3 text-dark fw-bold border-end bg-light bg-opacity-25" style={{ width: 80, fontSize: 12, fontFamily: 'var(--font-geist-sans), sans-serif' }}>
                          {`${String(h).padStart(2, "0")}:00`}
                        </div>

                        {/* Minute Grid & Events */}
                        <div className="flex-grow-1 position-relative h-100 bg-white">
                          {/* Minute Grid lines (every 5m) */}
                          <div className="d-flex h-100 position-absolute w-100" style={{ zIndex: 0 }}>
                            {Array.from({ length: 12 }).map((_, i) => (
                              <div key={i} className="flex-grow-1 h-100 border-end" style={{ flexBasis: 0, borderColor: "#f8f9fa" }} />
                            ))}
                          </div>

                          {/* Event Portion Bars */}
                          {rowPortions.map(p => {
                            const left = (p.start / 60) * 100;
                            const width = Math.max(1, ((p.end - p.start) / 60) * 100);

                            // Vertical stacking offset
                            const stack = stacks.find(s => s.includes(p));
                            const stackIdx = stack ? stack.indexOf(p) : 0;
                            const stackDepth = stack ? stack.length : 1;
                            const hPct = 100 / stackDepth;
                            const topPct = stackIdx * hPct;

                            return (
                              <div
                                key={`${p.event.id}-${h}`}
                                className="position-absolute rounded-2 border shadow-sm overflow-hidden d-flex flex-column justify-content-center px-2"
                                style={{
                                  left: `${left}%`,
                                  width: `calc(${width}% - 2px)`,
                                  top: `${topPct + 4}%`,
                                  height: `${hPct - 8}%`,
                                  borderLeft: `4px solid ${p.event.color}`,
                                  backgroundColor: `color-mix(in srgb, ${p.event.color} 15%, #ffffff)`,
                                  borderColor: `color-mix(in srgb, ${p.event.color} 30%, #dee2e6)`,
                                  zIndex: 1,
                                  minWidth: 12,
                                  transition: 'all 0.2s ease',
                                  lineHeight: '1.2'
                                }}
                                title={`${p.event.title} • ${minutesToLabel(p.event.startMin)} - ${minutesToLabel(p.event.endMin)}`}
                              >
                                <div className="text-truncate fw-bold text-dark" style={{ fontSize: 11, fontFamily: 'var(--font-geist-sans), sans-serif' }}>
                                  {p.event.title}
                                </div>
                                <div className="text-truncate text-secondary d-flex align-items-center gap-1" style={{ fontSize: 9, fontFamily: 'var(--font-geist-sans), sans-serif' }}>
                                  <span>{minutesToLabel(p.event.startMin)} - {minutesToLabel(p.event.endMin)}</span>
                                  <span className="opacity-50">|</span>
                                  <span className="text-truncate">{p.event.location || 'No Location'}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>
          )}

          {/* ===== HOTKEYS OVERLAY (placeholder) ===== */}
          {/* ===== HOTKEYS OVERLAY ===== */}
          <div
            className={`position-fixed inset-0 z-3 p-4 d-flex align-items-center justify-content-center ${hotkeysOpen ? '' : 'd-none'}`}
            style={{ backgroundColor: "rgba(0,0,0,.5)", top: 0, left: 0, right: 0, bottom: 0 }}
            aria-hidden={!hotkeysOpen}
          >
            <div className="bg-dark bg-opacity-75 text-white rounded-4 shadow-lg border border-start-0 border-top-0 border-end-0 border-bottom-0 border-secondary overflow-hidden position-relative" style={{ width: "min(920px, 94vw)", height: "min(520px, 82vh)", backdropFilter: "blur(10px)" }}>
              <div className="d-flex align-items-center justify-content-between p-3">
                <div className="small fw-bold text-uppercase letter-spacing-2 text-white-50">HotKeys</div>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-light rounded-3"
                  onClick={() => setHotkeysOpen(false)}
                  aria-label="Close HotKeys"
                >
                  ×
                </button>
              </div>

              <div className="d-grid align-items-center justify-items-center h-100 p-4" style={{ gridTemplateColumns: "1fr 280px 1fr", gridTemplateRows: "1fr 140px 1fr 1fr", gridTemplateAreas: `". top ." "leftTop core rightTop" "leftBottom core rightBottom" ". bottom ."` }}>
                {/* center = CLOSE */}
                <button
                  type="button"
                  className="rounded-circle bg-white border-0 shadow-lg d-flex align-items-center justify-content-center"
                  style={{ gridArea: "core", width: 130, height: 130, cursor: 'pointer' }}
                  onClick={() => setHotkeysOpen(false)}
                  aria-label="Close HotKeys"
                  title="Close"
                >
                  <span className="h1 mb-0">×</span>
                </button>

                <button type="button" className="btn btn-light rounded-pill shadow fw-bold p-3" style={{ gridArea: "top", width: "min(320px, 90%)" }}>Placeholder</button>
                <button type="button" className="btn btn-light rounded-pill shadow fw-bold p-3" style={{ gridArea: "leftTop", width: "min(320px, 90%)" }}>Placeholder</button>
                <button type="button" className="btn btn-light rounded-pill shadow fw-bold p-3" style={{ gridArea: "rightTop", width: "min(320px, 90%)" }}>Placeholder</button>
                <button type="button" className="btn btn-light rounded-pill shadow fw-bold p-3" style={{ gridArea: "leftBottom", width: "min(320px, 90%)" }}>Placeholder</button>
                <button type="button" className="btn btn-light rounded-pill shadow fw-bold p-3" style={{ gridArea: "rightBottom", width: "min(320px, 90%)" }}>Placeholder</button>
                <button type="button" className="btn btn-light rounded-pill shadow fw-bold p-3 align-self-start mt-2" style={{ gridArea: "bottom", width: "min(320px, 90%)" }}>Placeholder</button>
              </div>

              {/* 
              <div className="position-absolute bottom-0 start-0 p-3 small text-white-50">
                (AI panel placeholder — we’ll connect actions later)
              </div> 
              */}
            </div>
          </div>

          {/* ===== CHAT MODAL (placeholder) ===== */}
          {/* ===== CHAT MODAL ===== */}
          <div
            className={`position-fixed inset-0 z-3 p-4 d-flex align-items-center justify-content-center ${chatOpen ? '' : 'd-none'}`}
            style={{ backgroundColor: "rgba(0,0,0,.5)", top: 0, left: 0, right: 0, bottom: 0 }}
            aria-hidden={!chatOpen}
          >
            <div className="d-flex bg-white bg-opacity-25 backdrop-blur rounded-4 shadow-lg border border-white border-opacity-25 overflow-hidden" style={{ width: "min(980px, 94vw)", height: "min(560px, 86vh)", backdropFilter: "blur(10px)" }}>
              {/* Left: history */}
              <aside className="d-flex flex-column bg-white border-end flex-shrink-0" style={{ width: 260, minWidth: 260 }}>
                <div className="d-flex align-items-center justify-content-between px-3 border-bottom flex-shrink-0" style={{ height: 64, boxSizing: 'border-box' }}>
                  <div className="small fw-bold text-uppercase ls-1">Your Chats</div>
                  <button className="btn btn-sm btn-outline-secondary rounded-3 py-0 px-2 fw-bold" style={{ height: 28 }} type="button" onClick={newSession}>＋</button>
                </div>

                <div className="flex-grow-1 overflow-auto p-2" style={{ minHeight: 0 }}>
                  {sessions.map(s => (
                    <button
                      key={s.id}
                      type="button"
                      className={`w-100 text-start btn btn-sm mb-1 position-relative ${s.id === activeSessionId ? 'bg-secondary bg-opacity-10 text-dark fw-bold border-start border-3 border-primary' : 'btn-ghost text-muted'}`}
                      style={{ paddingLeft: s.id === activeSessionId ? '11px' : '12px', borderTopLeftRadius: 0, borderBottomLeftRadius: 0 }}
                      onClick={() => setActiveSessionId(s.id)}
                    >
                      {s.title}
                    </button>
                  ))}
                </div>

                <div className="d-flex align-items-center gap-2 px-3 border-top bg-light flex-shrink-0" style={{ height: 80, boxSizing: 'border-box' }}>
                  <div className="rounded-circle bg-secondary bg-opacity-25 d-flex align-items-center justify-content-center" style={{ width: 32, height: 32 }}>👤</div>
                  <div className="small fw-bold">John Doe</div>
                </div>
              </aside>

              {/* Center: chat */}
              <section className="flex-grow-1 d-flex flex-column bg-white" style={{ minWidth: 0 }}>
                <div className="d-flex align-items-center justify-content-between px-3 border-bottom flex-shrink-0" style={{ height: 64, boxSizing: 'border-box' }}>
                  <div className="d-flex align-items-center gap-2">
                    <span className="fs-5">🤖</span>
                    <span className="fw-bold">Scheduler Agent</span>
                  </div>

                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary rounded-3 shadow-sm"
                    style={{ height: 28, width: 28, padding: 0, lineHeight: 1 }}
                    onClick={() => setChatOpen(false)}
                    aria-label="Close chat"
                  >
                    ×
                  </button>
                </div>

                <div className="flex-grow-1 overflow-auto p-3 d-flex flex-column gap-3" style={{ minHeight: 0 }}>
                  {activeSession?.messages?.length ? (
                    activeSession.messages.map(msg => (
                      <div
                        key={msg.id}
                        className={`d-flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                      >
                        {msg.role === "agent" && <div className="fs-5">🤖</div>}
                        <div
                          className={`p-3 rounded-4 shadow-sm ${msg.role === "user" ? "bg-primary text-white" : "bg-light text-dark"}`}
                          style={{ maxWidth: "70%" }}
                          title={msg.tokens ? `Tokens: ${msg.tokens.join(" | ")}` : ""}
                        >
                          {msg.text}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-muted mt-5">
                      No messages yet. Type something!
                    </div>
                  )}

                  {/* Typing Indicator */}
                  {isTyping && (
                    <div className="d-flex gap-2">
                      <div className="fs-5">🤖</div>
                      <div className="p-3 rounded-4 shadow-sm bg-light text-dark d-flex align-items-center" style={{ maxWidth: "70%" }}>
                        <div className="typing-dots">
                          <span></span><span></span><span></span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                <form
                  className="px-3 border-top d-flex align-items-center gap-2 bg-light flex-shrink-0"
                  style={{ height: 80, boxSizing: 'border-box' }}
                  onSubmit={(e) => {
                    e.preventDefault();
                    pushUserMessage(chatInput);
                  }}
                >
                  <input
                    className="form-control rounded-pill shadow-sm border-secondary-subtle"
                    placeholder="Enter Message"
                    style={{ height: 44 }}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                  />
                  <button className="btn btn-primary rounded-circle shadow-sm d-flex align-items-center justify-content-center" style={{ width: 44, height: 44 }} type="submit" aria-label="Send">
                    ➤
                  </button>
                </form>

                {/* Token Buffer logic maintained, UI removed */}

              </section>
            </div>
          </div>

          {/* ===== MODAL ===== */}
          <div
            className={`position-fixed inset-0 z-3 p-4 d-flex align-items-center justify-content-center ${open ? '' : 'd-none'}`}
            style={{ backgroundColor: "rgba(0,0,0,.5)", top: 0, left: 0, right: 0, bottom: 0 }}
            aria-hidden={!open}
            onClick={(e) => {
              if (e.target === e.currentTarget) setOpen(false);
            }}
          >
            <div className="bg-white rounded-4 shadow-lg border border-light-subtle overflow-hidden position-relative" style={{ width: "min(720px, 92vw)" }}>
              <button type="button" className="btn btn-sm btn-light position-absolute top-0 end-0 m-3 rounded-3 z-1 shadow-sm border" onClick={() => setOpen(false)} aria-label="Close">
                ×
              </button>

              <div className="p-4 bg-light border-bottom border-dashed">
                <input
                  className="form-control form-control-lg fw-bold bg-transparent border-0 shadow-none px-0"
                  style={{ fontSize: 24 }}
                  value={mTitle}
                  onChange={(e) => setMTitle(e.target.value)}
                  placeholder="Add Title"
                />

                <div className="d-flex justify-content-center gap-3 mt-3">
                  <div
                    className={`btn btn-sm fw-bold rounded-pill px-4 ${modalKind === "event" ? 'btn-white shadow-sm text-dark' : 'btn-light text-secondary border-0'}`}
                    onClick={() => setModalKind("event")}
                    role="button"
                  >
                    Event
                  </div>
                  <div
                    className={`btn btn-sm fw-bold rounded-pill px-4 ${modalKind === "task" ? 'btn-white shadow-sm text-dark' : 'btn-light text-secondary border-0'}`}
                    onClick={() => setModalKind("task")}
                    role="button"
                  >
                    Task
                  </div>
                </div>
              </div>

              <div className="p-4 bg-white/50">
                <form onSubmit={saveEvent} className="d-flex flex-column gap-3">
                  <div className="d-flex gap-3">
                    <div className="text-secondary d-flex align-items-center justify-content-center" style={{ width: 44, height: 44 }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
                        <circle cx="12" cy="12" r="9"></circle>
                        <path d="M12 7v6l4 2"></path>
                      </svg>
                    </div>

                    <div className="flex-grow-1 p-3 rounded-4 bg-light border">
                      <div className="d-flex flex-wrap align-items-center gap-2">
                        <span className="badge bg-secondary bg-opacity-10 text-dark fw-bold px-2 py-1">{prettyDate}</span>

                        <input
                          className="form-control form-control-sm border-0 bg-secondary bg-opacity-10 text-dark fw-bold text-center p-1 rounded-2"
                          style={{ width: 80 }}
                          type="time"
                          value={mStart}
                          onChange={(e) => setMStart(e.target.value)}
                          disabled={mAllDay}
                          min={mAllDay ? undefined : (isTodaySelected ? minStart : "00:00")}
                        />

                        <input
                          className="form-control form-control-sm border-0 bg-secondary bg-opacity-10 text-dark fw-bold text-center p-1 rounded-2"
                          style={{ width: 80 }}
                          type="time"
                          value={mEnd}
                          onChange={(e) => setMEnd(e.target.value)}
                          disabled={mAllDay}
                          min={mAllDay ? undefined : mStart}
                        />

                        <div className="form-check form-switch ms-2">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id="mAllDay"
                            checked={mAllDay}
                            onChange={(e) => setMAllDay(e.target.checked)}
                          />
                          <label className="form-check-label small fw-bold" htmlFor="mAllDay">All Day</label>
                        </div>
                      </div>

                      <input
                        className="form-control form-control-sm mt-2 border-0 bg-transparent px-0"
                        type="date"
                        value={mDate}
                        onChange={(e) => setMDate(e.target.value)}
                        min={realTodayKey}
                      />
                    </div>
                  </div>

                  <div className="d-flex gap-3">
                    <div className="text-secondary d-flex align-items-center justify-content-center" style={{ width: 44, height: 44 }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
                        <path d="M12 22s7-6 7-12a7 7 0 1 0-14 0c0 6 7 12 7 12z"></path>
                        <circle cx="12" cy="10" r="2"></circle>
                      </svg>
                    </div>
                    <div className="flex-grow-1 p-2 rounded-4 bg-light border">
                      <input
                        className="form-control border-0 bg-transparent shadow-none"
                        placeholder="Add Location"
                        value={mLocation}
                        onChange={(e) => setMLocation(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="d-flex gap-3">
                    <div className="text-secondary d-flex align-items-center justify-content-center" style={{ width: 44, height: 44 }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
                        <path d="M12 20h9"></path>
                        <path d="M16.5 3.5a2.1 2.0 0 0 1 3 3L7 19l-4 1 1-4Z"></path>
                      </svg>
                    </div>
                    <div className="flex-grow-1 p-2 rounded-4 bg-light border">
                      <textarea
                        className="form-control border-0 bg-transparent shadow-none"
                        placeholder="Add Notes"
                        rows={3}
                        value={mNotes}
                        onChange={(e) => setMNotes(e.target.value)}
                        style={{ resize: "vertical", minHeight: 60 }}
                      />
                    </div>
                  </div>

                  <div className="d-flex gap-3">
                    <div className="text-secondary d-flex align-items-center justify-content-center" style={{ width: 44, height: 44 }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="24" height="24">
                        <path d="M12 22a10 10 0 0 1 0-20"></path>
                        <path d="M12 2a10 10 0 1 0 10 10"></path>
                        <path d="M12 12l8-4"></path>
                      </svg>
                    </div>
                    <div className="flex-grow-1 p-3 rounded-4 bg-light border">
                      <div className="d-flex align-items-center gap-3 flex-wrap">
                        <span className="small fw-bold text-secondary">Color</span>
                        <div className="d-flex gap-2 flex-wrap">
                          {RAINBOW.map((c) => (
                            <div
                              key={c}
                              className={`rounded-circle border border-2 ${mColor === c ? 'border-dark shadow-sm' : 'border-transparent'}`}
                              style={{ width: 24, height: 24, background: c, cursor: 'pointer' }}
                              onClick={() => setMColor(c)}
                              title={c}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="d-flex justify-content-end pt-3">
                    <button className="btn btn-primary rounded-pill px-5 fw-bold shadow" type="submit">Save</button>
                  </div>
                </form>
              </div>
            </div>
          </div>

        </main>
      </div >
    </div >
  );
}
