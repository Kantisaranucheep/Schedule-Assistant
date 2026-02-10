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
}

export default function MonthGrid({ cells, onSelectDay, setViewMode }: MonthGridProps) {
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
                    const shown = c.dayEvents.slice(0, 3);
                    const moreCount = Math.max(0, c.dayEvents.length - shown.length);

                    return (
                        <div
                            key={`${c.key}-${idx}`}
                            className={[
                                "p-2 border-end border-bottom position-relative overflow-hidden",
                                c.muted ? "bg-light text-muted" : "bg-white",
                                c.isToday ? "bg-primary bg-opacity-10 shadow-inset" : "",
                            ].join(" ")}
                            style={{ minHeight: 80, cursor: "pointer" }}
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
                                className={`p-2 fw-bold small ${c.muted ? "text-secondary opacity-50" : "text-dark"
                                    }`}
                            >
                                {c.date.getDate()}
                            </div>

                            <div className="d-flex flex-column gap-1 mt-1">
                                {shown.map((ev) => (
                                    <div
                                        key={ev.id}
                                        className="d-flex align-items-center gap-1 px-2 py-1 rounded-3 border overflow-hidden shadow-sm"
                                        style={{
                                            borderLeft: `3px solid ${ev.color}`,
                                            backgroundColor: `color-mix(in srgb, ${ev.color} 15%, #ffffff)`,
                                            borderColor: `color-mix(in srgb, ${ev.color} 30%, #dee2e6)`,
                                        }}
                                    >
                                        <div
                                            className="text-truncate small fw-semibold text-dark flex-grow-1"
                                            style={{ fontSize: 11 }}
                                        >
                                            {ev.title}
                                        </div>
                                        {ev.startMin !== undefined && !ev.allDay && (
                                            <div
                                                className="small text-secondary text-nowrap"
                                                style={{ fontSize: 10 }}
                                            >
                                                {minutesToLabel(ev.startMin)}
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {moreCount > 0 && (
                                    <div
                                        className="px-2 small text-secondary fw-bold"
                                        style={{ fontSize: 11 }}
                                    >
                                        +{moreCount} more
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
