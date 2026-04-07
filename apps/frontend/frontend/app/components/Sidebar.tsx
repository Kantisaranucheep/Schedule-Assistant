import React, { useMemo } from "react";
import { Ev, EventMap } from "../types";
import { minutesToLabel, keyOf, monthNames, parseISODate } from "../utils";

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
            {/* Logo Section */}
            <div
                className="d-flex align-items-center gap-2 p-3 border-bottom border-light-subtle hover-lift transition-all"
                style={{ cursor: "pointer" }}
                onClick={onLogoClick}
            >
                <div style={{ width: 28, height: 28 }} className="flex-shrink-0">
                    <svg id="Layer_1" data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122.88 121" width="100%" height="100%">
                        <defs><style>{`.cls-1{fill:#ef4136;}.cls-1,.cls-3,.cls-4,.cls-6{fill-rule:evenodd;}.cls-2{fill:gray;}.cls-3{fill:#fff;}.cls-4{fill:#c72b20;}.cls-5,.cls-6{fill:#1a1a1a;}`}</style></defs>
                        <title>calendar-color</title>
                        <path className="cls-1" d="M11.52,6.67h99.84a11.57,11.57,0,0,1,11.52,11.52V44.94H0V18.19A11.56,11.56,0,0,1,11.52,6.67Zm24.79,9.75A9.31,9.31,0,1,1,27,25.73a9.31,9.31,0,0,1,9.31-9.31Zm49.79,0a9.31,9.31,0,1,1-9.31,9.31,9.31,9.31,0,0,1,9.31-9.31Z" />
                        <path className="cls-2" d="M111.36,121H11.52A11.57,11.57,0,0,1,0,109.48V40H122.88v69.46A11.56,11.56,0,0,1,111.36,121Z" />
                        <path className="cls-3" d="M12.75,117.31h97.38a9.1,9.1,0,0,0,9.06-9.06V40H3.69v68.23a9.09,9.09,0,0,0,9.06,9.06Z" />
                        <path className="cls-4" d="M86.1,14.63a11.11,11.11,0,1,1-7.85,3.26l.11-.1a11.06,11.06,0,0,1,7.74-3.16Zm0,1.79a9.31,9.31,0,1,1-9.31,9.31,9.31,9.31,0,0,1,9.31-9.31Z" />
                        <path className="cls-4" d="M36.31,14.63a11.11,11.11,0,1,1-7.85,3.26l.11-.1a11.08,11.08,0,0,1,7.74-3.16Zm0,1.79A9.31,9.31,0,1,1,27,25.73a9.31,9.31,0,0,1,9.31-9.31Z" />
                        <path className="cls-5" d="M80.54,4.56C80.54,2,83,0,86.1,0s5.56,2,5.56,4.56V25.77c0,2.51-2.48,4.56-5.56,4.56s-5.56-2-5.56-4.56V4.56Z" />
                        <path className="cls-5" d="M30.75,4.56C30.75,2,33.24,0,36.31,0s5.56,2,5.56,4.56V25.77c0,2.51-2.48,4.56-5.56,4.56s-5.56-2-5.56-4.56V4.56Z" />
                        <path className="cls-6" d="M22,85.62H36a1.79,1.79,0,0,1,1.79,1.79v11.7A1.8,1.8,0,0,1,36,100.9H22a1.8,1.8,0,0,1-1.8-1.79V87.41A1.8,1.8,0,0,1,22,85.62Z" />
                        <path className="cls-6" d="M54.58,85.62H68.64a1.79,1.79,0,0,1,1.79,1.79v11.7a1.8,1.8,0,0,1-1.79,1.79H54.58a1.8,1.8,0,0,1-1.79-1.79V87.41a1.8,1.8,0,0,1,1.79-1.79Z" />
                        <path className="cls-6" d="M86.87,85.62h14.06a1.8,1.8,0,0,1,1.79,1.79v11.7a1.8,1.8,0,0,1-1.79,1.79H86.87a1.8,1.8,0,0,1-1.79-1.79V87.41a1.79,1.79,0,0,1,1.79-1.79Z" />
                        <path className="cls-6" d="M22,56.42H36a1.8,1.8,0,0,1,1.79,1.8V69.91A1.8,1.8,0,0,1,36,71.7H22a1.8,1.8,0,0,1-1.8-1.79V58.22a1.81,1.81,0,0,1,1.8-1.8Z" />
                        <path className="cls-6" d="M54.58,56.42H68.64a1.8,1.8,0,0,1,1.79,1.8V69.91a1.8,1.8,0,0,1-1.79,1.79H54.58a1.79,1.79,0,0,1-1.79-1.79V58.22a1.8,1.8,0,0,1,1.79-1.8Z" />
                        <path className="cls-6" d="M86.87,56.42h14.06a1.8,1.8,0,0,1,1.79,1.8V69.91a1.8,1.8,0,0,1-1.79,1.79H86.87a1.79,1.79,0,0,1-1.79-1.79V58.22a1.8,1.8,0,0,1,1.79-1.8Z" />
                    </svg>
                </div>
                <div className="fw-bold fs-5 text-uppercase letter-spacing-1 text-white">Smart Scheduler</div>
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
                            const dt = parseISODate(item.dateKey);
                            const dayName = dt.toLocaleDateString("en-US", { weekday: "short" });
                            const dayDate = dt.getDate();
                            const monthName = dt.toLocaleDateString("en-US", { month: "short" });
                            const timeLabel = item.allDay ? "ALL DAY" : minutesToLabel(item.startMin);
                            const label = `${dayName}, ${monthName} ${dayDate} • ${timeLabel}`;
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
                        <div style={{ width: 28, height: 28 }} className="flex-shrink-0">
                            <svg viewBox="0 0 512 512" fill="currentColor" className="text-white">
                                <title>ai</title>
                                <g id="Page-1" stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
                                    <g id="icon" fill="currentColor" transform="translate(64.000000, 64.000000)">
                                        <path d="M320,64 L320,320 L64,320 L64,64 L320,64 Z M171.749388,128 L146.817842,128 L99.4840387,256 L121.976629,256 L130.913039,230.977 L187.575039,230.977 L196.319607,256 L220.167172,256 L171.749388,128 Z M260.093778,128 L237.691519,128 L237.691519,256 L260.093778,256 L260.093778,128 Z M159.094727,149.47526 L181.409039,213.333 L137.135039,213.333 L159.094727,149.47526 Z M341.333333,256 L384,256 L384,298.666667 L341.333333,298.666667 L341.333333,256 Z M85.3333333,341.333333 L128,341.333333 L128,384 L85.3333333,384 L85.3333333,341.333333 Z M170.666667,341.333333 L213.333333,341.333333 L213.333333,384 L170.666667,384 L170.666667,341.333333 Z M85.3333333,0 L128,0 L128,42.6666667 L85.3333333,42.6666667 L85.3333333,0 Z M256,341.333333 L298.666667,341.333333 L298.666667,384 L256,384 L256,341.333333 Z M170.666667,0 L213.333333,0 L213.333333,42.6666667 L170.666667,42.6666667 L170.666667,0 Z M256,0 L298.666667,0 L298.666667,42.6666667 L256,42.6666667 L256,0 Z M341.333333,170.666667 L384,170.666667 L384,213.333333 L341.333333,213.333333 L341.333333,170.666667 Z M0,256 L42.6666667,256 L42.6666667,298.666667 L0,298.666667 L0,256 Z M341.333333,85.3333333 L384,85.3333333 L384,128 L341.333333,128 L341.333333,85.3333333 Z M0,170.666667 L42.6666667,170.666667 L42.6666667,213.333333 L0,213.333333 L0,170.666667 Z M0,85.3333333 L42.6666667,85.3333333 L42.6666667,128 L0,128 L0,85.3333333 Z" id="Combined-Shape" />
                                    </g>
                                </g>
                            </svg>
                        </div>
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
                            <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 0 0-1-1zm13 2.383-4.708 2.825L15 11.105zm-.034 6.876-5.64-3.471L8 9.583l-1.326-.795-5.64 3.471A1 1 0 0 0 2 13h12a1 1 0 0 0 .966-.741ZM1 11.105l4.708-2.897L1 5.383z" />
                        </svg>
                    </button>
                </div>
            </div>
        </aside>
    );
}
