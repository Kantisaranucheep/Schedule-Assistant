import React, { useMemo } from "react";
import { Ev, EventMap } from "../types";
import { minutesToLabel, keyOf, monthNames } from "../utils";

interface SidebarProps {
    filteredEvents: EventMap;
    onNotificationsClick: () => void;
    onChatClick: () => void;
    onProfileClick: () => void;
    onLogoClick: () => void;
    onEventClick: (dateKey: string) => void;
    onViewEvent: (dateKey: string, ev: Ev) => void;
}

export default function Sidebar({
    filteredEvents,
    onNotificationsClick,
    onChatClick,
    onProfileClick,
    onLogoClick,
    onEventClick,
    onViewEvent,
}: SidebarProps) {
    // Sidebar "today"
    const TODAY = useMemo(() => new Date(), []);

    const todayWeekday = useMemo(
        () => TODAY.toLocaleDateString("en-US", { weekday: "short" }),
        [TODAY]
    );
    const todayMonthYear = useMemo(
        () => `${monthNames[TODAY.getMonth()]} ${TODAY.getFullYear()}`,
        [TODAY]
    );

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

    return (
        <aside
            className="d-flex flex-column gap-1 border-end border-dark bg-dark text-white"
            style={{ width: 300, minWidth: 300, backgroundColor: "#212529" }}
        >
            <div className="d-flex align-items-center gap-3 p-3">
                <div
                    className="d-flex align-items-center justify-content-center"
                    style={{ width: 40, height: 40, fontSize: 24 }}
                >
                    📅
                </div>
                <div className="fw-semibold text-white fs-5 letter-spacing-1">Smart Scheduler</div>
            </div>

            <div
                className="p-3 transition-all hover-white-10 rounded-3 m-2"
                style={{ cursor: "pointer" }}
                onClick={onLogoClick}
                title="Go to Today"
            >
                <div className="text-uppercase small text-info fw-bold letter-spacing-2 mb-1">
                    Today
                </div>
                <div className="text-white-50 mb-0" style={{ fontSize: 14 }}>
                    {todayMonthYear}
                </div>
                <div className="d-flex align-items-baseline gap-2">
                    <div className="display-1 fw-bold lh-1" style={{ color: "#fd7e14" }}>
                        {TODAY.getDate()}
                    </div>
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
                            const label = item.allDay
                                ? "ALL DAY"
                                : minutesToLabel(item.startMin);
                            return (
                                <div
                                    className="d-flex gap-2 align-items-start p-2 rounded-3 transition-all hover-white-10"
                                    key={`${item.dateKey}-${item.id}`}
                                    style={{ cursor: "pointer", position: "relative" }}
                                    onClick={() => onEventClick(item.dateKey)}
                                >
                                    <div
                                        className="rounded-circle flex-shrink-0 mt-1"
                                        style={{ width: 8, height: 8, background: item.color }}
                                    />
                                    <div className="d-flex flex-column overflow-hidden flex-grow-1">
                                        <div
                                            className="small text-white-50 font-monospace"
                                            style={{ fontSize: 11 }}
                                        >
                                            {label}
                                        </div>
                                        <div
                                            className="text-white fw-bold text-uppercase small text-truncate"
                                            style={{ fontSize: 12, letterSpacing: "0.5px" }}
                                        >
                                            {item.title}
                                        </div>
                                        <div
                                            className="small text-white-50 text-uppercase"
                                            style={{ fontSize: 10 }}
                                        >
                                            {item.kind}
                                        </div>
                                    </div>
                                    <div className="d-flex align-items-center ms-1 justify-content-center" onClick={(e) => e.stopPropagation()}>
                                        <button
                                            className="btn btn-sm border-0 p-1 lh-1 text-white-50 hover-text-white z-2"
                                            style={{ position: "relative" }}
                                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onViewEvent(item.dateKey, item); }}
                                            title="View details"
                                        >
                                            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                                                <circle cx="12" cy="12" r="10"></circle>
                                                <line x1="12" y1="16" x2="12" y2="12"></line>
                                                <line x1="12" y1="8" x2="12.01" y2="8"></line>
                                            </svg>
                                        </button>
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
                    {/* Notifications */}
                    <button
                        type="button"
                        className="btn btn-dark rounded-circle d-flex align-items-center justify-content-center border border-secondary p-0 transition-all hover-white-10"
                        style={{ width: 40, height: 40 }}
                        title="Notifications"
                        onClick={onNotificationsClick}
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" className="bi bi-bell text-white-50" viewBox="0 0 16 16">
                            <path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2M8 1.918l-.797.161A4 4 0 0 0 4 6c0 .628-.134 2.197-.459 3.742-.16.767-.376 1.566-.663 2.258h10.244c-.287-.692-.502-1.49-.663-2.258C12.134 8.197 12 6.628 12 6a4 4 0 0 0-3.203-3.92zM14.22 12c.223.447.481.801.78 1H1c.299-.199.557-.553.78-1C2.68 10.2 3 6.88 3 6c0-2.42 1.72-4.44 4.005-4.901a1 1 0 1 1 1.99 0A5 5 0 0 1 13 6c0 .88.32 4.2 1.22 6" />
                        </svg>
                    </button>

                    {/* Chat button (middle) */}
                    <button
                        type="button"
                        className="btn btn-primary rounded-circle d-flex align-items-center justify-content-center shadow p-0"
                        style={{
                            width: 48,
                            height: 48,
                            background: "#5a4ad1",
                            borderColor: "#5a4ad1",
                        }}
                        title="Chat"
                        onClick={onChatClick}
                    >
                        <span className="fs-5">🤖</span>
                    </button>

                    {/* Account Email */}
                    <button
                        type="button"
                        className="btn btn-dark rounded-circle d-flex align-items-center justify-content-center border border-secondary p-0 transition-all hover-white-10"
                        style={{ width: 40, height: 40 }}
                        title="Account Email"
                        onClick={onProfileClick}
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" className="text-white-50" viewBox="0 0 16 16">
                            <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 0 0-1-1zm13 2.383-4.708 2.825L15 11.105zm-.034 6.876-5.64-3.471L8 9.583l-1.326-.795-5.64 3.471A1 1 0 0 0 2 13h12a1 1 0 0 0 .966-.741ZM1 11.105l4.708-2.897L1 5.383z"/>
                        </svg>
                    </button>
                </div>
            </div>
        </aside>
    );
}
