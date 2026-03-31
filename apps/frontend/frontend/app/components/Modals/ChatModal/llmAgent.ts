export type LLMChatResponse = {
    reply: string;
    error?: string;
    intent_json?: Record<string, unknown>;
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

export async function sendLLMMessage(
    message: string,
    sessionId: string,
    url = "http://localhost:8000/agent/chat",
): Promise<LLMChatResponse> {
    const cleanMessage = message.trim();
    if (!cleanMessage) {
        return { reply: "", error: "Empty message" };
    }

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            message: cleanMessage,
            session_id: sessionId,
            current_datetime: new Date().toISOString().slice(0, 16).replace("T", " "),
        }),
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
    if (!text.trim()) {
        return;
    }

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });
        if (!response.ok) {
            console.warn("TTS request failed", response.status);
            return;
        }
        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);
        await audio.play();
        URL.revokeObjectURL(audioUrl);
    } catch (error) {
        console.error("TTS playback error:", error);
    }
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
