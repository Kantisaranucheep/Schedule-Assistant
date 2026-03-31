import React from "react";
import { ChatSession } from "../../../types";

export function normalizeChatInput(text: string): string {
    return text.trim();
}

export function sendChatMessage(
    chatInput: string,
    activeSession: ChatSession | undefined,
    pushUserMessage: (s: string) => void,
    setChatInput: (s: string) => void,
): void {
    const normalized = normalizeChatInput(chatInput);
    if (!normalized || !activeSession) return;

    pushUserMessage(normalized);
    setChatInput("");
}

export function handleFormSubmit(
    event: React.FormEvent<HTMLFormElement>,
    chatInput: string,
    activeSession: ChatSession | undefined,
    pushUserMessage: (s: string) => void,
    setChatInput: (s: string) => void,
): void {
    event.preventDefault();
    sendChatMessage(chatInput, activeSession, pushUserMessage, setChatInput);
}

export function handleInputKeyDown(
    event: React.KeyboardEvent<HTMLInputElement>,
    callback: (event: React.FormEvent<HTMLFormElement>) => void,
): void {
    if (event.key !== "Enter" || event.shiftKey) return;

    event.preventDefault();
    callback(event as unknown as React.FormEvent<HTMLFormElement>);
}
