import React from "react";
import { Ev } from "../types";
import { minutesToLabel } from "../utils";

interface SidebarProps {
    today: Date;
    todayMonthYear: string;
    todayWeekday: string;
    upcoming: ({ dateKey: string } & Ev)[];
    onHotkeysClick: () => void;
    onChatClick: () => void;
    onProfileClick: () => void;
    onLogoClick: () => void;
    onEventClick: (dateKey: string) => void;
}

export default function Sidebar({
    today,
    todayMonthYear,
    todayWeekday,
    upcoming,
    onHotkeysClick,
    onChatClick,
    onProfileClick,
    onLogoClick,
    onEventClick,
}: SidebarProps) {
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
                        {today.getDate()}
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
                                    style={{ cursor: "pointer" }}
                                    onClick={() => onEventClick(item.dateKey)}
                                >
                                    <div
                                        className="rounded-circle flex-shrink-0 mt-1"
                                        style={{ width: 8, height: 8, background: item.color }}
                                    />
                                    <div className="d-flex flex-column overflow-hidden">
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
                        onClick={onHotkeysClick}
                    >
                        <span className="small text-white-50">⌘</span>
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

                    {/* Profile */}
                    <button
                        type="button"
                        className="btn btn-dark rounded-circle d-flex align-items-center justify-content-center border border-secondary p-0"
                        style={{ width: 40, height: 40 }}
                        title="Profile"
                        onClick={onProfileClick}
                    >
                        <span className="small text-white-50">👤</span>
                    </button>
                </div>
            </div>
        </aside>
    );
}
