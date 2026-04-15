/**
 * User Profile API Service
 * Handles communication with user profile/persona backend endpoints
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface PriorityConfig {
  [eventType: string]: number;
}

export interface PriorityExtractionResponse {
  success: boolean;
  priorities: PriorityConfig;
  persona_summary?: string;
  reasoning?: string;
  recommended_strategy?: string;
  error?: string;
}

export interface UserProfileResponse {
  id: string;
  user_id: string;
  user_story?: string;
  priority_config?: PriorityConfig;
  default_priorities?: PriorityConfig;
  scheduling_strategy: string;
  priorities_extracted_at?: string;
  merged_priorities: PriorityConfig;
}

export interface UserProfileWithExtractionResponse {
  profile: UserProfileResponse;
  extraction?: PriorityExtractionResponse;
}

export interface UserStoryRequest {
  user_story: string;
  extract_priorities?: boolean;
}

export interface PriorityUpdateRequest {
  priorities: PriorityConfig;
  strategy?: string;
}

export interface StrategyUpdateRequest {
  strategy: "minimize_moves" | "maximize_quality" | "balanced";
}

export interface EventPriorityResponse {
  event_type: string;
  priority: number;
  source: "extracted" | "default" | "fallback";
}

/**
 * Get user profile with priorities
 */
export async function getUserProfile(userId: string): Promise<UserProfileResponse> {
  const res = await fetch(`${API_BASE}/user-profile/${userId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to get user profile: ${error}`);
  }

  return res.json();
}

/**
 * Save user story and extract priorities
 */
export async function saveUserStory(
  userId: string,
  request: UserStoryRequest
): Promise<UserProfileWithExtractionResponse> {
  const res = await fetch(`${API_BASE}/user-profile/${userId}/story`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to save user story: ${error}`);
  }

  return res.json();
}

/**
 * Re-extract priorities from existing user story
 */
export async function extractPriorities(
  userId: string
): Promise<PriorityExtractionResponse> {
  const res = await fetch(`${API_BASE}/user-profile/${userId}/extract`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to extract priorities: ${error}`);
  }

  return res.json();
}

/**
 * Manually update priority weights
 */
export async function updatePriorities(
  userId: string,
  request: PriorityUpdateRequest
): Promise<UserProfileResponse> {
  const res = await fetch(`${API_BASE}/user-profile/${userId}/priorities`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to update priorities: ${error}`);
  }

  return res.json();
}

/**
 * Update scheduling strategy
 */
export async function updateStrategy(
  userId: string,
  request: StrategyUpdateRequest
): Promise<UserProfileResponse> {
  const res = await fetch(`${API_BASE}/user-profile/${userId}/strategy`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to update strategy: ${error}`);
  }

  return res.json();
}

/**
 * Get merged priorities for user
 */
export async function getPriorities(
  userId: string
): Promise<{ priorities: PriorityConfig }> {
  const res = await fetch(`${API_BASE}/user-profile/${userId}/priorities`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to get priorities: ${error}`);
  }

  return res.json();
}

/**
 * Get priority for a specific event type
 */
export async function getEventPriority(
  userId: string,
  eventType: string
): Promise<EventPriorityResponse> {
  const res = await fetch(
    `${API_BASE}/user-profile/${userId}/priority/${encodeURIComponent(eventType)}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to get event priority: ${error}`);
  }

  return res.json();
}

/**
 * Delete user profile
 */
export async function deleteUserProfile(userId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/user-profile/${userId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to delete user profile: ${error}`);
  }
}

// Helper function to get priority label
export function getPriorityLabel(priority: number): string {
  if (priority >= 9) return "Critical";
  if (priority >= 7) return "High";
  if (priority >= 5) return "Medium";
  if (priority >= 3) return "Low";
  return "Very Low";
}

// Helper function to get priority color
export function getPriorityColor(priority: number): string {
  if (priority >= 9) return "#dc3545"; // Red
  if (priority >= 7) return "#fd7e14"; // Orange
  if (priority >= 5) return "#ffc107"; // Yellow
  if (priority >= 3) return "#20c997"; // Teal
  return "#6c757d"; // Gray
}

// Strategy descriptions
export const STRATEGY_DESCRIPTIONS = {
  minimize_moves: "Move the fewest events possible, even if higher priority events get displaced",
  maximize_quality: "Always protect high-priority events, even if it means moving many lower priority ones",
  balanced: "Balance between minimizing moves and protecting high-priority events",
};

// Event type display names
export const EVENT_TYPE_LABELS: Record<string, string> = {
  exam: "Exams & Tests",
  deadline: "Deadlines",
  meeting: "Meetings",
  study: "Study Sessions",
  class: "Classes",
  appointment: "Appointments",
  work: "Work",
  interview: "Interviews",
  presentation: "Presentations",
  exercise: "Exercise",
  social: "Social Events",
  party: "Parties",
  personal: "Personal",
  travel: "Travel",
  family: "Family",
  hobby: "Hobbies",
  rest: "Rest & Breaks",
  other: "Other",
};
