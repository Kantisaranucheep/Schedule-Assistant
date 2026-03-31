/**
 * LLM Agent — Frontend Logic
 * Handles chat, Web Speech API (STT), and gTTS audio playback.
 */

// ============================================================
// State
// ============================================================
const sessionId = crypto.randomUUID();
let ttsEnabled = false;
let isRecording = false;
let recognition = null;

// ============================================================
// DOM references
// ============================================================
const chatMessages = document.getElementById("chat-messages");
const inputText = document.getElementById("input-text");
const btnSend = document.getElementById("btn-send");
const btnMic = document.getElementById("btn-mic");
const btnSpeaker = document.getElementById("btn-speaker");
const btnClear = document.getElementById("btn-clear");
const intentContent = document.getElementById("intent-content");

// ============================================================
// Initialise Web Speech API
// ============================================================
function initSpeechRecognition() {
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        btnMic.title = "Speech recognition not supported in this browser";
        btnMic.style.opacity = "0.3";
        btnMic.style.cursor = "not-allowed";
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        inputText.value = transcript;
        stopRecording();
        sendMessage();
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        stopRecording();
    };

    recognition.onend = () => {
        stopRecording();
    };
}

function startRecording() {
    if (!recognition) return;
    isRecording = true;
    btnMic.classList.add("recording");
    btnMic.textContent = "⏹️";
    recognition.start();
}

function stopRecording() {
    if (!recognition) return;
    isRecording = false;
    btnMic.classList.remove("recording");
    btnMic.textContent = "🎤";
    try { recognition.stop(); } catch (_) { /* already stopped */ }
}

// ============================================================
// Chat
// ============================================================
function addMessage(role, text) {
    // Remove the welcome message if it exists
    const welcome = chatMessages.querySelector(".welcome-message");
    if (welcome) welcome.remove();

    const div = document.createElement("div");
    div.className = `message ${role}`;

    const label = document.createElement("div");
    label.className = "label";
    label.textContent = role === "user" ? "You" : "Agent";

    const body = document.createElement("div");
    body.textContent = text;

    div.appendChild(label);
    div.appendChild(body);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
    const div = document.createElement("div");
    div.className = "typing-indicator";
    div.id = "typing";
    div.innerHTML = "<span></span><span></span><span></span>";
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTyping() {
    const el = document.getElementById("typing");
    if (el) el.remove();
}

async function sendMessage() {
    const text = inputText.value.trim();
    if (!text) return;

    addMessage("user", text);
    inputText.value = "";
    btnSend.disabled = true;
    showTyping();

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, session_id: sessionId }),
        });

        const data = await res.json();
        hideTyping();

        if (data.error) {
            addMessage("assistant", `⚠️ Error: ${data.error}`);
        } else {
            addMessage("assistant", data.reply);

            // Show intent JSON if extracted
            if (data.intent_json) {
                addIntentCard(data.intent_json);
            }

            // Play TTS if enabled
            if (ttsEnabled && data.reply) {
                playTTS(data.reply);
            }
        }
    } catch (err) {
        hideTyping();
        addMessage("assistant", `⚠️ Network error: ${err.message}`);
    } finally {
        btnSend.disabled = false;
        inputText.focus();
    }
}

// ============================================================
// Intent panel
// ============================================================
function addIntentCard(intentJson) {
    // Remove placeholder
    const placeholder = intentContent.querySelector(".placeholder-text");
    if (placeholder) placeholder.remove();

    const card = document.createElement("div");
    card.className = "intent-card";

    const label = document.createElement("div");
    label.className = "intent-label";
    label.textContent = `✅ ${intentJson.intent || "unknown"}`;

    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(intentJson, null, 2);

    const ts = document.createElement("div");
    ts.className = "timestamp";
    ts.textContent = new Date().toLocaleTimeString();

    card.appendChild(label);
    card.appendChild(pre);
    card.appendChild(ts);

    // Prepend (newest on top)
    intentContent.prepend(card);
}

// ============================================================
// TTS playback
// ============================================================
async function playTTS(text) {
    try {
        const res = await fetch("/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });

        if (!res.ok) return;

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play();
    } catch (err) {
        console.error("TTS playback error:", err);
    }
}

// ============================================================
// Event listeners
// ============================================================
btnSend.addEventListener("click", sendMessage);

inputText.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

btnMic.addEventListener("click", () => {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
});

btnSpeaker.addEventListener("click", () => {
    ttsEnabled = !ttsEnabled;
    btnSpeaker.textContent = ttsEnabled ? "🔊" : "🔇";
    btnSpeaker.classList.toggle("active", ttsEnabled);
});

btnClear.addEventListener("click", () => {
    // Clear chat UI
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <p>👋 Hi! I can help you create events, set reminders, send messages, or create tasks.</p>
            <p>Try saying: <em>"Make me an appointment tomorrow at 9 AM"</em></p>
        </div>`;

    // Clear intent panel
    intentContent.innerHTML =
        '<p class="placeholder-text">No intent extracted yet. Complete a conversation to see the JSON output here.</p>';

    // Note: This doesn't clear server-side history. A page reload gives a new session_id.
});

// ============================================================
// Init
// ============================================================
initSpeechRecognition();
inputText.focus();
