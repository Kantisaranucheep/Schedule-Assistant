export function pad(n: number) { return String(n).padStart(2, "0"); }

export function keyOf(d: Date) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }

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

export const monthNames = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];