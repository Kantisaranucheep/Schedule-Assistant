import React, { useState, useMemo, useEffect } from "react";
import { Kind, Ev } from "../../types";
import {
    RAINBOW,
    timeToMinutes,
    keyOf,
    roundUpTimeHHMM,
    nowTimeHHMM,
    parseISODate,
    prettyDow,
    prettyMonth
} from "../../utils";

interface EventModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (event: Ev, date: string) => void;
    events: Record<string, Ev[]>;
}

export default function EventModal({
    isOpen,
    onClose,
    onSave,
    events,
}: EventModalProps) {
    const realTodayKey = useMemo(() => keyOf(new Date()), []);

    // Form State
    const [modalKind, setModalKind] = useState<Kind>("event");
    const [mTitle, setMTitle] = useState("");
    const [mDate, setMDate] = useState<string>(realTodayKey);
    const [mStart, setMStart] = useState("09:00");
    const [mEnd, setMEnd] = useState("09:00");
    const [mAllDay, setMAllDay] = useState(false);
    const [mLocation, setMLocation] = useState("");
    const [mNotes, setMNotes] = useState("");
    const [mColor, setMColor] = useState<string>(RAINBOW[1]);

    const isTodaySelected = mDate === realTodayKey;

    // Reset form on open
    useEffect(() => {
        if (isOpen) {
            const t = setTimeout(() => {
                setModalKind("event");
                setMTitle("");
                setMDate(realTodayKey);
                setMStart("09:00");
                setMEnd("09:00");
                setMAllDay(false);
                setMLocation("");
                setMNotes("");
                setMColor(RAINBOW[1]);
            }, 0);
            return () => clearTimeout(t);
        }
    }, [isOpen, realTodayKey]);

    const minStart = useMemo(() => {
        if (!isTodaySelected || mAllDay) return "";
        return roundUpTimeHHMM(nowTimeHHMM(), 5);
    }, [isTodaySelected, mAllDay]);

    const handleStartChange = (val: string) => {
        let newVal = val;
        if (isTodaySelected && !mAllDay) {
            const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
            if (val < ms) newVal = ms;
        }
        setMStart(newVal);
        if (mEnd < newVal) setMEnd(newVal);
    };

    const handleEndChange = (val: string) => {
        let newVal = val;
        if (isTodaySelected && !mAllDay) {
            const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
            if (val < ms) newVal = ms;
        }
        if (newVal < mStart) newVal = mStart;
        setMEnd(newVal);
    };

    const handleDateChange = (val: string) => {
        setMDate(val);
        if (val === realTodayKey && !mAllDay) {
            const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
            if (mStart < ms) {
                setMStart(ms);
                if (mEnd < ms) setMEnd(ms);
            }
        }
    };

    const startMinVal = mAllDay ? 0 : timeToMinutes(mStart);
    const endMinVal = mAllDay ? 0 : timeToMinutes(mEnd);
    const duration = endMinVal - startMinVal;

    const existingOnDay = events[mDate] || [];
    const conflict = !mAllDay && existingOnDay.find(ex => {
        if (ex.allDay) return false;
        return (startMinVal < (ex.endMin ?? 0)) && (endMinVal > (ex.startMin ?? 0));
    });

    const isDurationTooShort = !mAllDay && duration < 5;
    const isPastTime = !mAllDay && isTodaySelected && mStart < minStart;
    const isInvalidTime = !mAllDay && endMinVal < startMinVal;

    const canSave = mTitle.trim() !== "" && !conflict && !isDurationTooShort && !isPastTime && !isInvalidTime;

    function saveEvent(e: React.FormEvent) {
        e.preventDefault();
        const title = mTitle.trim();
        if (!title) return;

        if (mDate < realTodayKey) {
            alert("You cannot choose a past date.");
            return;
        }

        if (!mAllDay) {
            if (isTodaySelected) {
                const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
                if (mStart < ms) {
                    alert("Start time cannot be in the past.");
                    setMStart(ms);
                    return;
                }
            }
            if (isInvalidTime) {
                alert("End time cannot be earlier than start time.");
                setMEnd(mStart);
                return;
            }
            if (isDurationTooShort) {
                alert("Event duration must be at least 5 minutes.");
                return;
            }
            if (conflict) {
                alert(`Time conflict! You cannot have multiple tasks at the same time (overlaps with "${conflict.title}").`);
                return;
            }
        }

        const newItem: Ev = {
            id: Date.now(),
            kind: modalKind,
            allDay: mAllDay,
            startMin: startMinVal,
            endMin: endMinVal,
            title,
            color: mColor || RAINBOW[1],
            location: mLocation.trim(),
            notes: mNotes.trim(),
        };

        onSave(newItem, mDate);
    }

    const prettyDate = useMemo(() => {
        const dt = parseISODate(mDate);
        return `${prettyDow(dt)}, ${dt.getDate()} ${prettyMonth(dt)}`;
    }, [mDate]);

    return (
        <div
            className={`position-fixed inset-0 z-3 p-4 d-flex align-items-center justify-content-center ${isOpen ? "" : "d-none"
                }`}
            style={{
                backgroundColor: "rgba(0,0,0,.5)",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
            }}
            aria-hidden={!isOpen}
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
        >
            <div
                className="bg-white rounded-4 shadow-lg border border-light-subtle overflow-hidden position-relative"
                style={{ width: "min(720px, 92vw)" }}
            >
                <button
                    type="button"
                    className="btn btn-sm btn-light position-absolute top-0 end-0 m-3 rounded-3 z-1 shadow-sm border"
                    onClick={onClose}
                    aria-label="Close"
                >
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
                            className={`btn btn-sm fw-bold rounded-pill px-4 ${modalKind === "event"
                                ? "btn-white shadow-sm text-dark"
                                : "btn-light text-secondary border-0"
                                }`}
                            onClick={() => setModalKind("event")}
                            role="button"
                        >
                            Event
                        </div>
                        <div
                            className={`btn btn-sm fw-bold rounded-pill px-4 ${modalKind === "task"
                                ? "btn-white shadow-sm text-dark"
                                : "btn-light text-secondary border-0"
                                }`}
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
                            <div
                                className="text-secondary d-flex align-items-center justify-content-center"
                                style={{ width: 44, height: 44 }}
                            >
                                <svg
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    width="24"
                                    height="24"
                                >
                                    <circle cx="12" cy="12" r="9"></circle>
                                    <path d="M12 7v6l4 2"></path>
                                </svg>
                            </div>

                            <div className="flex-grow-1 p-3 rounded-4 bg-light border">
                                <div className="d-flex flex-wrap align-items-center gap-2">
                                    <span className="badge bg-secondary bg-opacity-10 text-dark fw-bold px-2 py-1">
                                        {prettyDate}
                                    </span>

                                    <input
                                        className="form-control form-control-sm border-0 bg-secondary bg-opacity-10 text-dark fw-bold text-center p-1 rounded-2"
                                        style={{ width: 120 }}
                                        type="time"
                                        value={mStart}
                                        onChange={(e) => handleStartChange(e.target.value)}
                                        disabled={mAllDay}
                                        min={
                                            mAllDay
                                                ? undefined
                                                : isTodaySelected
                                                    ? minStart
                                                    : "00:00"
                                        }
                                    />

                                    <input
                                        className="form-control form-control-sm border-0 bg-secondary bg-opacity-10 text-dark fw-bold text-center p-1 rounded-2"
                                        style={{ width: 120 }}
                                        type="time"
                                        value={mEnd}
                                        onChange={(e) => handleEndChange(e.target.value)}
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
                                        <label
                                            className="form-check-label small fw-bold"
                                            htmlFor="mAllDay"
                                        >
                                            All Day
                                        </label>
                                    </div>
                                </div>

                                {conflict && (
                                    <div className="mt-2 text-danger small fw-bold d-flex align-items-center gap-1">
                                        ⚠️ Time conflict! Overlaps with &quot;{conflict.title}&quot;
                                    </div>
                                )}
                                {isDurationTooShort && (
                                    <div className="mt-2 text-warning small fw-bold d-flex align-items-center gap-1">
                                        ⚠️ Minimum duration is 5 minutes
                                    </div>
                                )}
                                {isPastTime && (
                                    <div className="mt-2 text-danger small fw-bold d-flex align-items-center gap-1">
                                        ⚠️ Cannot schedule in the past
                                    </div>
                                )}
                                {isInvalidTime && (
                                    <div className="mt-2 text-danger small fw-bold d-flex align-items-center gap-1">
                                        ⚠️ End time must be after start time
                                    </div>
                                )}

                                <input
                                    className="form-control form-control-sm mt-2 border-0 bg-transparent px-0"
                                    type="date"
                                    value={mDate}
                                    onChange={(e) => handleDateChange(e.target.value)}
                                    min={realTodayKey}
                                />
                            </div>
                        </div>

                        <div className="d-flex gap-3">
                            <div
                                className="text-secondary d-flex align-items-center justify-content-center"
                                style={{ width: 44, height: 44 }}
                            >
                                <svg
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    width="24"
                                    height="24"
                                >
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
                            <div
                                className="text-secondary d-flex align-items-center justify-content-center"
                                style={{ width: 44, height: 44 }}
                            >
                                <svg
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    width="24"
                                    height="24"
                                >
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
                            <div
                                className="text-secondary d-flex align-items-center justify-content-center"
                                style={{ width: 44, height: 44 }}
                            >
                                <svg
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    width="24"
                                    height="24"
                                >
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
                                                className={`rounded-circle border border-2 ${mColor === c
                                                    ? "border-dark shadow-sm"
                                                    : "border-transparent"
                                                    }`}
                                                style={{
                                                    width: 24,
                                                    height: 24,
                                                    background: c,
                                                    cursor: "pointer",
                                                }}
                                                onClick={() => setMColor(c)}
                                                title={c}
                                            />
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="d-flex justify-content-end pt-3">
                            <button
                                className="btn btn-primary rounded-pill px-5 fw-bold shadow"
                                type="submit"
                                disabled={!canSave}
                            >
                                Save
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
