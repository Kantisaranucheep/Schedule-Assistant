"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { ChatSession, Ev } from "../../../types";
import { tokenize, uid } from "../../../utils";
import { buildSessionId, playTTS, sendLLMMessage, initSpeechRecognition, startSpeechRecognition, stopSpeechRecognition, SpeechRecognitionState, LLMChatResponse } from "./llmAgent";

// Default calendar ID - in production, this should come from user context
const DEFAULT_CALENDAR_ID = "00000000-0000-0000-0000-000000000001";

export type ChatModalConfig = {
  calendarId?: string;
  userId?: string;
  onEventCreated?: (event: Record<string, unknown>) => void;
  onEventDeleted?: (eventId: string) => void;
  onEventUpdated?: (event: Record<string, unknown>) => void;
};

export function useChatModal(config: ChatModalConfig = {}) {
  const calendarId = config.calendarId || DEFAULT_CALENDAR_ID;
  const userId = config.userId;

  const [chatOpen, setChatOpen] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [sessionId] = useState(() => buildSessionId());

  const [sessions, setSessions] = useState<ChatSession[]>([
    {
      id: "s1",
      title: "Chat 1",
      messages: [
        {
          id: "m1",
          role: "agent",
          text: "Made An Appointment For Me",
          createdAt: Date.now() - 50000,
        },
        {
          id: "m2",
          role: "agent",
          text: "Ok Sir! Who is the appointment with, and when should it be?",
          createdAt: Date.now() - 49000,
        },
        {
          id: "m3",
          role: "user",
          text: "With my advisor, tomorrow afternoon",
          tokens: tokenize("With my advisor, tomorrow afternoon"),
          createdAt: Date.now() - 48000,
        },
        {
          id: "m4",
          role: "agent",
          text: "Got it. What duration do you want? 30 or 60 minutes?",
          createdAt: Date.now() - 47000,
        },
        {
          id: "m5",
          role: "user",
          text: "30 minutes",
          tokens: tokenize("30 minutes"),
          createdAt: Date.now() - 46000,
        },
      ],
    },
    { id: "s2", title: "Chat 2", messages: [] },
    { id: "s3", title: "Chat 3", messages: [] },
    { id: "s4", title: "Chat 4", messages: [] },
    { id: "s5", title: "Chat 5", messages: [] },
  ]);

  const [activeSessionId, setActiveSessionId] = useState("s1");
  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // STT state
  const [speechState, setSpeechState] = useState<SpeechRecognitionState>({ recognition: null, isRecording: false });

  useEffect(() => {
    const state = initSpeechRecognition({
      onResult: (transcript) => {
        setChatInput(transcript);
      },
      onError: (error) => {
        console.error("STT error:", error);
      },
      onEnd: () => {
        // Optional: handle end
      },
    });
    setSpeechState(state);
  }, []);

  const toggleRecording = () => {
    if (speechState.isRecording) {
      stopSpeechRecognition(speechState, setSpeechState);
    } else {
      startSpeechRecognition(speechState, setSpeechState);
    }
  };

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) || sessions[0],
    [sessions, activeSessionId]
  );

  const toggleTts = () => setTtsEnabled((prev) => !prev);

  const appendSessionMessage = (role: "user" | "agent", text: string) => {
    const newMessage = {
      id: uid(role === "user" ? "msg" : "msg_ai"),
      role,
      text,
      createdAt: Date.now(),
    };

    setSessions((prev) =>
      prev.map((s) =>
        s.id !== activeSessionId ? s : { ...s, messages: [...s.messages, newMessage] }
      )
    );
  };

  const pushUserMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const tokens = tokenize(trimmed);

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
    setIsTyping(true);

    try {
      const response: LLMChatResponse = await sendLLMMessage({
        message: trimmed,
        sessionId,
        calendarId,
        userId,
        executeIntent: true,
      });

      if (response.error) {
        appendSessionMessage("agent", `⚠️ Error: ${response.error}`);
      } else if (response.reply) {
        appendSessionMessage("agent", response.reply);

        // Handle action results - trigger callbacks
        if (response.action_result?.success) {
          if (response.intent?.intent === "create_event" && response.action_result.event) {
            config.onEventCreated?.(response.action_result.event);
          } else if (response.intent?.intent === "delete_event") {
            const eventId = response.intent.params?.event_id as string;
            if (eventId) config.onEventDeleted?.(eventId);
          } else if (response.intent?.intent === "move_event" && response.action_result.event) {
            config.onEventUpdated?.(response.action_result.event);
          }
        }

        if (ttsEnabled) {
          await playTTS(response.reply);
        }
      }
    } catch (err) {
      appendSessionMessage("agent", `⚠️ Network error: ${(err as Error).message}`);
    } finally {
      setIsTyping(false);
    }
  };

  const newSession = () => {
    const id = uid("s");
    setSessions((prev) => [{ id, title: `Chat ${prev.length + 1}`, messages: [] }, ...prev]);
    setActiveSessionId(id);
  };

  return {
    chatOpen,
    setChatOpen,
    sessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    chatInput,
    setChatInput,
    pushUserMessage,
    newSession,
    isTyping,
    ttsEnabled,
    toggleTts,
    chatEndRef,
    isRecording: speechState.isRecording,
    toggleRecording,
  };
}
