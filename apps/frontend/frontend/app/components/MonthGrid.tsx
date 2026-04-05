import React from "react";
import { Ev } from "../types";
import { minutesToLabel } from "../utils";

interface Cell {
    date: Date;
    muted: boolean;
    key: string;
    isToday: boolean;
    dayEvents: Ev[];
}

interface MonthGridProps {
    cells: Cell[];
    onSelectDay: (key: string) => void;
    setViewMode: (mode: "month" | "day") => void;
    onViewEvent: (dateKey: string, ev: Ev) => void;
}

export default function MonthGrid({ cells, onSelectDay, setViewMode, onViewEvent }: MonthGridProps) {
    return (
        <section className="flex-grow-1 d-flex flex-column overflow-hidden bg-white">
            <div
                className="d-grid gap-0 border-bottom border-light-subtle"
                style={{ gridTemplateColumns: "repeat(7, 1fr)" }}
            >
                <div
                    className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle"
                    style={{ fontSize: 11, letterSpacing: 1 }}
                >
                    Sunday
                </div>
                <div
                    className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle"
                    style={{ fontSize: 11, letterSpacing: 1 }}
                >
                    Monday
                </div>
                <div
                    className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle"
                    style={{ fontSize: 11, letterSpacing: 1 }}
                >
                    Tuesday
                </div>
                <div
                    className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle"
                    style={{ fontSize: 11, letterSpacing: 1 }}
                >
                    Wednesday
                </div>
                <div
                    className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle"
                    style={{ fontSize: 11, letterSpacing: 1 }}
                >
                    Thursday
                </div>
                <div
                    className="text-center py-2 small fw-bold text-uppercase text-secondary border-end border-light-subtle"
                    style={{ fontSize: 11, letterSpacing: 1 }}
                >
                    Friday
                </div>
                <div
                    className="text-center py-2 small fw-bold text-uppercase text-secondary"
                    style={{ fontSize: 11, letterSpacing: 1 }}
                >
                    Saturday
                </div>
            </div>

            <div
                className="flex-grow-1 d-grid gap-0 overflow-hidden"
                style={{
                    gridTemplateColumns: "repeat(7, 1fr)",
                    gridAutoRows: "1fr",
                }}
            >
                {cells.map((c, idx) => {
                    // Sort events by time: all-day/tasks first, then by startMin
                    const sortedEvents = [...c.dayEvents].sort((a, b) => {
                        // Tasks and all-day events come first
                        const aIsAllDay = a.allDay || a.kind === "task";
                        const bIsAllDay = b.allDay || b.kind === "task";
                        if (aIsAllDay && !bIsAllDay) return -1;
                        if (!aIsAllDay && bIsAllDay) return 1;
                        // Then sort by start time
                        return (a.startMin ?? 0) - (b.startMin ?? 0);
                    });
                    const shown = sortedEvents.slice(0, 3);
                    const moreCount = Math.max(0, sortedEvents.length - shown.length);

                    return (
                        <div
                            key={`${c.key}-${idx}`}
                            className={[
                                "p-1 border-end border-bottom position-relative overflow-hidden d-flex flex-column",
                                c.muted ? "bg-light text-muted" : "bg-white",
                                c.isToday ? "bg-primary bg-opacity-10 shadow-inset" : "",
                            ].join(" ")}
                            style={{
                                cursor: "pointer",
                                boxShadow: c.isToday ? "inset 0 3px 0 0 var(--bs-primary)" : undefined
                            }}
                            onClick={() => {
                                onSelectDay(c.key);
                                setViewMode("day");
                            }}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                    onSelectDay(c.key);
                                    setViewMode("day");
                                }
                            }}
                        >
                            <div
                                className={`px-1 fw-bold small flex-shrink-0 ${c.muted ? "text-secondary opacity-50" : "text-dark"
                                    }`}
                                style={{ fontSize: 12, paddingTop: c.isToday ? 2 : 0 }}
                            >
                                {c.date.getDate()}
                            </div>

                            <div className="d-flex flex-column flex-grow-1 justify-content-start" style={{ gap: 2 }}>
                                {shown.map((ev) => (
                                    <div
                                        key={ev.id}
                                        className="d-flex align-items-center px-1 rounded-2 overflow-hidden"
                                        style={{
                                            borderLeft: `3px solid ${ev.color}`,
                                            backgroundColor: `color-mix(in srgb, ${ev.color} 15%, #ffffff)`,
                                            cursor: "pointer",
                                            height: 25,
                                        }}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onViewEvent(c.key, ev);
                                        }}
                                    >
                                        <div
                                            className="text-truncate fw-semibold text-dark flex-grow-1"
                                            style={{ fontSize: 10 }}
                                        >
                                            {ev.title}
                                        </div>
                                        {ev.startMin !== undefined && !ev.allDay && ev.kind !== "task" && (
                                            <div
                                                className="text-secondary text-nowrap ms-1"
                                                style={{ fontSize: 9 }}
                                            >
                                                {minutesToLabel(ev.startMin)}
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {moreCount > 0 && (
                                    <div
                                        className="px-1 text-secondary fw-bold"
                                        style={{ fontSize: 10 }}
                                    >
                                        +{moreCount}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}
