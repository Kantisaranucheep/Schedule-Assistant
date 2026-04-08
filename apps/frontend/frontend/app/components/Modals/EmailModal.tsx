import React, { useState, useEffect } from "react";
import { sendTestEmail } from "../../services/settings.api";

const DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001";

interface EmailModalProps {
    isOpen: boolean;
    onClose: () => void;
    email: string;
    onUpdateEmail: (email: string) => void;
}

export default function EmailModal({
    isOpen,
    onClose,
    email,
    onUpdateEmail
}: EmailModalProps) {
    const [localEmail, setLocalEmail] = useState(email);
    const [error, setError] = useState("");
    const [testLoading, setTestLoading] = useState(false);
    const [testMessage, setTestMessage] = useState("");

    useEffect(() => {
        if (isOpen) {
            setLocalEmail(email);
            setError("");
            setTestMessage("");
        }
    }, [isOpen, email]);

    if (!isOpen) return null;

    const handleSave = () => {
        // Simple email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (localEmail && !emailRegex.test(localEmail)) {
            setError("Please enter a valid email address");
            return;
        }

        onUpdateEmail(localEmail);
        onClose();
    };

    const handleTestEmail = async () => {
        // Validate email first
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!localEmail) {
            setError("Please enter an email address");
            return;
        }
        if (!emailRegex.test(localEmail)) {
            setError("Please enter a valid email address");
            return;
        }

        setTestLoading(true);
        setError("");
        setTestMessage("");

        try {
            const result = await sendTestEmail(DEFAULT_USER_ID);

            if (!result.success) {
                setError(result.error || "Failed to send test email");
            } else {
                setTestMessage(`✅ Test email sent successfully to ${localEmail}!`);
            }
        } catch (err) {
            setError("Failed to send test email. Please try again.");
            console.error("Test email error:", err);
        } finally {
            setTestLoading(false);
        }
    };

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
                    width: "min(400px, 94vw)",
                    height: "auto",
                    backdropFilter: "blur(12px)",
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="d-flex align-items-center justify-content-between p-3 border-bottom border-secondary border-opacity-25">
                    <div className="d-flex align-items-center gap-2">
                        <div className="fw-bold text-uppercase small letter-spacing-1 opacity-75">
                            Account Email
                        </div>
                    </div>
                    <button
                        type="button"
                        className="btn btn-sm btn-outline-light rounded-circle border-0"
                        onClick={onClose}
                        style={{ width: 28, height: 28, fontSize: 18, lineHeight: 1 }}
                    >
                        ×
                    </button>
                </div>

                {/* Content */}
                <div className="p-4 d-flex flex-column gap-3">
                    <div className="p-3 rounded-4 transition-all" style={{ backgroundColor: "rgba(255, 255, 255, 0.08)" }}>
                        <div className="d-flex align-items-center gap-2 mb-2">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" className="text-white-50" viewBox="0 0 16 16">
                                <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 0 0-1-1zm13 2.383-4.708 2.825L15 11.105zm-.034 6.876-5.64-3.471L8 9.583l-1.326-.795-5.64 3.471A1 1 0 0 0 2 13h12a1 1 0 0 0 .966-.741ZM1 11.105l4.708-2.897L1 5.383z" />
                            </svg>
                            <span className="small text-white-50 fw-bold">Email Address</span>
                        </div>
                        <input
                            type="email"
                            className="form-control bg-transparent border-0 text-white p-0 shadow-none"
                            placeholder="name@example.com"
                            autoFocus
                            value={localEmail}
                            onChange={(e) => {
                                setLocalEmail(e.target.value);
                                if (error) setError("");
                                if (testMessage) setTestMessage("");
                            }}
                            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                        />
                    </div>

                    {error && (
                        <div className="bg-danger bg-opacity-10 border border-danger rounded-3 p-3">
                            <div className="text-danger small">
                                <strong>Error:</strong><br />
                                <div style={{ fontSize: "11px", fontFamily: "monospace", marginTop: "8px", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                                    {error}
                                </div>
                            </div>
                        </div>
                    )}

                    {testMessage && (
                        <div className="text-success small px-2">
                            {testMessage}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 pt-0 d-flex gap-2">
                    <button
                        type="button"
                        className="btn btn-outline-light rounded-pill py-2 fw-bold shadow-sm flex-grow-1"
                        onClick={handleTestEmail}
                        disabled={testLoading || !localEmail}
                        style={{ opacity: testLoading ? 0.6 : 1 }}
                    >
                        {testLoading ? "Sending..." : "Test Email"}
                    </button>
                    <button
                        type="button"
                        className="btn btn-primary flex-grow-1 rounded-pill py-2 fw-bold shadow-sm"
                        onClick={handleSave}
                        style={{ background: "#5a4ad1", borderColor: "#5a4ad1" }}
                    >
                        Save Email
                    </button>
                </div>
            </div>

            <style jsx>{`
                .letter-spacing-1 { letter-spacing: 1px; }
                .transition-all { transition: all 0.2s ease; }
                input::placeholder { color: rgba(255,255,255,0.2) !important; }
            `}</style>
        </div>
    );
}
