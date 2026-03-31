export function minutesToLabel(mins: number) {
  let h = Math.floor(mins / 60);
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

function pad(n: number) { return String(n).padStart(2, "0"); }