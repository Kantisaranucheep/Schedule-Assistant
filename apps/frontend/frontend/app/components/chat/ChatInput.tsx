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
    <div className="border-top bg-white p-3">
      <div className="d-flex align-items-end gap-2">
        {/* Terminate button */}
        <button
          onClick={onTerminate}
          className="btn btn-outline-danger btn-sm flex-shrink-0"
          title="Cancel and discard conversation"
          style={{ width: "38px", height: "38px" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
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
              minHeight: "38px", 
              resize: "none",
              borderRadius: "0.75rem",
              fontSize: "0.875rem",
            }}
          />
        </div>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="btn btn-primary flex-shrink-0"
          style={{ width: "38px", height: "38px", borderRadius: "0.75rem" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </button>
      </div>

      <p className="mt-2 text-muted text-center small mb-0">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
