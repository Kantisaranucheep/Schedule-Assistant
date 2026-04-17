/**
 * Chat Agent API Service
 * Handles communication with the new chat agent backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface ChoiceOption {
  id: string;
  label: string;
  value: string;
}

export interface AgentMessage {
  text: string;
  choices?: ChoiceOption[];
  requires_response: boolean;
  timeout_seconds?: number;
}

export interface SessionState {
  state: string;
  intent?: string;
  event_data?: Record<string, unknown>;
  conflict_info?: Record<string, unknown>;
}

export interface ChatAgentResponse {
  session_id: string;
  message: AgentMessage;
  state: SessionState;
  success: boolean;
  error?: string;
  event_created?: Record<string, unknown>;
  event_updated?: Record<string, unknown>;
  event_deleted?: string;
  events_list?: Record<string, unknown>[];
}

export interface ChatMessageRequest {
  message: string;
  session_id?: string;
  calendar_id?: string;
  user_id?: string;
  timezone?: string;
}

export interface ChatChoiceRequest {
  session_id: string;
  choice_id: string;
  choice_value: string;
}

export interface ChatTerminateRequest {
  session_id: string;
}

export interface ChatTerminateResponse {
  session_id: string;
  terminated: boolean;
  message: string;
}

export interface ChatHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  components: {
    llm: {
      status: string;
      available: boolean;
    };
    prolog: {
      status: string;
      available: boolean;
      note?: string;
    };
  };
}

/**
 * Send a message to the chat agent
 */
export async function sendChatMessage(
  request: ChatMessageRequest
): Promise<ChatAgentResponse> {
  const res = await fetch(`${API_BASE}/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: request.message,
      session_id: request.session_id,
      calendar_id: request.calendar_id,
      user_id: request.user_id,
      timezone: request.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
    }),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to send message: ${error}`);
  }

  return res.json();
}

/**
 * Send a choice selection to the chat agent
 */
export async function sendChatChoice(
  request: ChatChoiceRequest
): Promise<ChatAgentResponse> {
  const res = await fetch(`${API_BASE}/chat/choice`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to send choice: ${error}`);
  }

  return res.json();
}

/**
 * Terminate the current chat session
 */
export async function terminateChatSession(
  sessionId: string
): Promise<ChatTerminateResponse> {
  const res = await fetch(`${API_BASE}/chat/terminate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to terminate session: ${error}`);
  }

  return res.json();
}

/**
 * Get the current state of a chat session
 */
export async function getChatSessionState(
  sessionId: string
): Promise<SessionState | null> {
  const res = await fetch(`${API_BASE}/chat/session/${sessionId}`);

  if (!res.ok) {
    if (res.status === 404) {
      return null;
    }
    const error = await res.text();
    throw new Error(`Failed to get session state: ${error}`);
  }

  const text = await res.text();
  if (!text || text === "null") {
    return null;
  }

  return JSON.parse(text);
}

/**
 * Check the health of the chat agent
 */
export async function getChatHealth(): Promise<ChatHealthResponse> {
  const res = await fetch(`${API_BASE}/chat/health`);

  if (!res.ok) {
    throw new Error("Failed to check chat health");
  }

  return res.json();
}

/**
 * Generate a new session ID
 */
export function generateSessionId(): string {
  return crypto.randomUUID();
}
