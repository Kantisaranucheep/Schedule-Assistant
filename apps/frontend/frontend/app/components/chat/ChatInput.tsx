"use client";

import React, { useState, KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  onTerminate: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  onSend,
  onTerminate,
  disabled = false,
  placeholder = "Type your message...",
}: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    const trimmed = input.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setInput("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-top p-3" style={{ backgroundColor: "#ffffff" }}>
      <div className="d-flex align-items-end gap-3 px-1">
        {/* Terminate button */}
        <button
          onClick={onTerminate}
          className="btn btn-light border flex-shrink-0 d-flex align-items-center justify-content-center hover-lift transition-all"
          title="Terminate Session"
          aria-label="Terminate Session"
          style={{ width: "44px", height: "44px", borderRadius: "12px", color: "#dc3545" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        {/* Input area */}
        <div className="flex-grow-1">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            rows={1}
            className="form-control"
            style={{ 
              maxHeight: "120px", 
              minHeight: "44px", 
              resize: "none",
              borderRadius: "12px",
              fontSize: "0.9375rem",
              paddingTop: "10px",
              paddingBottom: "10px",
              boxShadow: "none",
              backgroundColor: "#f8f9fa",
              border: "1px solid #e9ecef"
            }}
          />
        </div>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          title="Send Message"
          aria-label="Send Message"
          className="btn btn-primary flex-shrink-0 d-flex align-items-center justify-content-center hover-lift transition-all"
          style={{ width: "44px", height: "44px", borderRadius: "12px", border: "none", boxShadow: "0 4px 12px rgba(13, 110, 253, 0.2)" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
    </div>
  );
}
