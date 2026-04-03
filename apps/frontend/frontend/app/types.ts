export type Kind = "event" | "task";

export type EventCategory = {
    id: string;
    name: string;
    color: string;
};

export type Ev = {
    id: number;
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
};
export type FilterCriteria = {
    searchText: string;
    kindFilter: "all" | "event" | "task";
    locationFilter: string;
    fromDate: string;
    toDate: string;
    selectedCategories: string[];
};
