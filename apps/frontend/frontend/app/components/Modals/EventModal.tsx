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
    onAddCategory: (cat: EventCategory) => Promise<string | void | undefined>;
    onDeleteCategory: (catId: string) => Promise<void>;
}

export default function EventModal({
    isOpen,
    onClose,
    onSave,
    events,
    editingEvent,
    categories,
    onAddCategory,
    onDeleteCategory,
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

    const [showUpdateConfirm, setShowUpdateConfirm] = useState(false);
    const [pendingEvent, setPendingEvent] = useState<{ item: Ev, date: string } | null>(null);

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

    const startMinVal = mAllDay || modalKind === "task" ? 0 : timeToMinutes(mStart);
    const endMinVal = mAllDay || modalKind === "task" ? 0 : timeToMinutes(mEnd);
    const duration = endMinVal - startMinVal;

    const existingOnDay = events[mDate] || [];
    // Only check conflicts for events, not tasks
    const conflict = modalKind === "event" && !mAllDay && existingOnDay.find(ex => {
        if (editingEvent && ex.id === editingEvent.event.id) return false;
        if (ex.allDay || ex.kind === "task") return false;
        return (startMinVal < (ex.endMin ?? 0)) && (endMinVal > (ex.startMin ?? 0));
    });

    // Skip time validations for tasks
    const isDurationTooShort = modalKind === "event" && !mAllDay && duration < 5;
    const isPastTime = modalKind === "event" && !mAllDay && isTodaySelected && mStart < minStart;
    const isInvalidTime = modalKind === "event" && !mAllDay && endMinVal < startMinVal;

    const canSave = mTitle.trim() !== "" && !conflict && !isDurationTooShort && !isPastTime && !isInvalidTime;

    function buildNewItem(): Ev {
        const title = mTitle.trim();
        const selectedCat = categories.find(c => c.id === mCategoryId);

        return {
            id: Date.now(),
            kind: modalKind,
            allDay: modalKind === "task" ? true : mAllDay,
            startMin: modalKind === "task" ? 0 : startMinVal,
            endMin: modalKind === "task" ? 0 : endMinVal,
            title,
            categoryId: mCategoryId,
            color: selectedCat ? selectedCat.color : (editingEvent ? editingEvent.event.color : RAINBOW[1]),
            location: mLocation.trim(),
            notes: mNotes.trim(),
            ...(modalKind === "event" && mIsRecurring ? {
                isRecurring: true,
                recurEndDate: mRecurEndDate,
                recurDays: mRecurDays,
            } : {})
        };
    }

    function saveEvent(e: React.FormEvent) {
        e.preventDefault();
        const title = mTitle.trim();
        if (!title) return;

        if (mDate < realTodayKey) {
            alert("You cannot choose a past date.");
            return;
        }

        // Only validate time for events, not tasks
        if (modalKind === "event" && !mAllDay) {
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
                alert(`Time conflict! You cannot have multiple events at the same time (overlaps with "${conflict.title}").`);
                return;
            }
        }

        // Recurring only applies to events
        if (modalKind === "event" && mIsRecurring) {
            if (mRecurEndDate < mDate) {
                alert("Recurring end date cannot be before start date.");
                return;
            }
            if (mRecurDays.length === 0) {
                alert("Please select at least one day of the week for the recurring event.");
                return;
            }
        }

        const newItem = buildNewItem();

        // If editing, show confirmation popup
        if (editingEvent) {
            setPendingEvent({ item: newItem, date: mDate });
            setShowUpdateConfirm(true);
        } else {
            onSave(newItem, mDate);
        }
    }

    const handleConfirmUpdate = () => {
        if (pendingEvent) {
            onSave(pendingEvent.item, pendingEvent.date);
        }
        setShowUpdateConfirm(false);
        setPendingEvent(null);
    };

    const handleCancelUpdate = () => {
        setShowUpdateConfirm(false);
        setPendingEvent(null);
    };

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
                if (e.target === e.currentTarget) {
                    if (showUpdateConfirm) {
                        setShowUpdateConfirm(false);
                        setPendingEvent(null);
                    } else {
                        onClose();
                    }
                }
            }}
        >
            {/* Update Confirmation Modal */}
            {showUpdateConfirm ? (
                <div
                    className="bg-white rounded-4 shadow-lg overflow-hidden position-relative"
                    style={{ width: "min(360px, 92vw)" }}
                >
                    <div className="p-4 text-center">
                        <div className="mb-3">
                            <div
                                className="d-inline-flex align-items-center justify-content-center rounded-circle bg-primary bg-opacity-10"
                                style={{ width: 56, height: 56 }}
                            >
                                <svg viewBox="0 0 24 24" width="28" height="28" stroke="#0d6efd" strokeWidth="2" fill="none">
                                    <path d="M12 20h9"></path>
                                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                                </svg>
                            </div>
                        </div>
                        <h5 className="fw-bold mb-2">Update {modalKind === "task" ? "Task" : "Event"}?</h5>
                        <p className="text-secondary small mb-4">
                            Are you sure you want to update &quot;{mTitle.trim()}&quot;?
                        </p>
                        <div className="d-flex gap-2 justify-content-center">
                            <button
                                type="button"
                                className="btn btn-light rounded-pill px-4 fw-semibold"
                                onClick={handleCancelUpdate}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="btn btn-primary rounded-pill px-4 fw-semibold"
                                onClick={handleConfirmUpdate}
                            >
                                Update
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
                <div
                    className="bg-white rounded-4 shadow-lg border border-light-subtle overflow-hidden position-relative d-flex flex-column"
                    style={{ width: "min(720px, 92vw)", maxHeight: "90vh" }}
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
                                    } ${editingEvent ? "pe-none opacity-75" : ""}`}
                                onClick={() => !editingEvent && setModalKind("event")}
                                role="button"
                                title={editingEvent ? "Cannot change type when editing" : undefined}
                            >
                                Event
                            </div>
                            <div
                                className={`btn btn-sm fw-bold rounded-pill px-4 ${modalKind === "task"
                                    ? "btn-white shadow-sm text-dark"
                                    : "btn-light text-secondary border-0"
                                    } ${editingEvent ? "pe-none opacity-75" : ""}`}
                                onClick={() => !editingEvent && setModalKind("task")}
                                role="button"
                                title={editingEvent ? "Cannot change type when editing" : undefined}
                            >
                                Task
                            </div>
                        </div>
                    </div>

                    <div className="p-4 bg-white/50 overflow-y-auto flex-grow-1" style={{ maxHeight: "calc(90vh - 130px)" }}>
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
                                        {modalKind === "task" ? (
                                            <>
                                                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                                                <line x1="16" y1="2" x2="16" y2="6"></line>
                                                <line x1="8" y1="2" x2="8" y2="6"></line>
                                                <line x1="3" y1="10" x2="21" y2="10"></line>
                                            </>
                                        ) : (
                                            <>
                                                <circle cx="12" cy="12" r="9"></circle>
                                                <path d="M12 7v6l4 2"></path>
                                            </>
                                        )}
                                    </svg>
                                </div>

                                <div className="flex-grow-1 p-3 rounded-4 bg-light border">
                                    <div className="d-flex flex-wrap align-items-center gap-2">
                                        <span className="badge bg-secondary bg-opacity-10 text-dark fw-bold px-2 py-1">
                                            {prettyDate}
                                        </span>

                                        {modalKind === "event" && (
                                            <>
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
                                            </>
                                        )}
                                    </div>

                                    {modalKind === "event" && conflict && (
                                        <div className="mt-2 p-2 rounded-3 d-flex align-items-center gap-2 border border-danger-subtle bg-danger bg-opacity-10 text-danger" style={{ fontSize: 11 }}>
                                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" className="flex-shrink-0">
                                                <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                            <span className="fw-bold">Time conflict! Overlaps with &quot;{conflict.title}&quot;</span>
                                        </div>
                                    )}
                                    {modalKind === "event" && isDurationTooShort && (
                                        <div className="mt-2 p-2 rounded-3 d-flex align-items-center gap-2 border border-danger-subtle bg-danger bg-opacity-10 text-danger" style={{ fontSize: 11 }}>
                                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" className="flex-shrink-0">
                                                <circle cx="12" cy="12" r="10" />
                                                <line x1="12" y1="8" x2="12" y2="12" strokeLinecap="round" strokeLinejoin="round" />
                                                <line x1="12" y1="16" x2="12.01" y2="16" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                            <span className="fw-bold">Minimum duration is 5 minutes</span>
                                        </div>
                                    )}
                                    {modalKind === "event" && isPastTime && (
                                        <div className="mt-2 p-2 rounded-3 d-flex align-items-center gap-2 border border-danger-subtle bg-danger bg-opacity-10 text-danger" style={{ fontSize: 11 }}>
                                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" className="flex-shrink-0">
                                                <circle cx="12" cy="12" r="10" />
                                                <line x1="12" y1="8" x2="12" y2="12" strokeLinecap="round" strokeLinejoin="round" />
                                                <line x1="12" y1="16" x2="12.01" y2="16" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                            <span className="fw-bold">Cannot schedule in the past</span>
                                        </div>
                                    )}
                                    {modalKind === "event" && isInvalidTime && (
                                        <div className="mt-2 p-2 rounded-3 d-flex align-items-center gap-2 border border-danger-subtle bg-danger bg-opacity-10 text-danger" style={{ fontSize: 11 }}>
                                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" className="flex-shrink-0">
                                                <circle cx="12" cy="12" r="10" />
                                                <line x1="12" y1="8" x2="12" y2="12" strokeLinecap="round" strokeLinejoin="round" />
                                                <line x1="12" y1="16" x2="12.01" y2="16" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                            <span className="fw-bold">End time must be after start time</span>
                                        </div>
                                    )}

                                    <input
                                        className="form-control form-control-sm mt-2 border-0 bg-transparent px-0"
                                        type="date"
                                        value={mDate}
                                        onChange={(e) => handleDateChange(e.target.value)}
                                        min={realTodayKey}
                                    />

                                    {modalKind === "event" && (
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
                                    )}

                                    {modalKind === "event" && mIsRecurring && (
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
                                <div className="flex-grow-1 p-2 rounded-4 bg-light border" style={{ minWidth: 0, width: 610, maxWidth: 610, flexBasis: 610, overflow: "hidden" }}>
                                    <div className="d-flex flex-column gap-2 py-1 ps-2">
                                        <span className="small fw-bold text-secondary">Category</span>
                                        <div className="d-flex gap-2 flex-wrap align-items-center">
                                            {categories.map((c) => (
                                                <div
                                                    key={c.id}
                                                    className={`btn btn-sm rounded-pill d-flex align-items-center gap-2 transition-all p-0 overflow-hidden ${mCategoryId === c.id
                                                        ? "shadow-sm border-0"
                                                        : "opacity-75 hover-opacity-100 border bg-light text-secondary"
                                                        }`}
                                                    style={{
                                                        fontSize: 12,
                                                        fontWeight: 600,
                                                        backgroundColor: mCategoryId === c.id ? `${c.color}20` : undefined,
                                                        color: mCategoryId === c.id ? c.color : undefined,
                                                        border: mCategoryId === c.id ? `1px solid ${c.color}` : undefined,
                                                        height: 28
                                                    }}
                                                    title={c.name}
                                                >
                                                    <div 
                                                        className="d-flex align-items-center gap-2 ps-2 pe-1 h-100 cursor-pointer"
                                                        onClick={() => setMCategoryId(c.id)}
                                                    >
                                                        <div
                                                            className="rounded-circle shadow-sm"
                                                            style={{
                                                                width: 10,
                                                                height: 10,
                                                                backgroundColor: c.color,
                                                            }}
                                                        />
                                                        <span className="text-truncate" style={{ maxWidth: 100 }}>{c.name}</span>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        className="btn btn-link p-0 pe-2 text-decoration-none border-0 d-flex align-items-center justify-content-center h-100 hover-opacity-100 transition-all"
                                                        style={{ 
                                                            fontSize: 14, 
                                                            color: 'inherit',
                                                            opacity: 0.5,
                                                            lineHeight: 1
                                                        }}
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            onDeleteCategory(c.id);
                                                        }}
                                                        aria-label={`Delete ${c.name} category`}
                                                    >
                                                        &times;
                                                    </button>
                                                </div>
                                            ))}
                                            <button
                                                type="button"
                                                className="btn btn-sm btn-light rounded-pill border fw-bold text-secondary text-nowrap"
                                                onClick={() => setIsAddingCategory(!isAddingCategory)}
                                                style={{ fontSize: 12, height: 28 }}
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
                                                            onClick={async () => {
                                                                const newCat = {
                                                                    id: `cat-${Date.now()}`,
                                                                    name: newCatName.trim(),
                                                                    color: newCatColor
                                                                };
                                                                const resultId = await onAddCategory(newCat);
                                                                if (resultId) {
                                                                    setMCategoryId(resultId);
                                                                }
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
                                    {editingEvent ? "Update" : "Save"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
