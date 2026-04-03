import React from "react";
import { ChatSession } from "../../../types";
import {
    handleFormSubmit,
    handleInputKeyDown,
} from "./chatModalHelper";

interface ChatModalProps {
    isOpen: boolean;
    onClose: () => void;
    sessions: ChatSession[];
    activeSessionId: string | null;
    setActiveSessionId: (id: string) => void;
    activeSession: ChatSession | undefined;
    chatInput: string;
    setChatInput: (s: string) => void;
    pushUserMessage: (s: string) => void;
    newSession: () => void;
    renameSession: (id: string, title: string) => void;
    deleteSession: (id: string) => void;
    togglePinSession: (id: string) => void;
    isTyping: boolean;
    ttsEnabled: boolean;
    toggleTts: () => void;
    chatEndRef: React.RefObject<HTMLDivElement | null>;
    isRecording: boolean;
    toggleRecording: () => void;
    loading?: boolean;
}

export default function ChatModal({
    isOpen,
    onClose,
    sessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    chatInput,
    setChatInput,
    pushUserMessage,
    newSession,
    renameSession,
    deleteSession,
    togglePinSession,
    isTyping,
    ttsEnabled,
    toggleTts,
    chatEndRef,
    isRecording,
    toggleRecording,
    loading = false,
}: ChatModalProps) {
    const [editingId, setEditingId] = React.useState<string | null>(null);
    const [editTitle, setEditTitle] = React.useState("");
    const [menuOpenId, setMenuOpenId] = React.useState<string | null>(null);

    const menuRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setMenuOpenId(null);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleStartEdit = (sessionId: string, currentTitle: string) => {
        setEditingId(sessionId);
        setEditTitle(currentTitle);
        setMenuOpenId(null);
    };

    const handleSaveEdit = () => {
        if (editingId && editTitle.trim()) {
            renameSession(editingId, editTitle.trim());
        }
        setEditingId(null);
    };

    const handleKeyDownEdit = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") handleSaveEdit();
        if (e.key === "Escape") setEditingId(null);
    };

    const renderSessionItem = (s: ChatSession) => {
        const isActive = s.id === activeSessionId;
        const isEditing = editingId === s.id;
        const isMenuOpen = menuOpenId === s.id;

        if (isEditing) {
            return (
                <div key={s.id} className="px-2 py-1">
                    <input
                        autoFocus
                        className="form-control form-control-sm rounded-3 shadow-sm border-primary"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={handleSaveEdit}
                        onKeyDown={handleKeyDownEdit}
                    />
                </div>
            );
        }

        return (
            <div key={s.id} className="position-relative mb-1 group px-2">
                <div className={`d-flex align-items-center rounded-3 position-relative transition-all ${isActive ? "bg-primary bg-opacity-10" : "hover-bg-light"
                    }`}
                    style={{ height: 36 }}
                    onClick={() => setActiveSessionId(s.id)}
                >
                    {/* Pin indicator */}
                    {s.isPinned && (
                        <span className="ms-2 small" title="Pinned">📍</span>
                    )}

                    <button
                        type="button"
                        className={`flex-grow-1 text-start btn btn-sm border-0 shadow-none px-2 text-truncate ${isActive ? "fw-bold text-dark" : "text-muted"
                            }`}
                        style={{ fontSize: '0.875rem' }}
                    >
                        {s.title}
                    </button>

                    {/* Menu Trigger */}
                    <div className="position-relative" ref={isMenuOpen ? menuRef : null}>
                        <button
                            type="button"
                            className={`btn btn-sm border-0 p-0 me-1 d-flex align-items-center justify-content-center opacity-0 group-hover-opacity-100 ${isMenuOpen ? "opacity-100" : ""}`}
                            style={{ width: 24, height: 24, transition: 'opacity 0.2s' }}
                            onClick={(e) => {
                                e.stopPropagation();
                                setMenuOpenId(isMenuOpen ? null : s.id);
                            }}
                        >
                            <span style={{ fontSize: '1.2rem', lineHeight: 0, marginTop: -8 }}>...</span>
                        </button>

                        {/* Dropdown Menu */}
                        {isMenuOpen && (
                            <div
                                className="position-absolute bg-white shadow-lg border rounded-3 py-1 z-3"
                                style={{
                                    top: '100%',
                                    right: 0,
                                    width: 140,
                                    marginTop: 4
                                }}
                                onClick={(e) => e.stopPropagation()}
                            >
                                <button
                                    className="w-100 text-start btn btn-sm btn-light border-0 rounded-0 px-3 py-2 d-flex align-items-center gap-2"
                                    onClick={() => {
                                        togglePinSession(s.id);
                                        setMenuOpenId(null);
                                    }}
                                >
                                    <span>{s.isPinned ? "📍 Unpin" : "📌 Pin"}</span>
                                </button>
                                <button
                                    className="w-100 text-start btn btn-sm btn-light border-0 rounded-0 px-3 py-2 d-flex align-items-center gap-2"
                                    onClick={() => handleStartEdit(s.id, s.title)}
                                >
                                    <span>Rename</span>
                                </button>
                                <div className="border-top my-1"></div>
                                <button
                                    className="w-100 text-start btn btn-sm btn-light border-0 rounded-0 px-3 py-2 text-danger d-flex align-items-center gap-2"
                                    onClick={() => {
                                        console.log("Deleting session from UI:", s.id);
                                        deleteSession(s.id);
                                        setMenuOpenId(null);
                                    }}
                                >
                                    <span>Delete</span>
                                </button>
                            </div>
                        )}
                    </div>
                </div>
                <style jsx>{`
                    .hover-bg-light:hover {
                        background-color: rgba(0,0,0,0.05);
                    }
                    .group:hover .opacity-0 {
                        opacity: 1 !important;
                    }
                `}</style>
            </div>
        );
    };

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
        >
            <div
                className="d-flex bg-white bg-opacity-25 backdrop-blur rounded-4 shadow-lg border border-white border-opacity-25 overflow-hidden"
                style={{
                    width: "min(980px, 94vw)",
                    height: "min(560px, 86vh)",
                    backdropFilter: "blur(10px)",
                }}
            >
                {/* Left: history */}
                <aside
                    className="d-flex flex-column bg-white border-end flex-shrink-0"
                    style={{ width: 260, minWidth: 260 }}
                >
                    <div
                        className="d-flex align-items-center justify-content-between px-3 border-bottom flex-shrink-0"
                        style={{ height: 64, boxSizing: "border-box" }}
                    >
                        <div className="small fw-bold text-uppercase ls-1">Your Chats</div>
                        <button
                            className="btn btn-sm btn-outline-secondary rounded-3 py-0 px-2 fw-bold"
                            style={{ height: 28 }}
                            type="button"
                            onClick={newSession}
                        >
                            ＋
                        </button>
                    </div>

                    <div
                        className="flex-grow-1 overflow-auto p-2"
                        style={{ minHeight: 0 }}
                    >
                        {loading ? (
                            <div className="text-center text-muted py-4">
                                <div className="spinner-border spinner-border-sm me-2" role="status">
                                    <span className="visually-hidden">Loading...</span>
                                </div>
                                Loading chats...
                            </div>
                        ) : sessions.length === 0 ? (
                            <div className="text-center text-muted py-4 small">
                                No chats yet
                            </div>
                        ) : (
                            <>
                                {sessions.some(s => s.isPinned) && (
                                    <div className="small fw-bold text-muted text-uppercase mb-2 px-2 mt-2" style={{ fontSize: '10px', letterSpacing: '0.05em' }}>Pinned</div>
                                )}
                                {sessions.map((s) => {
                                    if (!s.isPinned) return null;
                                    return renderSessionItem(s);
                                })}

                                {sessions.some(s => !s.isPinned) && (
                                    <div className="small fw-bold text-muted text-uppercase mb-2 px-2 mt-3" style={{ fontSize: '10px', letterSpacing: '0.05em' }}>Recent</div>
                                )}
                                {sessions.map((s) => {
                                    if (s.isPinned) return null;
                                    return renderSessionItem(s);
                                })}
                            </>
                        )}
                    </div>

                </aside>

                {/* Center: chat */}
                <section
                    className="flex-grow-1 d-flex flex-column bg-white"
                    style={{ minWidth: 0 }}
                >
                    <div
                        className="d-flex align-items-center justify-content-between px-3 border-bottom flex-shrink-0"
                        style={{ height: 64, boxSizing: "border-box" }}
                    >
                        <div className="d-flex align-items-center gap-2">
                            <span className="fs-5">🤖</span>
                            <span className="fw-bold">Scheduler Agent</span>
                        </div>

                        <div className="d-flex gap-2">
                            <button
                                type="button"
                                className={`btn btn-sm rounded-3 shadow-sm ${ttsEnabled ? "btn-primary" : "btn-outline-secondary"}`}
                                style={{ height: 28, width: 28, padding: 0, lineHeight: 1 }}
                                onClick={toggleTts}
                                aria-label="Toggle TTS"
                            >
                                {ttsEnabled ? "🔊" : "🔇"}
                            </button>

                            <button
                                type="button"
                                className="btn btn-sm btn-outline-secondary rounded-3 shadow-sm"
                                style={{ height: 28, width: 28, padding: 0, lineHeight: 1 }}
                                onClick={onClose}
                                aria-label="Close chat"
                            >
                                ×
                            </button>
                        </div>
                    </div>

                    <div
                        className="flex-grow-1 overflow-auto p-3 d-flex flex-column gap-3"
                        style={{ minHeight: 0 }}
                    >
                        {activeSession?.messages?.length ? (
                            activeSession.messages.map((msg) => (
                                <div
                                    key={msg.id}
                                    className={`d-flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""
                                        }`}
                                >
                                    {msg.role === "agent" && <div className="fs-5">🤖</div>}
                                    <div
                                        className={`p-3 rounded-4 shadow-sm ${msg.role === "user"
                                            ? "bg-primary text-white"
                                            : "bg-light text-dark"
                                            }`}
                                        style={{ maxWidth: "70%" }}
                                        title={
                                            msg.tokens ? `Tokens: ${msg.tokens.join(" | ")}` : ""
                                        }
                                    >
                                        {msg.text}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-center text-muted mt-5">
                                No messages yet. Type something!
                            </div>
                        )}

                        {/* Typing Indicator */}
                        {isTyping && (
                            <div className="d-flex gap-2">
                                <div className="fs-5">🤖</div>
                                <div
                                    className="p-3 rounded-4 shadow-sm bg-light text-dark d-flex align-items-center"
                                    style={{ maxWidth: "70%" }}
                                >
                                    <div className="typing-dots">
                                        <span></span>
                                        <span></span>
                                        <span></span>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    <form
                        className="px-3 border-top d-flex align-items-center gap-2 bg-light flex-shrink-0"
                        style={{ height: 80, boxSizing: "border-box" }}
                        onSubmit={(e) =>
                            handleFormSubmit(
                                e,
                                chatInput,
                                activeSession,
                                pushUserMessage,
                                setChatInput,
                            )
                        }
                    >
                        <input
                            className="form-control rounded-pill shadow-sm border-secondary-subtle"
                            placeholder="Enter Message"
                            style={{ height: 44 }}
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            onKeyDown={(e) =>
                                handleInputKeyDown(e, (formEvent) =>
                                    handleFormSubmit(
                                        formEvent,
                                        chatInput,
                                        activeSession,
                                        pushUserMessage,
                                        setChatInput,
                                    ),
                                )
                            }
                        />

                        <button
                            className={`btn rounded-circle shadow-sm d-flex align-items-center justify-content-center ${isRecording ? "btn-danger" : "btn-primary"}`}
                            style={{ width: 44, height: 44 }}
                            type="button"
                            id="btn-send-mic"
                            onClick={toggleRecording}
                            aria-label="Toggle Recording"
                        >
                            {isRecording ? "⏹️" : "🎤"}
                        </button>

                        <button
                            className="btn btn-primary rounded-circle shadow-sm d-flex align-items-center justify-content-center"
                            style={{ width: 44, height: 44 }}
                            type="submit"
                            id="btn-send"
                            aria-label="Send"
                        >
                            ➤
                        </button>
                    </form>
                </section>
            </div>
        </div>
    );
}
