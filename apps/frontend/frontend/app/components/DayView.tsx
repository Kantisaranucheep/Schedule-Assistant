import React from "react";
import { Ev } from "../types";
import { addDaysISO, minutesToLabel } from "../utils";

interface DayViewProps {
    dayEvents: Ev[];
    selectedDay: string;
    onViewEvent: (dateKey: string, ev: Ev) => void;
}

interface EventPortion {
    hour: number;
    start: number; // minutes within hour (0-60)
    end: number; // minutes within hour (0-60)
    event: Ev;
}

const HOURS = Array.from({ length: 24 }, (_, i) => i);

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

export default function DayView({
    dayEvents,
    selectedDay,
    onViewEvent,
}: DayViewProps) {
    // Separate tasks from timed events
    const tasks = dayEvents.filter(e => e.kind === "task");
    const timedEvents = dayEvents.filter(e => e.kind === "event" && !e.allDay && (e.endMin ?? 0) - (e.startMin ?? 0) < 720);
    const allDayEvents = dayEvents.filter(e => e.kind === "event" && e.allDay);

    return (
        <section className="flex-grow-1 d-flex flex-column overflow-hidden bg-white shadow-sm">
            {/* Tasks Section - shown at top if there are tasks */}
            {tasks.length > 0 && (
                <div className="border-bottom bg-light bg-opacity-25 p-3">
                    <div className="d-flex align-items-center gap-2 mb-2">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16" className="text-secondary">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                            <line x1="16" y1="2" x2="16" y2="6"></line>
                            <line x1="8" y1="2" x2="8" y2="6"></line>
                            <line x1="3" y1="10" x2="21" y2="10"></line>
                        </svg>
                        <span className="small fw-bold text-secondary text-uppercase" style={{ letterSpacing: "1px", fontSize: 11 }}>
                            Tasks
                        </span>
                    </div>
                    <div className="d-flex flex-wrap gap-2">
                        {tasks.map(task => (
                            <div
                                key={task.id}
                                className="d-flex align-items-center gap-2 px-3 py-2 rounded-3 border shadow-sm bg-white hover-lift transition-all"
                                style={{
                                    borderLeft: `4px solid ${task.color}`,
                                    cursor: "pointer",
                                }}
                                onClick={() => onViewEvent(selectedDay, task)}
                                role="button"
                                tabIndex={0}
                            >
                                <span className="fw-semibold small text-dark">{task.title}</span>
                                {task.location && (
                                    <span className="text-muted small" style={{ fontSize: 11 }}>
                                        • {task.location}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* All Day Events Section */}
            {allDayEvents.length > 0 && (
                <div className="border-bottom bg-light bg-opacity-25 p-3">
                    <div className="d-flex align-items-center gap-2 mb-2">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16" className="text-secondary">
                            <circle cx="12" cy="12" r="9"></circle>
                            <path d="M12 7v6l4 2"></path>
                        </svg>
                        <span className="small fw-bold text-secondary text-uppercase" style={{ letterSpacing: "1px", fontSize: 11 }}>
                            All Day
                        </span>
                    </div>
                    <div className="d-flex flex-wrap gap-2">
                        {allDayEvents.map(event => (
                            <div
                                key={event.id}
                                className="d-flex align-items-center gap-2 px-3 py-2 rounded-3 border shadow-sm bg-white hover-lift transition-all"
                                style={{
                                    borderLeft: `4px solid ${event.color}`,
                                    cursor: "pointer",
                                }}
                                onClick={() => onViewEvent(selectedDay, event)}
                                role="button"
                                tabIndex={0}
                            >
                                <span className="fw-semibold small text-dark">{event.title}</span>
                                {event.location && (
                                    <span className="text-muted small" style={{ fontSize: 11 }}>
                                        • {event.location}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Minute Header */}
            <div
                className="d-flex border-bottom bg-light bg-opacity-50"
                style={{ height: 28 }}
            >
                <div
                    style={{ width: 90, fontSize: 11, fontWeight: 700, letterSpacing: "1px" }}
                    className="border-end bg-light d-flex align-items-center justify-content-center text-secondary text-uppercase"
                >
                    Time
                </div>
                <div className="flex-grow-1 d-flex">
                    {[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60].map((m) => (
                        <div
                            key={m}
                            className="flex-grow-1 text-muted border-end d-flex align-items-center justify-content-center"
                            style={{
                                fontSize: 11,
                                flexBasis: 0,
                                fontWeight: 700,
                                fontFamily: "var(--font-geist-sans), sans-serif",
                                fontVariantNumeric: "tabular-nums",
                                backgroundColor: m % 15 === 0 ? "rgba(0,0,0,0.03)" : "transparent",
                            }}
                        >
                            {`:${String(m).padStart(2, "0")}`}
                        </div>
                    ))}
                </div>
            </div>

            <div className="d-flex flex-column flex-grow-1 overflow-auto custom-scrollbar">
                {HOURS.map((h) => {
                    const allPortions = timedEvents.flatMap(splitEventByHours);
                    const rowPortions = allPortions.filter((p) => p.hour === h);

                    // Overlapping events stacking: compute overlap groups
                    const overlapGroups: EventPortion[][] = [];
                    const sorted = [...rowPortions].sort((a, b) => a.start - b.start);
                    for (const p of sorted) {
                        let placed = false;
                        for (const g of overlapGroups) {
                            if (g.some(existing => p.start < existing.end && p.end > existing.start)) {
                                g.push(p);
                                placed = true;
                                break;
                            }
                        }
                        if (!placed) overlapGroups.push([p]);
                    }
                    // Flatten: for each portion, find its group index and group size
                    const portionMeta = new Map<EventPortion, { idx: number; total: number }>();
                    for (const g of overlapGroups) {
                        g.forEach((p, i) => portionMeta.set(p, { idx: i, total: g.length }));
                    }
                    const maxOverlap = overlapGroups.reduce((max, g) => Math.max(max, g.length), 1);
                    const rowHeight = Math.max(50, maxOverlap * 32);

                    return (
                        <div
                            key={h}
                            className="d-flex border-bottom border-light flex-grow-1 row-hover-bg transition-colors"
                            style={{
                                minHeight: rowHeight,
                                borderBottomStyle: "solid",
                                borderBottomWidth: 1,
                                borderColor: "#f5f5f5",
                            }}
                        >
                            {/* Hour Label */}
                            <div
                                className="d-flex align-items-center justify-content-end pe-3 text-dark fw-bold border-end bg-light bg-opacity-25"
                                style={{
                                    width: 90,
                                    fontSize: 13,
                                    fontFamily: "var(--font-geist-sans), sans-serif",
                                    color: "#444"
                                }}
                            >
                                {`${h === 0 ? 0 : (h % 12 || 12)} ${h >= 12 ? "PM" : "AM"}`}
                            </div>

                            {/* Minute Grid & Events */}
                            <div className="flex-grow-1 position-relative h-100 bg-white">
                                {/* Minute Grid lines (every 5m) */}
                                <div
                                    className="d-flex h-100 position-absolute w-100"
                                    style={{ zIndex: 0 }}
                                >
                                    {Array.from({ length: 12 }).map((_, i) => (
                                        <div
                                            key={i}
                                            className="flex-grow-1 h-100 border-end"
                                            style={{
                                                flexBasis: 0,
                                                borderColor: (i + 1) % 3 === 0 ? "#eeeeee" : "#fbfbfb"
                                            }}
                                        />
                                    ))}
                                </div>

                                {/* Event Portion Bars */}
                                {rowPortions.map((p) => {
                                    const left = (p.start / 60) * 100;
                                    const width = Math.max(1, ((p.end - p.start) / 60) * 100);

                                    // Vertical stacking offset for overlapping events
                                    const meta = portionMeta.get(p) || { idx: 0, total: 1 };
                                    const hPct = 100 / meta.total;
                                    const topPct = meta.idx * hPct;

                                    return (
                                        <div
                                            key={`${p.event.id}-${h}`}
                                            className="position-absolute rounded-3 border shadow-sm overflow-hidden d-flex flex-column justify-content-center px-3 py-1 event-hover-lift transition-all"
                                            style={{
                                                left: `${left}%`,
                                                width: `calc(${width}% - 3px)`,
                                                top: `${topPct + 6}%`,
                                                height: `${hPct - 12}%`,
                                                borderLeft: `4px solid ${p.event.color}`,
                                                backgroundColor: `color-mix(in srgb, ${p.event.color} 12%, #ffffff)`,
                                                borderColor: `color-mix(in srgb, ${p.event.color} 25%, #dee2e6)`,
                                                zIndex: 1,
                                                minWidth: 20,
                                                lineHeight: "1.2",
                                                boxShadow: "0 2px 4px rgba(0,0,0,0.04)"
                                            }}
                                            title={`${p.event.title} • ${minutesToLabel(
                                                p.event.startMin
                                            )} - ${minutesToLabel(p.event.endMin)}`}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onViewEvent(selectedDay, p.event);
                                            }}
                                            role="button"
                                            tabIndex={0}
                                        >
                                            <div
                                                className="text-truncate fw-bold text-dark"
                                                style={{
                                                    fontSize: 12,
                                                    fontFamily: "var(--font-geist-sans), sans-serif",
                                                    letterSpacing: "-0.2px"
                                                }}
                                            >
                                                {p.event.title}
                                            </div>
                                            <div
                                                className="text-truncate text-secondary d-flex align-items-center gap-2"
                                                style={{
                                                    fontSize: 10,
                                                    fontFamily: "var(--font-geist-sans), sans-serif",
                                                    opacity: 0.8
                                                }}
                                            >
                                                <span className="fw-semibold">
                                                    {minutesToLabel(p.event.startMin)}
                                                </span>
                                                <span className="opacity-30">|</span>
                                                <span className="text-truncate">
                                                    {p.event.location || "No Location"}
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}
