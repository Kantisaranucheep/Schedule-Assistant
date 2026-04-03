/**
 * Chat API Service
 * Handles chat session and message API calls
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatMessageResponse {
  id: string;
  role: "user" | "agent";
  text: string;
  created_at: string;
}

export interface ChatSessionResponse {
  id: string;
  title: string;
  created_at: string;
  messages: ChatMessageResponse[];
}

/**
 * Fetch all chat sessions for a user
 */
export async function fetchChatSessions(userId: string): Promise<ChatSessionResponse[]> {
  const params = new URLSearchParams({ user_id: userId });
  
  const res = await fetch(`${API_BASE}/agent/sessions?${params}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch chat sessions: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Fetch a specific chat session with messages
 */
export async function fetchChatSession(sessionId: string): Promise<ChatSessionResponse> {
  const res = await fetch(`${API_BASE}/agent/sessions/${sessionId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch chat session: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Create a new chat session
 */
export async function createChatSession(
  userId: string,
  title: string = "New Chat"
): Promise<ChatSessionResponse> {
  const params = new URLSearchParams({ user_id: userId, title });
  
  const res = await fetch(`${API_BASE}/agent/sessions?${params}`, {
    method: "POST",
  });
  
  if (!res.ok) {
    throw new Error(`Failed to create chat session: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Delete a chat session
 */
export async function deleteChatSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/agent/sessions/${sessionId}`, {
    method: "DELETE",
  });
  
  if (!res.ok) {
    throw new Error(`Failed to delete chat session: ${res.statusText}`);
  }
}
