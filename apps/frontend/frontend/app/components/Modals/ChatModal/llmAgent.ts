export type LLMChatResponse = {
    reply: string;
    error?: string;
    intent?: {
        intent: string;
        params: Record<string, unknown>;
    };
    action_result?: {
        success: boolean;
        message?: string;
        error?: string;
        event?: Record<string, unknown>;
        events?: Array<Record<string, unknown>>;
    };
};

export type SpeechRecognitionLike = {
    start: () => void;
    stop: () => void;
    lang: string;
    interimResults: boolean;
    continuous: boolean;
    onresult?: (event: unknown) => void;
    onerror?: (event: unknown) => void;
    onend?: () => void;
};

export type SpeechRecognitionState = {
    recognition: SpeechRecognitionLike | null;
    isRecording: boolean;
};

export type SpeechRecognitionHandlers = {
    onResult: (transcript: string) => void;
    onError?: (error: string) => void;
    onEnd?: () => void;
};

export function buildSessionId(): string {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    return "session-" + Date.now() + "-" + Math.random().toString(16).slice(2);
}

export type SendMessageOptions = {
    message: string;
    sessionId: string;
    calendarId?: string;
    userId?: string;
    executeIntent?: boolean;
    url?: string;
    timezone?: string;
};

export async function sendLLMMessage(
    messageOrOptions: string | SendMessageOptions,
    sessionId?: string,
    url = "http://localhost:8000/agent/chat",
): Promise<LLMChatResponse> {
    // Support both old and new API
    let options: SendMessageOptions;
    if (typeof messageOrOptions === "string") {
        options = {
            message: messageOrOptions,
            sessionId: sessionId || "default",
            url,
        };
    } else {
        options = messageOrOptions;
    }

    const cleanMessage = options.message.trim();
    if (!cleanMessage) {
        return { reply: "", error: "Empty message" };
    }

    const requestBody: Record<string, unknown> = {
        message: cleanMessage,
        session_id: options.sessionId,
        execute_intent: options.executeIntent ?? true,
    };

    // Add calendar_id if provided (required for executing intents)
    if (options.calendarId) {
        requestBody.calendar_id = options.calendarId;
    }

    // Add user_id if provided
    if (options.userId) {
        requestBody.user_id = options.userId;
    }

    // Add timezone for proper datetime handling
    requestBody.timezone = options.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;

    const response = await fetch(options.url || url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
        const content = await response.text();
        return {
            reply: "",
            error: `HTTP ${response.status}: ${content}`,
        };
    }

    const data = (await response.json()) as LLMChatResponse;

    if (data.error) {
        return { reply: "", error: data.error };
    }

    return data;
}

export async function playTTS(text: string, url = "http://localhost:8000/agent/tts"): Promise<void> {
    // TTS endpoint removed from backend - this is a no-op fallback
    // You can integrate a client-side TTS library like Web Speech API instead
    if (!text.trim()) {
        return;
    }

    // Try using browser's built-in speech synthesis
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "en-US";
        window.speechSynthesis.speak(utterance);
        return;
    }

    console.warn("TTS not available - no speech synthesis support");
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

type SpeechRecognitionEventLike = {
    results?: Array<Array<{ transcript?: string }>>;
};

type SpeechRecognitionErrorLike = {
    error?: string;
};

export function initSpeechRecognition(
    handlers: SpeechRecognitionHandlers,
    lang = "en-US",
): SpeechRecognitionState {
    const win = window as Window & {
        SpeechRecognition?: SpeechRecognitionConstructor;
        webkitSpeechRecognition?: SpeechRecognitionConstructor;
    };
    const SpeechRecognition = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        handlers.onError?.("SpeechRecognition API is not available in this browser");
        return { recognition: null, isRecording: false };
    }

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (event: unknown) => {
        const speechEvent = event as SpeechRecognitionEventLike;
        const transcript = speechEvent.results?.[0]?.[0]?.transcript;
        if (transcript) {
            handlers.onResult(transcript);
        }
        handlers.onEnd?.();
    };

    recognition.onerror = (event: unknown) => {
        const errorEvent = event as SpeechRecognitionErrorLike;
        handlers.onError?.(errorEvent.error || "unknown speech recognition error");
        handlers.onEnd?.();
    };

    recognition.onend = () => {
        handlers.onEnd?.();
    };

    return { recognition, isRecording: false };
}

export function startSpeechRecognition(
    state: SpeechRecognitionState,
    setState: (next: SpeechRecognitionState) => void,
): void {
    if (!state.recognition || state.isRecording) return;
    state.recognition.start();
    setState({ ...state, isRecording: true });
}

export function stopSpeechRecognition(
    state: SpeechRecognitionState,
    setState: (next: SpeechRecognitionState) => void,
): void {
    if (!state.recognition) return;

    try {
        state.recognition.stop();
    } catch {
        // no-op
    }

    setState({ ...state, isRecording: false });
}
