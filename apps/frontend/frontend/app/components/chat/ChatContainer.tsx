"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import {
  sendChatMessage,
  sendChatChoice,
  terminateChatSession,
  generateSessionId,
  AgentMessage,
  ChoiceOption,
  ChatAgentResponse,
} from "../../services/chat-agent.api";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string | AgentMessage;
  timestamp: Date;
}

interface ChatContainerProps {
  calendarId?: string;
}

export default function ChatContainer({ calendarId }: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize session on mount
  useEffect(() => {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);

    // Add welcome message
    setMessages([
      {
        id: "welcome",
        role: "agent",
        content: {
          text: "👋 Hi! I'm your schedule assistant. I can help you:\n\n• Add new events\n• Edit existing events\n• Remove events\n• Check your schedule\n\nTry saying something like \"Add a meeting tomorrow at 9am\" or \"What do I have this week?\"",
          requires_response: false,
        },
        timestamp: new Date(),
      },
    ]);
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = useCallback(
    (role: "user" | "agent", content: string | AgentMessage) => {
      const newMessage: Message = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substring(7)}`,
        role,
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, newMessage]);
      return newMessage.id;
    },
    []
  );

  const handleSendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      setError(null);
      addMessage("user", text);
      setIsLoading(true);

      // Add loading indicator
      const loadingId = addMessage("agent", {
        text: "",
        requires_response: false,
      });

      try {
        const response: ChatAgentResponse = await sendChatMessage({
          message: text,
          session_id: sessionId,
          calendar_id: calendarId,
        });

        // Remove loading message and add real response
        setMessages((prev) =>
          prev.filter((m) => m.id !== loadingId).concat({
            id: `msg-${Date.now()}`,
            role: "agent",
            content: response.message,
            timestamp: new Date(),
          })
        );

        // Update session ID if it changed
        if (response.session_id !== sessionId) {
          setSessionId(response.session_id);
        }
      } catch (err) {
        // Remove loading message and show error
        setMessages((prev) => prev.filter((m) => m.id !== loadingId));
        const errorMessage =
          err instanceof Error ? err.message : "An error occurred";
        setError(errorMessage);
        addMessage("agent", {
          text: `Sorry, something went wrong: ${errorMessage}. Please try again.`,
          requires_response: false,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, calendarId, isLoading, addMessage]
  );

  const handleChoiceClick = useCallback(
    async (choice: ChoiceOption) => {
      if (isLoading) return;

      setError(null);
      addMessage("user", choice.label);
      setIsLoading(true);

      const loadingId = addMessage("agent", {
        text: "",
        requires_response: false,
      });

      try {
        const response: ChatAgentResponse = await sendChatChoice({
          session_id: sessionId,
          choice_id: choice.id,
          choice_value: choice.value,
        });

        setMessages((prev) =>
          prev.filter((m) => m.id !== loadingId).concat({
            id: `msg-${Date.now()}`,
            role: "agent",
            content: response.message,
            timestamp: new Date(),
          })
        );
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.id !== loadingId));
        const errorMessage =
          err instanceof Error ? err.message : "An error occurred";
        setError(errorMessage);
        addMessage("agent", {
          text: `Sorry, something went wrong: ${errorMessage}. Please try again.`,
          requires_response: false,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, isLoading, addMessage]
  );

  const handleTerminate = useCallback(async () => {
    try {
      await terminateChatSession(sessionId);
    } catch {
      // Ignore errors on terminate
    }

    // Reset session
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    setMessages([
      {
        id: "welcome-new",
        role: "agent",
        content: {
          text: "Session ended. Starting fresh! How can I help you?",
          requires_response: false,
        },
        timestamp: new Date(),
      },
    ]);
    setError(null);
  }, [sessionId]);

  return (
    <div className="d-flex flex-column h-100 bg-white rounded-4 shadow overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3" style={{ background: "linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%)" }}>
        <h2 className="h5 mb-1 text-white fw-semibold">Schedule Assistant</h2>
        <p className="text-white-50 small mb-0">
          Chat with AI to manage your calendar
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="alert alert-danger rounded-0 border-0 border-bottom mb-0 py-2 px-4 small">
          {error}
        </div>
      )}

      {/* Messages area */}
      <div className="flex-grow-1 overflow-auto p-3" style={{ minHeight: 0 }}>
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            role={msg.role}
            message={msg.content}
            onChoiceClick={handleChoiceClick}
            isLoading={
              isLoading &&
              msg.role === "agent" &&
              typeof msg.content !== "string" &&
              msg.content.text === ""
            }
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <ChatInput
        onSend={handleSendMessage}
        onTerminate={handleTerminate}
        disabled={isLoading}
        placeholder={
          isLoading ? "Thinking..." : "Type your message or click a button..."
        }
      />
    </div>
  );
}
