import React, { useState, useMemo, useEffect, useRef } from "react";
import { ChatSession } from "../../types";
import { tokenize, uid } from "../../utils";

interface ChatModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function ChatModal({
    isOpen,
    onClose,
}: ChatModalProps) {
    // Sessions + active session
    const [sessions, setSessions] = useState<ChatSession[]>([
        {
            id: "s1",
            title: "Chat 1",
            messages: [
                {
                    id: "m1",
                    role: "agent",
                    text: "Made An Appointment For Me",
                    createdAt: 1700000000000,
                },
                {
                    id: "m2",
                    role: "agent",
                    text: "Ok Sir! Who is the appointment with, and when should it be?",
                    createdAt: 1700000001000,
                },
                {
                    id: "m3",
                    role: "user",
                    text: "With my advisor, tomorrow afternoon",
                    tokens: tokenize("With my advisor, tomorrow afternoon"),
                    createdAt: 1700000002000,
                },
                {
                    id: "m4",
                    role: "agent",
                    text: "Got it. What duration do you want? 30 or 60 minutes?",
                    createdAt: 1700000003000,
                },
                {
                    id: "m5",
                    role: "user",
                    text: "30 minutes",
                    tokens: tokenize("30 minutes"),
                    createdAt: 1700000004000,
                },
            ],
        },
        { id: "s2", title: "Chat 2", messages: [] },
        { id: "s3", title: "Chat 3", messages: [] },
        { id: "s4", title: "Chat 4", messages: [] },
        { id: "s5", title: "Chat 5", messages: [] },
    ]);
    const [activeSessionId, setActiveSessionId] = useState("s1");
    const activeSession = useMemo(
        () => sessions.find((s) => s.id === activeSessionId) || sessions[0],
        [sessions, activeSessionId]
    );

    const [chatInput, setChatInput] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll chat to bottom
    useEffect(() => {
        if (isOpen) {
            chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [activeSession?.messages, isTyping, isOpen]);

    function pushUserMessage(text: string) {
        const trimmed = text.trim();
        if (!trimmed) return;

        const tokens = tokenize(trimmed);

        // Save into current session as message + tokens
        setSessions((prev) =>
            prev.map((s) => {
                if (s.id !== activeSessionId) return s;
                return {
                    ...s,
                    messages: [
                        ...s.messages,
                        {
                            id: uid("msg"),
                            role: "user",
                            text: trimmed,
                            tokens,
                            createdAt: Date.now(),
                        },
                    ],
                };
            })
        );

        setChatInput("");

        // Simulate AI response delay
        setIsTyping(true);
        setTimeout(() => {
            setSessions((prev) =>
                prev.map((s) => {
                    if (s.id !== activeSessionId) return s;
                    return {
                        ...s,
                        messages: [
                            ...s.messages,
                            {
                                id: uid("msg_ai"),
                                role: "agent",
                                text: "Got it! I'm simulating a 5-second wait to show off the cool loading animation. We can connect this to a real AI soon!",
                                createdAt: Date.now(),
                            },
                        ],
                    };
                })
            );
            setIsTyping(false);
        }, 5000);
    }

    function newSession() {
        const id = uid("s");
        setSessions((prev) => [
            { id, title: `Chat ${prev.length + 1}`, messages: [] },
            ...prev,
        ]);
        setActiveSessionId(id);
    }

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
                        {sessions.map((s) => (
                            <button
                                key={s.id}
                                type="button"
                                className={`w-100 text-start btn btn-sm mb-1 position-relative ${s.id === activeSessionId
                                    ? "bg-secondary bg-opacity-10 text-dark fw-bold border-start border-3 border-primary"
                                    : "btn-ghost text-muted"
                                    }`}
                                style={{
                                    paddingLeft: s.id === activeSessionId ? "11px" : "12px",
                                    borderTopLeftRadius: 0,
                                    borderBottomLeftRadius: 0,
                                }}
                                onClick={() => setActiveSessionId(s.id)}
                            >
                                {s.title}
                            </button>
                        ))}
                    </div>

                    <div
                        className="d-flex align-items-center gap-2 px-3 border-top bg-light flex-shrink-0"
                        style={{ height: 80, boxSizing: "border-box" }}
                    >
                        <div
                            className="rounded-circle bg-secondary bg-opacity-25 d-flex align-items-center justify-content-center"
                            style={{ width: 32, height: 32 }}
                        >
                            👤
                        </div>
                        <div className="small fw-bold">John Doe</div>
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
                        onSubmit={(e) => {
                            e.preventDefault();
                            pushUserMessage(chatInput);
                        }}
                    >
                        <input
                            className="form-control rounded-pill shadow-sm border-secondary-subtle"
                            placeholder="Enter Message"
                            style={{ height: 44 }}
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                        />
                        <button
                            className="btn btn-primary rounded-circle shadow-sm d-flex align-items-center justify-content-center"
                            style={{ width: 44, height: 44 }}
                            type="submit"
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
