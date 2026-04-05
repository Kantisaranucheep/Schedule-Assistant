import React, { useMemo, useState } from "react";
import { Ev } from "../../types";
import { parseISODate, prettyDow, prettyMonth, minutesToLabel } from "../../utils";

interface ViewEventModalProps {
    isOpen: boolean;
    onClose: () => void;
    eventData: { event: Ev; dateKey: string } | null;
    onEdit: (dateKey: string, ev: Ev) => void;
    onDelete: (dateKey: string, eventId: string | number) => void;
}

export default function ViewEventModal({
    isOpen,
    onClose,
    eventData,
    onEdit,
    onDelete,
}: ViewEventModalProps) {
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    const prettyDate = useMemo(() => {
        if (!eventData) return "";
        const dt = parseISODate(eventData.dateKey);
        return `${prettyDow(dt)}, ${dt.getDate()} ${prettyMonth(dt)}`;
    }, [eventData]);

    const timeString = useMemo(() => {
        if (!eventData) return "";
        const { event } = eventData;
        // Tasks don't have time, only show date
        if (event.kind === "task") return "";
        if (event.allDay) return "All day";
        return `${minutesToLabel(event.startMin)} – ${minutesToLabel(event.endMin)}`;
    }, [eventData]);

    if (!isOpen || !eventData) return null;

    const { event, dateKey } = eventData;

    const handleDeleteClick = () => {
        setShowDeleteConfirm(true);
    };

    const handleConfirmDelete = () => {
        setShowDeleteConfirm(false);
        onClose();
        onDelete(dateKey, event.id);
    };

    const handleCancelDelete = () => {
        setShowDeleteConfirm(false);
    };

    return (
        <div
            className={`position-fixed inset-0 z-3 p-4 d-flex align-items-center justify-content-center`}
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
                    if (showDeleteConfirm) {
                        setShowDeleteConfirm(false);
                    } else {
                        onClose();
                    }
                }
            }}
        >
            {/* Delete Confirmation Modal */}
            {showDeleteConfirm ? (
                <div
                    className="bg-white rounded-4 shadow-lg overflow-hidden position-relative"
                    style={{ width: "min(360px, 92vw)" }}
                >
                    <div className="p-4 text-center">
                        <div className="mb-3">
                            <div
                                className="d-inline-flex align-items-center justify-content-center rounded-circle bg-danger bg-opacity-10"
                                style={{ width: 56, height: 56 }}
                            >
                                <svg viewBox="0 0 24 24" width="28" height="28" stroke="#dc3545" strokeWidth="2" fill="none">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                </svg>
                            </div>
                        </div>
                        <h5 className="fw-bold mb-2">Delete {event.kind === "task" ? "Task" : "Event"}?</h5>
                        <p className="text-secondary small mb-4">
                            Are you sure you want to delete &quot;{event.title}&quot;? This action cannot be undone.
                        </p>
                        <div className="d-flex gap-2 justify-content-center">
                            <button
                                type="button"
                                className="btn btn-light rounded-pill px-4 fw-semibold"
                                onClick={handleCancelDelete}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="btn btn-danger rounded-pill px-4 fw-semibold"
                                onClick={handleConfirmDelete}
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
                <div
                    className="bg-white rounded-4 shadow-lg overflow-hidden position-relative"
                    style={{ width: "min(400px, 92vw)" }}
                >
                    {/* Actions Top Bar */}
                    <div className="d-flex justify-content-end p-2 bg-light border-bottom">
                        <button
                            type="button"
                            className="btn btn-sm text-secondary hover-text-dark border-0 p-2 lh-1"
                            onClick={() => {
                                onClose();
                                onEdit(dateKey, event);
                            }}
                            title="Edit event"
                        >
                            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M12 20h9"></path>
                                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                            </svg>
                        </button>
                        <button
                            type="button"
                            className="btn btn-sm text-secondary hover-text-danger border-0 p-2 lh-1"
                            onClick={handleDeleteClick}
                            title="Delete event"
                        >
                            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                        <button
                            type="button"
                            className="btn btn-sm text-secondary hover-text-dark border-0 p-2 lh-1 ms-2"
                            onClick={onClose}
                            title="Close"
                        >
                            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </button>
                    </div>

                    <div className="p-4">
                        <div className="d-flex gap-3 align-items-start mb-3">
                            <div
                                className="rounded-circle flex-shrink-0 mt-2"
                                style={{ width: 16, height: 16, background: event.color }}
                            />
                            <div>
                                <div className="d-flex align-items-center gap-2 mb-1">
                                    <h4 className="fw-bold mb-0">{event.title}</h4>
                                    {event.kind === "task" && (
                                        <span className="badge bg-secondary bg-opacity-25 text-dark small">Task</span>
                                    )}
                                </div>
                                <div className="text-secondary small d-flex flex-column gap-1">
                                    <div>{prettyDate}{timeString && ` • ${timeString}`}</div>
                                </div>
                            </div>
                        </div>

                        {event.location && (
                            <div className="d-flex gap-3 align-items-center mb-3">
                                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="text-secondary opacity-75">
                                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                                    <circle cx="12" cy="10" r="3"></circle>
                                </svg>
                                <div className="text-dark small">{event.location}</div>
                            </div>
                        )}

                        {event.notes && (
                            <div className="d-flex gap-3 align-items-start mb-2">
                                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="text-secondary opacity-75 mt-1">
                                    <line x1="4" y1="6" x2="20" y2="6"></line>
                                    <line x1="4" y1="12" x2="20" y2="12"></line>
                                    <line x1="4" y1="18" x2="12" y2="18"></line>
                                </svg>
                                <div className="text-dark small" style={{ whiteSpace: "pre-wrap" }}>{event.notes}</div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
