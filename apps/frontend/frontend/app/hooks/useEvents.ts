"use client";

import { useState } from "react";
import { EventMap, Ev, Kind } from "../types";
import { RAINBOW, timeToMinutes, nowTimeHHMM, roundUpTimeHHMM } from "../utils";
import { initialEvents } from "../data/initialEvents";

export function useEvents() {
  const [events, setEvents] = useState<EventMap>(initialEvents);
  const [nextId, setNextId] = useState(100);

  function addEvent(
    modalKind: Kind,
    mTitle: string,
    mDate: string,
    mStart: string,
    mEnd: string,
    mAllDay: boolean,
    mColor: string,
    mLocation: string,
    mNotes: string,
    realTodayKey: string,
    isTodaySelected: boolean
  ) {
    const title = mTitle.trim();
    if (!title) return { success: false, error: "Title is required" };

    if (mDate < realTodayKey) {
      return { success: false, error: "You cannot choose a past date." };
    }

    let startMinVal = 0;
    let endMinVal = 0;

    if (!mAllDay) {
      if (isTodaySelected) {
        const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
        if (mStart < ms) {
          return { success: false, error: "Start time cannot be in the past." };
        }
      }
      startMinVal = timeToMinutes(mStart);
      endMinVal = timeToMinutes(mEnd);

      if (endMinVal < startMinVal) {
        return { success: false, error: "End time cannot be earlier than start time." };
      }

      if (endMinVal - startMinVal < 5) {
        return { success: false, error: "Event duration must be at least 5 minutes." };
      }

      // Conflict Check
      const existingOnDay = events[mDate] || [];
      const conflict = existingOnDay.find(ex => {
        if (ex.allDay) return false;
        return (startMinVal < (ex.endMin ?? 0)) && (endMinVal > (ex.startMin ?? 0));
      });

      if (conflict) {
        return { success: false, error: `Time conflict! You cannot have multiple tasks at the same time (overlaps with "${conflict.title}").` };
      }
    }

    const newItem: Ev = {
      id: nextId,
      kind: modalKind,
      allDay: mAllDay,
      startMin: startMinVal,
      endMin: endMinVal,
      title,
      color: mColor || RAINBOW[1],
      location: mLocation.trim(),
      notes: mNotes.trim(),
    };

    setNextId((x) => x + 1);

    setEvents((prev) => {
      const next: EventMap = { ...prev };
      const arr = next[mDate] ? [...next[mDate]] : [];
      arr.push(newItem);
      arr.sort((a, b) => (a.startMin ?? 0) - (b.startMin ?? 0));
      next[mDate] = arr;
      return next;
    });

    return { success: true };
  }

  return { events, addEvent };
}