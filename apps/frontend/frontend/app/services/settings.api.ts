/**
 * Settings API Service
 * Handles user settings and notification preferences
 */

import { UserSettings, UpdateSettingsRequest, NotificationTimePreference } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Default user ID (matches backend default)
const DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001";

/**
 * Get user settings from the backend
 */
export async function fetchUserSettings(userId: string = DEFAULT_USER_ID): Promise<UserSettings | null> {
  try {
    const response = await fetch(`${API_BASE}/settings/${userId}`);
    
    if (response.status === 404) {
      // Settings not found - will need to create
      return null;
    }
    
    if (!response.ok) {
      throw new Error(`Failed to fetch settings: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error("Error fetching user settings:", error);
    return null;
  }
}

/**
 * Create user settings
 */
export async function createUserSettings(
  userId: string = DEFAULT_USER_ID,
  settings: UpdateSettingsRequest
): Promise<UserSettings | null> {
  try {
    const response = await fetch(`${API_BASE}/settings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        ...settings,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create settings: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error("Error creating user settings:", error);
    return null;
  }
}

/**
 * Update user settings
 */
export async function updateUserSettings(
  userId: string = DEFAULT_USER_ID,
  settings: UpdateSettingsRequest
): Promise<UserSettings | null> {
  try {
    const response = await fetch(`${API_BASE}/settings/${userId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(settings),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update settings: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error("Error updating user settings:", error);
    return null;
  }
}

/**
 * Save or update user settings (creates if not exists)
 */
export async function saveUserSettings(
  userId: string = DEFAULT_USER_ID,
  settings: UpdateSettingsRequest
): Promise<UserSettings | null> {
  // Try to update first
  const existingSettings = await fetchUserSettings(userId);
  
  if (existingSettings) {
    return updateUserSettings(userId, settings);
  } else {
    return createUserSettings(userId, settings);
  }
}

/**
 * Helper to convert minutes to human-readable label
 */
export function minutesToLabel(minutes: number): string {
  if (minutes >= 1440) {
    const days = Math.floor(minutes / 1440);
    return `${days} day${days > 1 ? 's' : ''} before`;
  } else if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    return `${hours} hour${hours > 1 ? 's' : ''} before`;
  } else {
    return `${minutes} minute${minutes > 1 ? 's' : ''} before`;
  }
}

/**
 * Predefined notification time options
 */
export const NOTIFICATION_TIME_OPTIONS: { value: number; label: string }[] = [
  { value: 10, label: "10 minutes before" },
  { value: 15, label: "15 minutes before" },
  { value: 30, label: "30 minutes before" },
  { value: 60, label: "1 hour before" },
  { value: 120, label: "2 hours before" },
  { value: 360, label: "6 hours before" },
  { value: 720, label: "12 hours before" },
  { value: 1440, label: "1 day before" },
];

/**
 * Send a test email to the user's notification email
 */
export async function sendTestEmail(userId: string = DEFAULT_USER_ID): Promise<{ success: boolean; message: string; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/settings/${userId}/test-email`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        message: "Failed to send test email",
        error: errorData.detail || "Unknown error"
      };
    }

    const data = await response.json();
    return {
      success: true,
      message: data.message,
      error: undefined
    };
  } catch (error) {
    console.error("Error sending test email:", error);
    return {
      success: false,
      message: "Failed to send test email",
      error: error instanceof Error ? error.message : "Unknown error"
    };
  }
}
