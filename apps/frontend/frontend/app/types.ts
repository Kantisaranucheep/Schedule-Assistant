export type Kind = "event" | "task";

export type Ev = {
    id: number;
    kind: Kind;
    allDay: boolean;
    startMin: number;
    endMin: number;
    title: string;
    color: string; // color = category
    location: string;
    notes: string;
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
