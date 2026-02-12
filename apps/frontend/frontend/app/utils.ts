export const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];

export const RAINBOW = [
    "#ff3b30",
    "#ff9500",
    "#ffcc00",
    "#34c759",
    "#00c7be",
    "#007aff",
    "#af52de"
];

export function pad(n: number) { return String(n).padStart(2, "0"); }

export function keyOf(d: Date) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }

export function minutesToLabel(mins: number) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    const ap = h >= 12 ? "PM" : "AM";
    let hh = h % 12;
    if (hh === 0) hh = 12;
    return `${pad(hh)}:${pad(m)}${ap}`;
}

export function timeToMinutes(t: string) {
    const [hh, mm] = t.split(":").map(Number);
    return hh * 60 + mm;
}

export function parseISODate(iso: string) {
    const [y, mo, da] = iso.split("-").map(Number);
    return new Date(y, mo - 1, da);
}

export function prettyDow(d: Date) { return d.toLocaleDateString("en-US", { weekday: "long" }); }
export function prettyMonth(d: Date) { return d.toLocaleDateString("en-US", { month: "long" }); }

export function formatUpcomingDate(iso: string) {
    const [y, mo, d] = iso.split("-").map(Number);
    const dt = new Date(y, mo - 1, d);
    const dd = dt.getDate();
    const mname = monthNames[dt.getMonth()].slice(0, 3);
    return `${dd} ${mname} ${dt.getFullYear()}`;
}

export function nowTimeHHMM() {
    const now = new Date();
    return `${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

export function roundUpTimeHHMM(hhmm: string, stepMin = 5) {
    const [h, m] = hhmm.split(":").map(Number);
    let total = h * 60 + m;
    total = Math.ceil(total / stepMin) * stepMin;
    if (total > 23 * 60 + 59) total = 23 * 60 + 59;
    const hh = Math.floor(total / 60);
    const mm = total % 60;
    return `${pad(hh)}:${pad(mm)}`;
}

export function uniq(arr: string[]) {
    return Array.from(new Set(arr));
}

export function addDaysISO(iso: string, delta: number) {
    const d = parseISODate(iso);
    d.setDate(d.getDate() + delta);
    return keyOf(d);
}

export function dayHeaderLabel(iso: string) {
    const d = parseISODate(iso);
    const dd = d.getDate();
    const m = monthNames[d.getMonth()].toUpperCase();
    const y = d.getFullYear();
    return `${dd} ${m} ${y}`;
}

/** Very simple tokenizer placeholder */
export function tokenize(text: string): string[] {
    return text
        .trim()
        .split(/[\s]+|(?=[,.!?;:(){}\[\]])|(?<=[,.!?;:(){}\[\]])/g)
        .map(t => t.trim())
        .filter(Boolean);
}

export function uid(prefix = "id") {
    return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now()}`;
}

export function clamp(n: number, a: number, b: number) { return Math.max(a, Math.min(b, n)); }
