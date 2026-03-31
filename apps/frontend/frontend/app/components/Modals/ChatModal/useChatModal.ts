"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { ChatSession } from "../../../types";
import { tokenize, uid } from "../../../utils";
import { buildSessionId, playTTS, sendLLMMessage, initSpeechRecognition, startSpeechRecognition, stopSpeechRecognition, SpeechRecognitionState } from "./llmAgent";

export function useChatModal() {
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
      const { reply, error } = await sendLLMMessage(trimmed, sessionId);
      if (error) {
        appendSessionMessage("agent", `⚠️ Error: ${error}`);
      } else if (reply) {
        appendSessionMessage("agent", reply);
        if (ttsEnabled) {
          await playTTS(reply);
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
