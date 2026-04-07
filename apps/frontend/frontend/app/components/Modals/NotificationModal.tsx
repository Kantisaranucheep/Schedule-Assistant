import React, { useState, useEffect } from "react";
import { NotificationSettings, NotificationTimePreference } from "../../types";
import { NOTIFICATION_TIME_OPTIONS, minutesToLabel } from "../../services/settings.api";

interface NotificationModalProps {
    isOpen: boolean;
    onClose: () => void;
    settings: NotificationSettings;
    onUpdateSettings: (settings: NotificationSettings) => void;
    userEmail: string;
    onEmailClick: () => void;
}

export default function NotificationModal({
    isOpen,
    onClose,
    settings,
    onUpdateSettings,
    userEmail,
    onEmailClick
}: NotificationModalProps) {
    const [showTimePicker, setShowTimePicker] = useState(false);
    
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
                className="bg-dark bg-opacity-75 text-white rounded-4 shadow-lg border border-secondary overflow-hidden position-relative"
                style={{
                    width: "min(500px, 94vw)",
                    maxHeight: "90vh",
                    backdropFilter: "blur(12px)",
                    overflowY: "auto"
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="d-flex align-items-center justify-content-between p-4 border-bottom border-secondary border-opacity-25">
                    <div className="d-flex align-items-center gap-2">
                        <div className="p-2 bg-primary bg-opacity-25 rounded-3 text-primary">
                            <BellIcon />
                        </div>
                        <div className="fw-bold text-uppercase letter-spacing-1">
                            Notification Settings
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

                {/* Content */}
                <div className="p-4 d-flex flex-column gap-4">
                    {/* Window Notifications Toggle */}
                    <div className="d-flex align-items-center justify-content-between p-3 rounded-4 transition-all" style={{ backgroundColor: "rgba(255, 255, 255, 0.08)" }}>
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
                    <div className="d-flex align-items-center justify-content-between p-3 rounded-4 transition-all" style={{ backgroundColor: "rgba(255, 255, 255, 0.08)" }}>
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
                        <div className="p-3 rounded-4" style={{ backgroundColor: "rgba(255, 255, 255, 0.05)" }}>
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
