import { Ev } from "../types";

export interface EventPortion {
  hour: number;
  start: number; // minutes within hour (0-60)
  end: number; // minutes within hour (0-60)
  event: Ev;
}

export function splitEventByHours(ev: Ev): EventPortion[] {
  const startTotal = ev.startMin ?? 0;
  const endTotal = ev.endMin ?? 0;
  const portions: EventPortion[] = [];

  const startHour = Math.floor(startTotal / 60);
  const endHour = Math.floor(endTotal / 60);

  for (let h = startHour; h <= endHour; h++) {
    if (h < 0 || h > 23) continue;
    const hStart = h * 60;
    const hEnd = (h + 1) * 60;

    const pStart = Math.max(startTotal, hStart);
    const pEnd = Math.min(endTotal, hEnd);

    if (pStart < pEnd) {
      portions.push({
        hour: h,
        start: pStart - hStart,
        end: pEnd - hStart,
        event: ev,
      });
    }
  }
  return portions;
}