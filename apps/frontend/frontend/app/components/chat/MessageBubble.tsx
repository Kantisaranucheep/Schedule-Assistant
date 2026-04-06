"use client";

import React from "react";
import { AgentMessage, ChoiceOption } from "../../services/chat-agent.api";

interface MessageBubbleProps {
  role: "user" | "agent";
  message: string | AgentMessage;
  onChoiceClick?: (choice: ChoiceOption) => void;
  isLoading?: boolean;
}

export default function MessageBubble({
  role,
  message,
  onChoiceClick,
  isLoading = false,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const messageText = typeof message === "string" ? message : message.text;
  const choices = typeof message === "string" ? undefined : message.choices;

  return (
    <div className={`d-flex ${isUser ? "justify-content-end" : "justify-content-start"} mb-3`}>
      <div
        className={`px-3 py-2 shadow-sm ${
          isUser
            ? "bg-primary text-white"
            : "bg-light text-dark"
        }`}
        style={{
          maxWidth: "80%",
          borderRadius: isUser 
            ? "1rem 1rem 0 1rem" 
            : "1rem 1rem 1rem 0",
        }}
      >
        {/* Message text with line breaks */}
        <div className="small" style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
          {isLoading ? (
            <div className="typing-dots d-flex align-items-center gap-1">
              <span></span>
              <span></span>
              <span></span>
            </div>
          ) : (
            messageText
          )}
        </div>

        {/* Choice buttons */}
        {choices && choices.length > 0 && !isLoading && (
          <div className="mt-2 d-flex flex-column gap-2">
            {choices.map((choice) => (
              <button
                key={choice.id}
                onClick={() => onChoiceClick?.(choice)}
                className="btn btn-outline-primary btn-sm text-start w-100"
                style={{ 
                  borderRadius: "0.5rem",
                  fontSize: "0.8125rem",
                }}
              >
                {choice.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
