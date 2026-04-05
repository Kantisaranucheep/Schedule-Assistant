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

// Chat V2 Types (new chat feature)
export interface ChatButtonV2 {
    label: string;
    value: string;
}

export interface ChatTableV2 {
    headers: string[];
    rows: (string | number)[][];
}

export interface ChatMessageV2 {
    id: string;
    role: "user" | "agent";
    text: string;
    timestamp: number;
    buttons?: ChatButtonV2[];
    table?: ChatTableV2;
}

export interface ChatSessionV2 {
    id: string;
    title: string;
    messages: ChatMessageV2[];
    currentState: string;
    createdAt: string;
}

export type FilterCriteria = {
    searchText: string;
    kindFilter: "all" | "event" | "task";
    locationFilter: string;
    fromDate: string;
    toDate: string;
    selectedCategories: string[];
};
