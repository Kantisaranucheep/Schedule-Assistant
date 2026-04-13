"use client";

import { useMemo, useRef, useState, useEffect, useCallback } from "react";
import { ChatSession, ChatMsg } from "../../../types";
import { tokenize, uid } from "../../../utils";
import { buildSessionId, playTTS, sendLLMMessage, initSpeechRecognition, startSpeechRecognition, stopSpeechRecognition, SpeechRecognitionState, LLMChatResponse } from "./llmAgent";
import { 
  fetchChatSessions, 
  createChatSession, 
  ChatSessionResponse, 
  ChatMessageResponse 
} from "../../../services/chat.api";

// Default IDs - in production, these should come from user context


export type ChatModalConfig = {
  calendarId?: string;
  userId?: string;
  onEventCreated?: (event: Record<string, unknown>) => void;
  onEventDeleted?: (eventId: string) => void;
  onEventUpdated?: (event: Record<string, unknown>) => void;
};

/**
 * Transform API chat session to frontend format
 */
function transformApiSession(apiSession: ChatSessionResponse): ChatSession {
  return {
    id: apiSession.id,
    title: apiSession.title,
    messages: apiSession.messages.map((msg: ChatMessageResponse): ChatMsg => ({
      id: msg.id,
      role: msg.role as "user" | "agent",
      text: msg.text,
      tokens: msg.role === "user" ? tokenize(msg.text) : undefined,
      createdAt: new Date(msg.created_at).getTime(),
    })),
  };
}

export function useChatModal(config: ChatModalConfig = {}) {
  const [calendarId, setCalendarId] = useState<string>(config.calendarId || "");
  const [userId, setUserId] = useState<string>(config.userId || "");

  useEffect(() => {
    if (!userId) {
      try {
        const sessionItem = localStorage.getItem("scheduler_auth_session");
        if (sessionItem) {
          const sessionData = JSON.parse(sessionItem);
          if (sessionData && sessionData.user_id) {
            setUserId(sessionData.user_id);
          }
        }
      } catch (e) {
        console.error("Error reading session", e);
      }
    }
  }, [userId]);

  const [chatOpen, setChatOpen] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // STT state
  const [speechState, setSpeechState] = useState<SpeechRecognitionState>({ recognition: null, isRecording: false });

  // Load sessions from database only when chat is opened
  useEffect(() => {
    if (!chatOpen || initialized) return;

    async function loadSessions() {
      try {
        setLoading(true);
        const apiSessions = await fetchChatSessions(userId);
        
        if (apiSessions.length > 0) {
          const transformedSessions = apiSessions.map(transformApiSession);
          setSessions(transformedSessions);
          setActiveSessionId(transformedSessions[0].id);
        } else {
          // Create a new session if none exist
          try {
            const newSession = await createChatSession(userId, "Chat 1");
            const transformed = transformApiSession(newSession);
            setSessions([transformed]);
            setActiveSessionId(transformed.id);
          } catch {
            // API not available, create local session
            const fallbackSession: ChatSession = {
              id: uid("s"),
              title: "New Chat",
              messages: [],
            };
            setSessions([fallbackSession]);
            setActiveSessionId(fallbackSession.id);
          }
        }
        setInitialized(true);
      } catch (err) {
        console.error("Failed to load chat sessions:", err);
        // Fallback: create empty local session (API might not be available)
        const fallbackSession: ChatSession = {
          id: uid("s"),
          title: "New Chat",
          messages: [],
        };
        setSessions([fallbackSession]);
        setActiveSessionId(fallbackSession.id);
        setInitialized(true);
      } finally {
        setLoading(false);
      }
    }

    loadSessions();
  }, [chatOpen, initialized, userId]);

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
    const newMessage: ChatMsg = {
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
    if (!trimmed || !activeSessionId) return;

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
              role: "user" as const,
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
        sessionId: activeSessionId,
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

  const newSession = useCallback(async () => {
    try {
      const sessionNumber = sessions.length + 1;
      const newSessionData = await createChatSession(userId, `Chat ${sessionNumber}`);
      const transformed = transformApiSession(newSessionData);
      setSessions((prev) => [transformed, ...prev]);
      setActiveSessionId(transformed.id);
    } catch (err) {
      console.error("Failed to create new session:", err);
      // Fallback: create local session
      const id = uid("s");
      setSessions((prev) => [{ id, title: `Chat ${prev.length + 1}`, messages: [] }, ...prev]);
      setActiveSessionId(id);
    }
  }, [sessions.length, userId]);

  const renameSession = useCallback((sessionId: string, newTitle: string) => {
    if (!newTitle.trim()) return;
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle } : s))
    );
    // API call would go here
    console.log(`Renaming session ${sessionId} to ${newTitle}`);
  }, []);

  const deleteSession = useCallback((sessionId: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    if (activeSessionId === sessionId) {
      setActiveSessionId(null);
    }
    // API call would go here
    console.log(`Deleting session ${sessionId}`);
  }, [activeSessionId]);

  const togglePinSession = useCallback((sessionId: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, isPinned: !s.isPinned } : s))
    );
  }, []);

  const sortedSessions = useMemo(() => {
    const pinned = sessions.filter((s) => s.isPinned);
    const others = sessions.filter((s) => !s.isPinned);
    return [...pinned, ...others];
  }, [sessions]);

  return {
    chatOpen,
    setChatOpen,
    sessions: sortedSessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    chatInput,
    setChatInput,
    pushUserMessage,
    newSession,
    renameSession,
    deleteSession,
    togglePinSession,
    isTyping,
    ttsEnabled,
    toggleTts,
    chatEndRef,
    isRecording: speechState.isRecording,
    toggleRecording,
    loading,
  };
}
