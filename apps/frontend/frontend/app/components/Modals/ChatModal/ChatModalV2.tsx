import React, { useState, useRef, useEffect } from "react";
import styles from "./ChatModalV2.module.css";

interface ChatMessage {
  id: string;
  role: "user" | "agent";
  text: string;
  timestamp: number;
  buttons?: ChatButton[];
  table?: ChatTable;
}

interface ChatButton {
  label: string;
  value: string;
}

interface ChatTable {
  headers: string[];
  rows: (string | number)[][];
}

interface ChatModalV2Props {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  calendarId: string;
}

export default function ChatModalV2({ isOpen, onClose, userId, calendarId }: ChatModalV2Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentState, setCurrentState] = useState("initial");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Initialize chat on open
  useEffect(() => {
    if (isOpen && !sessionId) {
      initializeChat();
    }
  }, [isOpen]);

  // Initialize chat session
  const initializeChat = async () => {
    try {
      setLoading(true);
      console.log("[ChatModalV2] Starting chat with userId:", userId, "calendarId:", calendarId);

      const response = await fetch("/api/agent/chat-v2/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          calendar_id: calendarId,
          title: `Chat ${new Date().toLocaleString()}`,
        }),
      });

      console.log("[ChatModalV2] Response status:", response.status);
      const responseText = await response.text();
      console.log("[ChatModalV2] Response body:", responseText);

      if (!response.ok) {
        let errorMsg = "Failed to start chat";
        try {
          const errorData = JSON.parse(responseText);
          errorMsg = errorData.error || errorData.detail || errorMsg;
        } catch {
          errorMsg = `Backend error (${response.status}): ${responseText}`;
        }
        throw new Error(errorMsg);
      }

      const data = JSON.parse(responseText);
      console.log("[ChatModalV2] Chat initialized:", data);
      setSessionId(data.session_id);
      setCurrentState(data.state);

      // Add welcome message
      setMessages([
        {
          id: "welcome",
          role: "agent",
          text: data.message,
          timestamp: Date.now(),
        },
      ]);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Unknown error";
      console.error("[ChatModalV2] Chat init error:", errorMsg);
      setMessages([
        {
          id: "error",
          role: "agent",
          text: `Failed to start chat: ${errorMsg}`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Send message
  const handleSendMessage = async (messageText?: string) => {
    const textToSend = messageText || chatInput.trim();
    if (!textToSend || !sessionId || isTyping) return;

    // Add user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: textToSend,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setIsTyping(true);

    try {
      const response = await fetch("/api/agent/chat-v2/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          user_id: userId,
          calendar_id: calendarId,
          message: textToSend,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Bangkok",
        }),
      });

      console.log("[ChatModalV2] Send response status:", response.status);
      const responseText = await response.text();
      console.log("[ChatModalV2] Send response body:", responseText);

      if (!response.ok) {
        let errorMsg = "Failed to send message";
        try {
          const errorData = JSON.parse(responseText);
          errorMsg = errorData.error || errorData.detail || errorMsg;
        } catch {
          errorMsg = `Backend error (${response.status}): ${responseText}`;
        }
        throw new Error(errorMsg);
      }

      const data = JSON.parse(responseText);
      console.log("[ChatModalV2] Message sent successfully:", data);
      setCurrentState(data.state);

      // Add agent message
      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        role: "agent",
        text: data.reply,
        timestamp: Date.now(),
        buttons: data.buttons,
        table: data.table,
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Unknown error";
      console.error("[ChatModalV2] Send message error:", errorMsg);
      const errorMsg2: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "agent",
        text: `Error: ${errorMsg}`,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMsg2]);
    } finally {
      setIsTyping(false);
    }
  };

  // Handle button click
  const handleButtonClick = (value: string) => {
    setChatInput(value);
    inputRef.current?.focus();
    // Auto-send after short delay to let user review
    setTimeout(() => {
      if (inputRef.current) {
        handleSendMessage(value);
      }
    }, 300);
  };

  // Handle input key down
  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Handle stop/close chat
  const handleStopChat = async () => {
    if (!sessionId) return;

    const confirmed = window.confirm("Save conversation and close?");
    if (!confirmed) return;

    try {
      setLoading(true);
      const response = await fetch("/api/agent/chat-v2/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!response.ok) throw new Error("Failed to stop chat");

      // Close modal
      onClose();
      setSessionId(null);
      setMessages([]);
      setCurrentState("initial");
    } catch (error) {
      console.error("Stop chat error:", error);
      alert("Error saving conversation. You can still close.");
      onClose();
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h2>Calendar Assistant</h2>
            <small>{currentState}</small>
          </div>
          <button className={styles.stopButton} onClick={handleStopChat} disabled={loading}>
            {loading ? "Saving..." : "Stop & Save"}
          </button>
        </div>

        {/* Messages Area */}
        <div className={styles.messagesContainer}>
          {messages.map((msg) => (
            <div key={msg.id} className={`${styles.message} ${styles[msg.role]}`}>
              {msg.role === "agent" && <span className={styles.avatar}>🤖</span>}

              <div className={styles.content}>
                {/* Table */}
                {msg.table && (
                  <div className={styles.tableWrapper}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          {msg.table.headers.map((header) => (
                            <th key={header}>{header}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {msg.table.rows.map((row, idx) => (
                          <tr key={idx}>
                            {row.map((cell, cidx) => (
                              <td key={cidx}>{cell}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Text */}
                <p>{msg.text}</p>

                {/* Buttons */}
                {msg.buttons && msg.buttons.length > 0 && (
                  <div className={styles.buttons}>
                    {msg.buttons.map((btn) => (
                      <button
                        key={btn.value}
                        className={styles.actionButton}
                        onClick={() => handleButtonClick(btn.value)}
                        disabled={isTyping}
                      >
                        {btn.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {msg.role === "user" && <span className={styles.avatar}>👤</span>}
            </div>
          ))}

          {/* Typing Indicator */}
          {isTyping && (
            <div className={`${styles.message} ${styles.agent}`}>
              <span className={styles.avatar}>🤖</span>
              <div className={styles.typingDots}>
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input Area */}
        <div className={styles.inputContainer}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className={styles.form}
          >
            <input
              ref={inputRef}
              type="text"
              placeholder="Ask me to add, edit, or list events..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={handleInputKeyDown}
              disabled={isTyping || loading}
              className={styles.input}
            />
            <button
              type="submit"
              disabled={isTyping || loading || !chatInput.trim()}
              className={styles.sendButton}
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
