import React, { useState, useEffect } from "react";
import { NotificationSettings, NotificationTimePreference } from "../../types";
import { NOTIFICATION_TIME_OPTIONS, minutesToLabel } from "../../services/settings.api";
import { InvitationResponse, AcceptInvitationResult, ConflictReport } from "../../services/collaborators.api";
import { EventUpdateRequest } from "../../services/events.api";

interface NotificationModalProps {
    isOpen: boolean;
    onClose: () => void;
    settings: NotificationSettings;
    onUpdateSettings: (settings: NotificationSettings) => void;
    userEmail: string;
    onEmailClick: () => void;
    invitations: InvitationResponse[];
    onAcceptInvitation: (id: string) => Promise<void>;
    onDeclineInvitation: (id: string) => Promise<void>;
    conflictResult: AcceptInvitationResult | null;
    onForceAccept: (invitationId: string) => Promise<void>;
    onReportConflict: (invitationId: string, message?: string) => Promise<void>;
    onDismissConflict: () => void;
    conflictReportedMessage: string | null;
    receivedConflictReports: ConflictReport[];
    onDismissConflictReport: (invitationId: string) => void;
    onUpdateEventTime: (eventId: string, update: EventUpdateRequest) => Promise<boolean>;
}


export default function NotificationModal({
    isOpen,
    onClose,
    settings,
    onUpdateSettings,
    userEmail,
    onEmailClick,
    invitations,
    onAcceptInvitation,
    onDeclineInvitation,
    conflictResult,
    onForceAccept,
    onReportConflict,
    onDismissConflict,
    conflictReportedMessage,
    receivedConflictReports,
    onDismissConflictReport,
    onUpdateEventTime,
}: NotificationModalProps) {
    const [showTimePicker, setShowTimePicker] = useState(false);
    const [activeTab, setActiveTab] = useState<'invites' | 'settings'>('invites');
    // Conflict resolution: edit mode state
    const [editMode, setEditMode] = useState(false);
    const [editingEventId, setEditingEventId] = useState<string | null>(null);
    const [editStart, setEditStart] = useState("");
    const [editEnd, setEditEnd] = useState("");
    const [editSaving, setEditSaving] = useState(false);
    const [editError, setEditError] = useState<string | null>(null);
    const [resolvedEventIds, setResolvedEventIds] = useState<Set<string>>(new Set());

    // Reset edit state when conflict result changes
    useEffect(() => {
        if (!conflictResult) {
            setEditMode(false);
            setEditingEventId(null);
            setEditStart("");
            setEditEnd("");
            setEditError(null);
            setResolvedEventIds(new Set());
        }
    }, [conflictResult]);

    // Helper to format Date as datetime-local input value
    const toLocalDatetimeString = (dt: Date) => {
        const pad = (n: number) => n.toString().padStart(2, "0");
        return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
    };

    if (!isOpen) return null;

    const BellIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" className="bi bi-bell" viewBox="0 0 16 16">
            <path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2M8 1.918l-.797.161A4 4 0 0 0 4 6c0 .628-.134 2.197-.459 3.742-.16.767-.376 1.566-.663 2.258h10.244c-.287-.692-.502-1.49-.663-2.258C12.134 8.197 12 6.628 12 6a4 4 0 0 0-3.203-3.92zM14.22 12c.223.447.481.801.78 1H1c.299-.199.557-.553.78-1C2.68 10.2 3 6.88 3 6c0-2.42 1.72-4.44 4.005-4.901a1 1 0 1 1 1.99 0A5 5 0 0 1 13 6c0 .88.32 4.2 1.22 6" />
        </svg>
    );

    const BellSlashIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" className="bi bi-bell-slash" viewBox="0 0 16 16">
            <path d="M5.164 14H15c-.299-.199-.557-.553-.78-1-.9-1.8-1.22-5.12-1.22-6q0-.396-.06-.776l-.938.938c.02.708.157 2.154.457 3.58.161.767.377 1.566.663 2.258H6.164zm5.581-9.91a4 4 0 0 0-1.948-1.01L8 2.917l-.797.161A4 4 0 0 0 4 7c0 .628-.134 2.197-.459 3.742q-.075.358-.166.718l-1.653 1.653q.03-.055.059-.113C2.679 11.2 3 7.88 3 7c0-2.42 1.72-4.44 4.005-4.901a1 1 0 1 1 1.99 0c.942.19 1.788.645 2.457 1.284zM10 15a2 2 0 1 1-4 0zm-9.375.625a.53.53 0 0 0 .75.75l14.75-14.75a.53.53 0 0 0-.75-.75z" />
        </svg>
    );

    const ClockIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71z"/>
            <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0"/>
        </svg>
    );

    const PlusIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4"/>
        </svg>
    );

    const TrashIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
            <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>
            <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>
        </svg>
    );

    const handleAddNotificationTime = (minutes: number) => {
        const notificationTimes = settings.notificationTimes || [];
        
        // Check if already exists
        if (notificationTimes.some(t => t.minutes_before === minutes)) {
            return;
        }
        
        // Max 2 notification times
        if (notificationTimes.length >= 2) {
            return;
        }
        
        const newTime: NotificationTimePreference = {
            minutes_before: minutes,
            label: minutesToLabel(minutes)
        };
        
        onUpdateSettings({
            ...settings,
            notificationTimes: [...notificationTimes, newTime]
        });
        setShowTimePicker(false);
    };

    const handleRemoveNotificationTime = (minutes: number) => {
        const notificationTimes = settings.notificationTimes || [];
        onUpdateSettings({
            ...settings,
            notificationTimes: notificationTimes.filter(t => t.minutes_before !== minutes)
        });
    };

    const notificationTimes = settings.notificationTimes || [];
    const canAddMore = notificationTimes.length < 2;

    return (
        <div
            className="position-fixed inset-0 z-3 p-4 d-flex align-items-center justify-content-center"
            style={{
                backgroundColor: "rgba(0,0,0,.6)",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backdropFilter: "blur(4px)",
            }}
            onClick={onClose}
        >
            <div
                className="bg-dark bg-opacity-75 text-white rounded-4 shadow-lg border border-secondary position-relative d-flex flex-column"
                style={{
                    width: "min(500px, 94vw)",
                    maxHeight: "85vh",
                    backdropFilter: "blur(12px)",
                }}
                onClick={(e) => e.stopPropagation()}
            >

                {/* Header with Tabs */}
                <div className="d-flex align-items-center justify-content-between p-4 border-bottom border-secondary border-opacity-25">
                    <div className="d-flex align-items-center gap-2">
                        <div className="p-2 bg-primary bg-opacity-25 rounded-3 text-primary">
                            <BellIcon />
                        </div>
                        <div className="fw-bold text-uppercase letter-spacing-1">
                            Notifications
                        </div>
                    </div>
                    <button
                        type="button"
                        className="btn btn-sm btn-outline-light rounded-circle border-0 hover-bg-light hover-text-dark"
                        onClick={onClose}
                        style={{ width: 32, height: 32 }}
                    >
                        ×
                    </button>
                </div>
                {/* Tabs - Modern pill style */}
                <div className="d-flex justify-content-center align-items-center py-3 bg-dark position-relative" style={{zIndex:2}}>
                    <div className="bg-secondary bg-opacity-10 rounded-pill shadow-sm d-flex p-1" style={{gap: 4, minWidth: 320, maxWidth: 400}}>
                        <button
                            className={`btn btn-sm d-flex align-items-center gap-2 px-4 py-2 fw-bold rounded-pill transition-all ${activeTab === 'invites' ? 'bg-primary text-white shadow' : 'bg-transparent text-secondary'}`}
                            style={{fontSize: 15, border: 'none'}}
                            onClick={() => setActiveTab('invites')}
                        >
                            <svg width="18" height="18" fill="currentColor" className="bi bi-people" viewBox="0 0 16 16"><path d="M13 7a2 2 0 1 0-4 0 2 2 0 0 0 4 0zM6 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm7 8a3 3 0 0 0-2.824-2H5.824A3 3 0 0 0 3 16h10zm-9.995-.15A2.01 2.01 0 0 1 5.824 14h4.352a2.01 2.01 0 0 1 2.819 1.85H3.005z"/></svg>
                            Invitations
                        </button>
                        <button
                            className={`btn btn-sm d-flex align-items-center gap-2 px-4 py-2 fw-bold rounded-pill transition-all ${activeTab === 'settings' ? 'bg-primary text-white shadow' : 'bg-transparent text-secondary'}`}
                            style={{fontSize: 15, border: 'none'}}
                            onClick={() => setActiveTab('settings')}
                        >
                            <svg width="18" height="18" fill="currentColor" className="bi bi-gear" viewBox="0 0 16 16"><path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/><path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.901-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319zm-2.633.283c.246-.835 1.428-.835 1.674 0l.094.319a1.873 1.873 0 0 0 2.693 1.115l.291-.16c.764-.415 1.6.42 1.184 1.185l-.159.292a1.873 1.873 0 0 0 1.116 2.692l.318.094c.835.246.835 1.428 0 1.674l-.319.094a1.873 1.873 0 0 0-1.115 2.693l.16.291c.415.764-.42 1.6-1.185 1.184l-.291-.159a1.873 1.873 0 0 0-2.693 1.116l-.094.318c-.246.835-1.428.835-1.674 0l-.094-.319a1.873 1.873 0 0 0-2.692-1.115l-.292.16c-.764.415-1.6-.42-1.184-1.185l.159-.291A1.873 1.873 0 0 0 1.945 8.93l-.319-.094c-.835-.246-.835-1.428 0-1.674l.319-.094A1.873 1.873 0 0 0 3.06 4.377l-.16-.292c-.415-.764.42-1.6 1.185-1.184l.291.159a1.873 1.873 0 0 0 2.693-1.115l.094-.319z"/></svg>
                            Settings
                        </button>
                    </div>
                </div>


                {/* Content: Tabs */}
                <div className="p-4 d-flex flex-column gap-4" style={{background: 'rgba(255,255,255,0.03)', borderRadius: 24, boxShadow: '0 2px 16px 0 rgba(0,0,0,0.10)', overflowY: 'auto', flex: 1, minHeight: 0}}>
                    {activeTab === 'invites' && (
                        <div className="mb-2">
                            <div className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ fontSize: 18 }}>
                                <svg width="20" height="20" fill="currentColor" className="bi bi-people" viewBox="0 0 16 16"><path d="M13 7a2 2 0 1 0-4 0 2 2 0 0 0 4 0zM6 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm7 8a3 3 0 0 0-2.824-2H5.824A3 3 0 0 0 3 16h10zm-9.995-.15A2.01 2.01 0 0 1 5.824 14h4.352a2.01 2.01 0 0 1 2.819 1.85H3.005z"/></svg>
                                Invitations
                            </div>

                            {/* Conflict Reported Success Message (for invitee) */}
                            {conflictReportedMessage && (
                                <div className="alert alert-info rounded-4 small mb-3 d-flex align-items-center gap-2" style={{ backgroundColor: "rgba(13, 202, 240, 0.15)", border: "1px solid rgba(13, 202, 240, 0.3)", color: "#0dcaf0" }}>
                                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.399l-.254.001-.082-.381 2.01-.499zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2"/></svg>
                                    {conflictReportedMessage}
                                </div>
                            )}

                            {/* Conflict Reports received (for event creator) */}
                            {receivedConflictReports.length > 0 && (
                                <div className="mb-3">
                                    {receivedConflictReports.map((report) => (
                                        <div key={report.invitation_id} className="rounded-4 shadow-sm p-3 mb-2 border" style={{ backgroundColor: "rgba(220, 53, 69, 0.1)", borderColor: "rgba(220, 53, 69, 0.3)" }}>
                                            <div className="d-flex align-items-center gap-2 mb-2">
                                                <svg width="18" height="18" fill="#dc3545" viewBox="0 0 16 16">
                                                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                                                </svg>
                                                <span className="fw-bold small" style={{ color: "#dc3545" }}>Conflict Report</span>
                                            </div>
                                            <div className="small text-white mb-1">
                                                <span className="fw-semibold">{report.reporter_username}</span> reported a conflict for <span className="fw-semibold">&ldquo;{report.event_title}&rdquo;</span>
                                            </div>
                                            <div className="small text-secondary mb-2">{report.message}</div>
                                            <div className="small text-white-50 mb-2">
                                                Please create a new event at a different time.
                                            </div>
                                            <button
                                                className="btn btn-sm btn-outline-secondary rounded-pill px-3"
                                                onClick={() => onDismissConflictReport(report.invitation_id)}
                                            >
                                                Dismiss
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Conflict Resolution Dialog */}
                            {conflictResult && conflictResult.status === "conflict" && conflictResult.invitation_id && (
                                <div className="rounded-4 shadow p-4 mb-3 border" style={{ backgroundColor: "rgba(255, 193, 7, 0.1)", borderColor: "rgba(255, 193, 7, 0.4)" }}>
                                    <div className="fw-bold mb-2 d-flex align-items-center gap-2" style={{ color: "#ffc107", fontSize: 16 }}>
                                        <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
                                            <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                                        </svg>
                                        Schedule Conflict Detected
                                    </div>
                                    <div className="small text-secondary mb-2">
                                        {conflictResult.message}
                                    </div>
                                    <div className="small mb-2">
                                        <span className="text-white-50">Collaboration event: </span>
                                        <span className="fw-semibold text-white">{conflictResult.collab_event_title}</span>
                                        <div className="text-secondary">
                                            {conflictResult.collab_event_start && new Date(conflictResult.collab_event_start).toLocaleString()} 
                                            {" – "}
                                            {conflictResult.collab_event_end && new Date(conflictResult.collab_event_end).toLocaleTimeString()}
                                        </div>
                                    </div>

                                    {!editMode ? (
                                        <>
                                            <div className="small mb-3">
                                                <span className="text-white-50">Your conflicting events:</span>
                                                {conflictResult.conflicts.map((c) => (
                                                    <div key={c.event_id} className="ms-2 mt-1 p-2 rounded-3" style={{ backgroundColor: "rgba(255, 255, 255, 0.05)" }}>
                                                        <span className="fw-semibold text-white">{c.title}</span>
                                                        <div className="text-secondary" style={{ fontSize: 12 }}>
                                                            {new Date(c.start_time).toLocaleString()} – {new Date(c.end_time).toLocaleTimeString()}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                            <div className="small text-white-50 mb-3">
                                                Choose how to resolve this conflict:
                                            </div>
                                            <div className="d-flex flex-column gap-2">
                                                <button 
                                                    className="btn btn-warning rounded-pill px-4 fw-bold shadow-sm text-dark"
                                                    onClick={() => setEditMode(true)}
                                                >
                                                    Reschedule My Event &amp; Accept
                                                </button>
                                                <button 
                                                    className="btn btn-outline-light rounded-pill px-4 fw-bold border shadow-sm"
                                                    onClick={() => onReportConflict(conflictResult.invitation_id!)}
                                                >
                                                    Report Conflict to Creator
                                                </button>
                                                <button 
                                                    className="btn btn-link text-secondary small p-0 mt-1"
                                                    onClick={onDismissConflict}
                                                >
                                                    Cancel
                                                </button>
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            {/* Edit mode: reschedule conflicting events */}
                                            <div className="small text-white-50 mb-2">
                                                Click a conflicting event to change its time, then accept the collaboration:
                                            </div>
                                            <div className="d-flex flex-column gap-2 mb-3">
                                                {conflictResult.conflicts.map((c) => {
                                                    const isEditing = editingEventId === c.event_id;
                                                    const isResolved = resolvedEventIds.has(c.event_id);

                                                    return (
                                                        <div key={c.event_id} className="rounded-3 border overflow-hidden" style={{ backgroundColor: isResolved ? "rgba(25, 135, 84, 0.1)" : "rgba(255, 255, 255, 0.05)", borderColor: isResolved ? "rgba(25, 135, 84, 0.4)" : "rgba(255, 255, 255, 0.1)" }}>
                                                            <div
                                                                className="p-2 d-flex align-items-center justify-content-between"
                                                                style={{ cursor: isResolved ? "default" : "pointer" }}
                                                                onClick={() => {
                                                                    if (isResolved) return;
                                                                    if (isEditing) {
                                                                        setEditingEventId(null);
                                                                    } else {
                                                                        setEditingEventId(c.event_id);
                                                                        // Pre-fill with current times
                                                                        const startDt = new Date(c.start_time);
                                                                        const endDt = new Date(c.end_time);
                                                                        setEditStart(toLocalDatetimeString(startDt));
                                                                        setEditEnd(toLocalDatetimeString(endDt));
                                                                        setEditError(null);
                                                                    }
                                                                }}
                                                            >
                                                                <div>
                                                                    <span className="fw-semibold text-white small">{c.title}</span>
                                                                    <div className="text-secondary" style={{ fontSize: 11 }}>
                                                                        {new Date(c.start_time).toLocaleString()} – {new Date(c.end_time).toLocaleTimeString()}
                                                                    </div>
                                                                </div>
                                                                {isResolved ? (
                                                                    <span className="badge bg-success bg-opacity-25 text-success small">✓ Rescheduled</span>
                                                                ) : (
                                                                    <span className="badge bg-warning bg-opacity-25 text-warning small" style={{ cursor: "pointer" }}>
                                                                        {isEditing ? "▾" : "Edit Time"}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            {isEditing && !isResolved && (
                                                                <div className="p-2 border-top" style={{ borderColor: "rgba(255,255,255,0.1)", backgroundColor: "rgba(0,0,0,0.15)" }}>
                                                                    <div className="d-flex flex-column gap-2 mb-2">
                                                                        <div>
                                                                            <label className="form-label text-white-50 mb-1" style={{ fontSize: 11 }}>New Start</label>
                                                                            <input
                                                                                type="datetime-local"
                                                                                className="form-control form-control-sm bg-dark text-white border-secondary"
                                                                                value={editStart}
                                                                                onChange={(e) => setEditStart(e.target.value)}
                                                                            />
                                                                        </div>
                                                                        <div>
                                                                            <label className="form-label text-white-50 mb-1" style={{ fontSize: 11 }}>New End</label>
                                                                            <input
                                                                                type="datetime-local"
                                                                                className="form-control form-control-sm bg-dark text-white border-secondary"
                                                                                value={editEnd}
                                                                                onChange={(e) => setEditEnd(e.target.value)}
                                                                            />
                                                                        </div>
                                                                    </div>
                                                                    {editError && (
                                                                        <div className="small mb-2 p-2 rounded-3 d-flex align-items-center gap-2" style={{ backgroundColor: "rgba(220, 53, 69, 0.15)", border: "1px solid rgba(220, 53, 69, 0.4)", color: "#ff6b6b" }}>
                                                                            <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16" className="flex-shrink-0">
                                                                                <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                                                                            </svg>
                                                                            <span>{editError}</span>
                                                                        </div>
                                                                    )}
                                                                    <div className="d-flex gap-2">
                                                                        <button
                                                                            className="btn btn-sm btn-primary rounded-pill px-3 fw-bold"
                                                                            disabled={editSaving || !editStart || !editEnd}
                                                                            onClick={async (e) => {
                                                                                e.stopPropagation();
                                                                                if (!editStart || !editEnd) return;
                                                                                setEditSaving(true);
                                                                                setEditError(null);
                                                                                try {
                                                                                    const success = await onUpdateEventTime(c.event_id, {
                                                                                        start_time: new Date(editStart).toISOString(),
                                                                                        end_time: new Date(editEnd).toISOString(),
                                                                                    });
                                                                                    if (success) {
                                                                                        setResolvedEventIds(prev => new Set([...prev, c.event_id]));
                                                                                        setEditingEventId(null);
                                                                                    } else {
                                                                                        setEditError("Failed to update event time");
                                                                                    }
                                                                                } catch (err) {
                                                                                    setEditError(err instanceof Error ? err.message : "Failed to update");
                                                                                } finally {
                                                                                    setEditSaving(false);
                                                                                }
                                                                            }}
                                                                        >
                                                                            {editSaving ? "Saving..." : "Save"}
                                                                        </button>
                                                                        <button
                                                                            className="btn btn-sm btn-outline-secondary rounded-pill px-3"
                                                                            onClick={(e) => {
                                                                                e.stopPropagation();
                                                                                setEditingEventId(null);
                                                                                setEditError(null);
                                                                            }}
                                                                        >
                                                                            Cancel
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                            {/* Accept button — enabled only after ALL conflicting events are rescheduled */}
                                            <div className="d-flex flex-column gap-2">
                                                {(() => {
                                                    const allResolved = conflictResult.conflicts.every(c => resolvedEventIds.has(c.event_id));
                                                    const someResolved = resolvedEventIds.size > 0;
                                                    return (
                                                        <>
                                                            {someResolved && !allResolved && (
                                                                <div className="small p-2 rounded-3 d-flex align-items-center gap-2" style={{ backgroundColor: "rgba(220, 53, 69, 0.12)", border: "1px solid rgba(220, 53, 69, 0.3)", color: "#ff6b6b" }}>
                                                                    <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16" className="flex-shrink-0">
                                                                        <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                                                                    </svg>
                                                                    <span>All conflicting events must be rescheduled before accepting.</span>
                                                                </div>
                                                            )}
                                                            <button
                                                                className="btn btn-success rounded-pill px-4 fw-bold shadow-sm"
                                                                disabled={!allResolved}
                                                                onClick={() => onForceAccept(conflictResult.invitation_id!)}
                                                            >
                                                                {allResolved
                                                                    ? "✓ Accept Collaboration Event"
                                                                    : `Reschedule all conflicts first (${resolvedEventIds.size}/${conflictResult.conflicts.length})`}
                                                            </button>
                                                        </>
                                                    );
                                                })()}
                                                <button 
                                                    className="btn btn-link text-secondary small p-0 mt-1"
                                                    onClick={() => setEditMode(false)}
                                                >
                                                    ← Back
                                                </button>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            {invitations.length === 0 && !conflictResult && receivedConflictReports.length === 0 ? (
                                <div className="small text-secondary text-center py-4">No new invitations</div>
                            ) : (
                                <div className="d-flex flex-column gap-3 mb-2">
                                    {invitations.map((invite) => (
                                        <div key={invite.id} className="rounded-4 shadow-sm p-3 bg-white bg-opacity-10 border border-secondary border-opacity-25 d-flex flex-column gap-2 position-relative">
                                            <div className="fw-bold text-white fs-5">{invite.event_title}</div>
                                            <div className="small text-secondary">Invited by <span className="fw-semibold">{invite.inviter_username}</span> for <span className="fw-semibold">{new Date(invite.event_date).toLocaleString()}</span></div>
                                            <div className="d-flex gap-2 mt-1">
                                                <button className="btn btn-primary rounded-pill px-4 fw-bold shadow-sm" style={{minWidth: 90}} onClick={() => onAcceptInvitation(invite.id)}>Accept</button>
                                                <button className="btn btn-outline-light rounded-pill px-4 fw-bold border shadow-sm" style={{minWidth: 90}} onClick={() => onDeclineInvitation(invite.id)}>Decline</button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                    {activeTab === 'settings' && (
                        <>
                        {/* Window Notifications Toggle */}
                        <div className="d-flex align-items-center justify-content-between p-3 rounded-4 transition-all shadow-sm" style={{ backgroundColor: "rgba(255, 255, 255, 0.10)" }}>
                            <div className="d-flex align-items-center gap-3">
                                <div className={`p-2 rounded-3 ${settings.windowEnabled ? 'text-info bg-info bg-opacity-25' : 'text-white-50 bg-secondary bg-opacity-25'}`}>
                                    {settings.windowEnabled ? <BellIcon /> : <BellSlashIcon />}
                                </div>
                                <div>
                                    <div className="fw-semibold">Window Notifications</div>
                                    <div className="small text-white-50">Browser push notifications</div>
                                </div>
                            </div>
                            <div className="form-check form-switch m-0">
                                <input
                                    className="form-check-input shadow-none cursor-pointer"
                                    type="checkbox"
                                    role="switch"
                                    style={{ width: "3em", height: "1.5rem" }}
                                    checked={settings.windowEnabled ?? true}
                                    onChange={(e) => onUpdateSettings({ ...settings, windowEnabled: e.target.checked })}
                                />
                            </div>
                        </div>

                        {/* Email Notifications Toggle */}
                        <div className="d-flex align-items-center justify-content-between p-3 rounded-4 transition-all shadow-sm" style={{ backgroundColor: "rgba(255, 255, 255, 0.10)" }}>
                            <div className="d-flex align-items-center gap-3">
                                <div className={`p-2 rounded-3 ${settings.emailEnabled ? 'text-warning bg-warning bg-opacity-25' : 'text-white-50 bg-secondary bg-opacity-25'}`}>
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" className="bi bi-envelope" viewBox="0 0 16 16">
                                        <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 0 0-1-1zm13 2.383-4.708 2.825L15 11.105zm-.034 6.876-5.64-3.471L8 9.583l-1.326-.795-5.64 3.471A1 1 0 0 0 2 13h12a1 1 0 0 0 .966-.741ZM1 11.105l4.708-2.897L1 5.383z"/>
                                    </svg>
                                </div>
                                <div>
                                    <div className="fw-semibold">Email Notifications</div>
                                    <div className="small text-white-50">
                                        {userEmail ? (
                                            <span className="text-success">{userEmail}</span>
                                        ) : (
                                            <span 
                                                className="text-warning cursor-pointer text-decoration-underline"
                                                onClick={onEmailClick}
                                            >
                                                Click to set email
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <div className="form-check form-switch m-0">
                                <input
                                    className="form-check-input shadow-none cursor-pointer"
                                    type="checkbox"
                                    role="switch"
                                    style={{ width: "3em", height: "1.5rem" }}
                                    checked={settings.emailEnabled ?? false}
                                    onChange={(e) => onUpdateSettings({ ...settings, emailEnabled: e.target.checked })}
                                    disabled={!userEmail}
                                />
                            </div>
                        </div>

                        {/* Notification Timing Section - Only show if email enabled */}
                        {settings.emailEnabled && userEmail && (
                            <div className="p-3 rounded-4 shadow-sm" style={{ backgroundColor: "rgba(255, 255, 255, 0.07)" }}>
                                <div className="d-flex align-items-center gap-2 mb-3">
                                    <ClockIcon />
                                    <span className="fw-semibold">When to Notify</span>
                                    <span className="badge bg-secondary ms-auto">{notificationTimes.length}/2</span>
                                </div>
                                {/* Current notification times */}
                                <div className="d-flex flex-column gap-2 mb-3">
                                    {notificationTimes.length === 0 ? (
                                        <div className="text-white-50 small text-center py-2">
                                            No notification times set. Add one below.
                                        </div>
                                    ) : (
                                        notificationTimes.map((time, index) => (
                                            <div 
                                                key={time.minutes_before}
                                                className="d-flex align-items-center justify-content-between p-2 px-3 rounded-3"
                                                style={{ backgroundColor: "rgba(255, 255, 255, 0.1)" }}
                                            >
                                                <div className="d-flex align-items-center gap-2">
                                                    <span className="badge bg-primary">{index + 1}</span>
                                                    <span>{time.label || minutesToLabel(time.minutes_before)}</span>
                                                </div>
                                                <button
                                                    type="button"
                                                    className="btn btn-sm btn-outline-danger border-0 rounded-circle p-1"
                                                    onClick={() => handleRemoveNotificationTime(time.minutes_before)}
                                                    title="Remove"
                                                >
                                                    <TrashIcon />
                                                </button>
                                            </div>
                                        ))
                                    )}
                                </div>
                                {/* Add notification time */}
                                {canAddMore && (
                                    <>
                                        {!showTimePicker ? (
                                            <button
                                                type="button"
                                                className="btn btn-outline-primary w-100 d-flex align-items-center justify-content-center gap-2 rounded-3"
                                                onClick={() => setShowTimePicker(true)}
                                            >
                                                <PlusIcon /> Add Notification Time
                                            </button>
                                        ) : (
                                            <div className="d-flex flex-column gap-2">
                                                <div className="small text-white-50 mb-1">Select when to notify:</div>
                                                <div className="d-flex flex-wrap gap-2">
                                                    {NOTIFICATION_TIME_OPTIONS
                                                        .filter(opt => !notificationTimes.some(t => t.minutes_before === opt.value))
                                                        .map(opt => (
                                                            <button
                                                                key={opt.value}
                                                                type="button"
                                                                className="btn btn-sm btn-outline-light rounded-pill"
                                                                onClick={() => handleAddNotificationTime(opt.value)}
                                                            >
                                                                {opt.label}
                                                            </button>
                                                        ))
                                                    }
                                                </div>
                                                <button
                                                    type="button"
                                                    className="btn btn-sm btn-link text-white-50 mt-1"
                                                    onClick={() => setShowTimePicker(false)}
                                                >
                                                    Cancel
                                                </button>
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        )}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 pt-0 mt-2">
                    <button
                        type="button"
                        className="btn btn-primary w-100 rounded-pill py-2 fw-bold shadow-sm"
                        onClick={onClose}
                        style={{ background: "#5a4ad1", borderColor: "#5a4ad1" }}
                    >
                        Done
                    </button>
                    <div className="text-center mt-3 small text-white-25">
                        Preferences are saved automatically
                    </div>
                </div>
            </div>

            <style jsx>{`
                .cursor-pointer { cursor: pointer; }
                .hover-bg-opacity-10:hover { background-color: rgba(255, 255, 255, 0.1) !important; }
                .hover-bg-light:hover { background-color: rgba(255, 255, 255, 0.1) !important; }
                .hover-text-dark:hover { color: white !important; }
                .letter-spacing-1 { letter-spacing: 1px; }
                .transition-all { transition: all 0.2s ease; }
            `}</style>
        </div>
    );
}
