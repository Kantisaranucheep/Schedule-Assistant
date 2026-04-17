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
import { 
  initSpeechRecognition, 
  startSpeechRecognition, 
  stopSpeechRecognition, 
  SpeechRecognitionState,
  playTTS
} from "../Modals/ChatModal/llmAgent";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string | AgentMessage;
  timestamp: Date;
}

interface ChatContainerProps {
  calendarId?: string;
  userId?: string;
}

export default function ChatContainer({ calendarId, userId }: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string>("");
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Speech-to-Text state
  const [speechState, setSpeechState] = useState<SpeechRecognitionState>({ 
    recognition: null, 
    isRecording: false 
  });

  const toggleTts = useCallback(() => {
    setTtsEnabled(prev => !prev);
    // Stop any ongoing speech if disabling
    if (ttsEnabled && typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }, [ttsEnabled]);

  // Initialize Speech Recognition on mount
  useEffect(() => {
    const state = initSpeechRecognition({
      onResult: (transcript) => {
        setInput(transcript);
      },
      onError: (err) => {
        console.error("STT error:", err);
      },
      onEnd: () => {
        // Recognition automatically stops after a result normally
      },
    });
    setSpeechState(state);
  }, []);

  const toggleRecording = useCallback(() => {
    if (speechState.isRecording) {
      stopSpeechRecognition(speechState, setSpeechState);
    } else {
      startSpeechRecognition(speechState, setSpeechState);
    }
  }, [speechState]);

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
          user_id: userId,
        });

        // Clear input on success
        setInput("");

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

        // Play TTS if enabled
        if (ttsEnabled && response.message.text) {
          playTTS(response.message.text);
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

        // Play TTS if enabled
        if (ttsEnabled && response.message.text) {
          playTTS(response.message.text);
        }
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
    <div className="d-flex flex-column h-100 bg-white shadow-sm overflow-hidden border-0">
      {/* Header */}
      <div className="px-4 py-3 border-bottom d-flex align-items-center justify-content-between" style={{ backgroundColor: "#ffffff" }}>
        <div>
          <h2 className="h6 mb-0 text-dark fw-bold text-uppercase letter-spacing-1">Schedule Assistant</h2>
          <p className="text-secondary small mb-0 opacity-75" style={{ fontSize: "11px" }}>
            AI-POWERED CALENDAR MANAGEMENT
          </p>
        </div>
        <div className="d-flex align-items-center gap-2">
          {/* TTS Toggle */}
          <button
            onClick={toggleTts}
            className={`btn p-2 rounded-3 transition-all d-flex align-items-center gap-1 ${
              ttsEnabled ? "bg-primary bg-opacity-10 text-primary border-primary border-opacity-25" : "text-secondary hover-bg-light"
            }`}
            title={ttsEnabled ? "Disable AI Voice" : "Enable AI Voice"}
            style={{ border: ttsEnabled ? "1px solid" : "1px solid transparent" }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              {ttsEnabled ? (
                <>
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                </>
              ) : (
                <line x1="23" y1="9" x2="17" y2="15"></line>
              )}
            </svg>
            {ttsEnabled && (
              <span className="fw-bold" style={{ fontSize: "10px", textTransform: "uppercase" }}>Voice On</span>
            )}
          </button>

          <div className="p-2 bg-primary bg-opacity-10 rounded-3 text-primary">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
        </div>
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
        value={input}
        onChange={setInput}
        onSend={handleSendMessage}
        onTerminate={handleTerminate}
        isRecording={speechState.isRecording}
        onToggleRecording={toggleRecording}
        disabled={isLoading}
        placeholder={
          isLoading ? "Thinking..." : "Type your message or click a button..."
        }
      />
    </div>
  );
}
