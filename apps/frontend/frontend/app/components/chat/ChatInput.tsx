"use client";

import React, { useState, KeyboardEvent } from "react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (message: string) => void;
  onTerminate: () => void;
  isRecording?: boolean;
  onToggleRecording?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  value,
  onChange,
  onSend,
  onTerminate,
  isRecording = false,
  onToggleRecording,
  disabled = false,
  placeholder = "Type your message...",
}: ChatInputProps) {
  const handleSend = () => {
    const trimmed = value.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
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

        {/* Mic button (Speech-to-Text) */}
        {onToggleRecording && (
          <button
            onClick={onToggleRecording}
            className={`btn flex-shrink-0 d-flex align-items-center justify-content-center hover-lift transition-all ${
              isRecording ? "btn-danger pulse-recording" : "btn-light border"
            }`}
            title={isRecording ? "Stop Recording" : "Open Mic"}
            aria-label={isRecording ? "Stop Recording" : "Open Mic"}
            style={{ 
              width: "44px", 
              height: "44px", 
              borderRadius: "12px", 
              color: isRecording ? "#fff" : "#5a67d8" 
            }}
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
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          </button>
        )}

        {/* Input area */}
        <div className="flex-grow-1">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
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
          disabled={disabled || !value.trim()}
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

      <style jsx>{`
        .pulse-recording {
          animation: pulse-red 1.5s infinite;
          box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
        }
        @keyframes pulse-red {
          0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7); }
          70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(220, 53, 69, 0); }
          100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
        }
      `}</style>
    </div>
  );
}
