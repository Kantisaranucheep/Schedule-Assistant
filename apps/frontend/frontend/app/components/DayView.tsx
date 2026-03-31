import React from "react";
import { Ev } from "../types";
import { addDaysISO, dayHeaderLabel, minutesToLabel } from "../utils";

interface DayViewProps {
    dayEvents: Ev[];
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
}: DayViewProps) {
    return (
        <section className="flex-grow-1 d-flex flex-column overflow-hidden bg-white shadow-sm">
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
                    const timedEvents = dayEvents.filter(
                        (e) => !e.allDay && (e.endMin ?? 0) - (e.startMin ?? 0) < 720
                    );
                    const allPortions = timedEvents.flatMap(splitEventByHours);
                    const rowPortions = allPortions.filter((p) => p.hour === h);

                    // Vertical stacking within row if minutes overlap
                    const stacks: EventPortion[][] = [];
                    rowPortions
                        .sort((a, b) => a.start - b.start)
                        .forEach((p) => {
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
                        <div
                            key={h}
                            className="d-flex border-bottom border-light flex-grow-1 row-hover-bg transition-colors"
                            style={{
                                minHeight: 50,
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
                                {`${String(h).padStart(2, "0")}:00`}
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

                                    // Vertical stacking offset
                                    const stack = stacks.find((s) => s.includes(p));
                                    const stackIdx = stack ? stack.indexOf(p) : 0;
                                    const stackDepth = stack ? stack.length : 1;
                                    const hPct = 100 / stackDepth;
                                    const topPct = stackIdx * hPct;

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
