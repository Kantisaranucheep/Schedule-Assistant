export type Kind = "event" | "task";

export type EventCategory = {
    id: string;
    name: string;
    color: string;
};

export type Ev = {
    id: string | number; // string for API events (UUID), number for local
    kind: Kind;
    allDay: boolean;
    startMin: number;
    endMin: number;
    title: string;
    color: string; // color = category
    categoryId?: string;
    location: string;
    notes: string;
    isRecurring?: boolean;
    recurEndDate?: string;
    recurDays?: number[]; // 0=Sun, 1=Mon, ..., 6=Sat
};

export type EventMap = Record<string, Ev[]>;

export type ChatRole = "user" | "agent";

export type ChatMsg = {
    id: string;
    role: ChatRole;
    text: string;
    tokens?: string[];
    createdAt: number;
};

export type ChatSession = {
    id: string;
    title: string;
    messages: ChatMsg[];
    isPinned?: boolean;
};
export type FilterCriteria = {
    searchText: string;
    kindFilter: "all" | "event" | "task";
    locationFilter: string;
    fromDate: string;
    toDate: string;
    selectedCategories: string[];
};

// Notification time preference (e.g., 1 day before, 30 minutes before)
export type NotificationTimePreference = {
    minutes_before: number; // 10-1440 (max 1 day)
    label?: string; // Human readable label like "1 day before"
};

export type NotificationSettings = {
    windowEnabled: boolean;
    emailEnabled: boolean;
    notificationTimes: NotificationTimePreference[]; // Max 2 items
};

// User settings from API
export type UserSettings = {
    id: string;
    user_id: string;
    working_hours_start: string;
    working_hours_end: string;
    buffer_minutes: number;
    notification_email: string | null;
    notifications_enabled: boolean;
    window_notifications_enabled: boolean;
    notification_times: NotificationTimePreference[];
    created_at: string;
    updated_at: string;
};

// Update settings request
export type UpdateSettingsRequest = {
    working_hours_start?: string;
    working_hours_end?: string;
    buffer_minutes?: number;
    notification_email?: string | null;
    notifications_enabled?: boolean;
    window_notifications_enabled?: boolean;
    notification_times?: NotificationTimePreference[];
};
