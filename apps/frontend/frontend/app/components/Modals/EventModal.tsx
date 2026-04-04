import React, { useState, useMemo, useEffect } from "react";
import { Kind, Ev, EventCategory } from "../../types";
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
    editingEvent?: { event: Ev, dateKey: string } | null;
    categories: EventCategory[];
    onAddCategory: (cat: EventCategory) => void;
}

export default function EventModal({
    isOpen,
    onClose,
    onSave,
    events,
    editingEvent,
    categories,
    onAddCategory,
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
    const [mCategoryId, setMCategoryId] = useState<string>("");

    const [isAddingCategory, setIsAddingCategory] = useState(false);
    const [newCatName, setNewCatName] = useState("");
    const [newCatColor, setNewCatColor] = useState("#007aff");

    const [mIsRecurring, setMIsRecurring] = useState(false);
    const [mRecurEndDate, setMRecurEndDate] = useState<string>(realTodayKey);
    const [mRecurDays, setMRecurDays] = useState<number[]>([]);

    const isTodaySelected = mDate === realTodayKey;

    // Reset form on open
    useEffect(() => {
        if (isOpen) {
            const t = setTimeout(() => {
                if (editingEvent) {
                    const { event, dateKey } = editingEvent;
                    setModalKind(event.kind);
                    setMTitle(event.title);
                    setMDate(dateKey);
                    setMAllDay(event.allDay ?? false);
                    setMLocation(event.location || "");
                    setMNotes(event.notes || "");
                    const catId = event.categoryId || categories.find(c => c.color === event.color)?.id || categories[0]?.id || "";
                    setMCategoryId(catId);
                    setMIsRecurring(event.isRecurring || false);
                    setMRecurEndDate(event.recurEndDate || dateKey);
                    setMRecurDays(event.recurDays || []);
                    if (event.allDay) {
                        setMStart("09:00");
                        setMEnd("09:00");
                    } else {
                        const sH = Math.floor((event.startMin || 0) / 60).toString().padStart(2, '0');
                        const sM = ((event.startMin || 0) % 60).toString().padStart(2, '0');
                        setMStart(`${sH}:${sM}`);

                        const eH = Math.floor((event.endMin || 0) / 60).toString().padStart(2, '0');
                        const eM = ((event.endMin || 0) % 60).toString().padStart(2, '0');
                        setMEnd(`${eH}:${eM}`);
                    }
                } else {
                    setModalKind("event");
                    setMTitle("");
                    setMDate(realTodayKey);
                    setMStart("09:00");
                    setMEnd("09:00");
                    setMAllDay(false);
                    setMLocation("");
                    setMNotes("");
                    setMCategoryId(categories[0]?.id || "");
                    setIsAddingCategory(false);
                    setNewCatName("");
                    setMIsRecurring(false);
                    setMRecurEndDate(realTodayKey);
                    setMRecurDays([]);
                }
            }, 0);
            return () => clearTimeout(t);
        }
    }, [isOpen, realTodayKey, editingEvent, categories]);

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
        if (editingEvent && ex.id === editingEvent.event.id) return false;
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

        if (mIsRecurring) {
            if (mRecurEndDate < mDate) {
                alert("Recurring end date cannot be before start date.");
                return;
            }
            if (mRecurDays.length === 0) {
                alert("Please select at least one day of the week for the recurring event.");
                return;
            }
        }

        const selectedCat = categories.find(c => c.id === mCategoryId);

        const newItem: Ev = {
            id: Date.now(),
            kind: modalKind,
            allDay: mAllDay,
            startMin: startMinVal,
            endMin: endMinVal,
            title,
            categoryId: mCategoryId,
            color: selectedCat ? selectedCat.color : (editingEvent ? editingEvent.event.color : RAINBOW[1]),
            location: mLocation.trim(),
            notes: mNotes.trim(),
            ...(mIsRecurring ? {
                isRecurring: true,
                recurEndDate: mRecurEndDate,
                recurDays: mRecurDays,
            } : {})
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

                                <div className="form-check form-switch mt-3 d-flex align-items-center gap-2 px-0">
                                    <input
                                        className="form-check-input m-0 ms-1"
                                        type="checkbox"
                                        id="mIsRecurring"
                                        style={{ transform: "scale(1.2)", cursor: editingEvent ? "not-allowed" : "pointer" }}
                                        checked={mIsRecurring}
                                        disabled={!!editingEvent}
                                        onChange={(e) => setMIsRecurring(e.target.checked)}
                                    />
                                    <label className="form-check-label small fw-bold" htmlFor="mIsRecurring" style={{ cursor: "pointer" }}>
                                        Recurring Event
                                    </label>
                                </div>

                                {mIsRecurring && (
                                    <div className="mt-3 p-3 bg-white rounded-3 border border-light-subtle d-flex flex-column gap-3 shadow-sm">
                                        <div>
                                            <label className="form-label small fw-bold text-secondary mb-1">Ends On</label>
                                            <input
                                                className="form-control form-control-sm border-0 bg-secondary bg-opacity-10 text-dark fw-bold rounded-2 px-3 py-2 w-auto"
                                                type="date"
                                                value={mRecurEndDate}
                                                disabled={!!editingEvent}
                                                onChange={(e) => setMRecurEndDate(e.target.value)}
                                                min={mDate}
                                            />
                                        </div>

                                        <div>
                                            <label className="form-label small fw-bold text-secondary mb-2">Repeats On</label>
                                            <div className="d-flex gap-2 flex-wrap">
                                                {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day, idx) => {
                                                    const isSelected = mRecurDays.includes(idx);
                                                    return (
                                                        <button
                                                            key={day}
                                                            type="button"
                                                            disabled={!!editingEvent}
                                                            className={`btn btn-sm rounded-circle fw-bold transition-all ${isSelected ? 'btn-primary shadow-sm text-white' : 'btn-light border border-light-subtle text-secondary'}`}
                                                            style={{ width: 36, height: 36, padding: 0 }}
                                                            onClick={() => {
                                                                if (isSelected) {
                                                                    setMRecurDays(mRecurDays.filter(d => d !== idx));
                                                                } else {
                                                                    setMRecurDays([...mRecurDays, idx]);
                                                                }
                                                            }}
                                                        >
                                                            {day[0]}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    </div>
                                )}
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
                                <div className="d-flex align-items-center gap-3 flex-wrap w-100">
                                    <span className="small fw-bold text-secondary">Category</span>
                                    <div className="d-flex gap-2 flex-wrap align-items-center w-100">
                                        {categories.map((c) => (
                                            <button
                                                key={c.id}
                                                type="button"
                                                className={`btn btn-sm rounded-pill d-flex align-items-center gap-2 transition-all ${mCategoryId === c.id
                                                    ? "shadow-sm border-0"
                                                    : "opacity-75 hover-opacity-100 border bg-light text-secondary"
                                                    }`}
                                                style={{
                                                    fontSize: 12,
                                                    fontWeight: 600,
                                                    backgroundColor: mCategoryId === c.id ? `${c.color}20` : undefined,
                                                    color: mCategoryId === c.id ? c.color : undefined,
                                                    border: mCategoryId === c.id ? `1px solid ${c.color}` : undefined
                                                }}
                                                onClick={() => setMCategoryId(c.id)}
                                                title={c.name}
                                            >
                                                <div
                                                    className="rounded-circle shadow-sm"
                                                    style={{
                                                        width: 12,
                                                        height: 12,
                                                        backgroundColor: c.color,
                                                    }}
                                                />
                                                {c.name}
                                            </button>
                                        ))}
                                        <button
                                            type="button"
                                            className="btn btn-sm btn-light rounded-pill border fw-bold text-secondary text-nowrap"
                                            onClick={() => setIsAddingCategory(!isAddingCategory)}
                                        >
                                            + New Category
                                        </button>
                                    </div>

                                    {isAddingCategory && (
                                        <div className="w-100 mt-2 p-3 bg-secondary bg-opacity-10 rounded-3 border shadow-sm">
                                            <div className="d-flex flex-column gap-2">
                                                <label className="small fw-bold text-dark">Create Custom Category</label>
                                                <div className="d-flex gap-2 align-items-center">
                                                    <input
                                                        type="text"
                                                        className="form-control form-control-sm border-0"
                                                        placeholder="Category Name"
                                                        value={newCatName}
                                                        onChange={(e) => setNewCatName(e.target.value)}
                                                    />
                                                    <input
                                                        type="color"
                                                        className="form-control form-control-sm form-control-color border-0 p-1"
                                                        value={newCatColor}
                                                        onChange={(e) => setNewCatColor(e.target.value)}
                                                        title="Choose your color"
                                                        style={{ width: 40, cursor: 'pointer' }}
                                                    />
                                                    <button
                                                        type="button"
                                                        className="btn btn-sm btn-dark fw-bold rounded-pill px-3"
                                                        disabled={!newCatName.trim()}
                                                        onClick={() => {
                                                            const newCat = {
                                                                id: `cat-${Date.now()}`,
                                                                name: newCatName.trim(),
                                                                color: newCatColor
                                                            };
                                                            onAddCategory(newCat);
                                                            setMCategoryId(newCat.id);
                                                            setIsAddingCategory(false);
                                                            setNewCatName("");
                                                        }}
                                                    >
                                                        Add
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
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
