"use client";

import { useState, useMemo, useEffect } from "react";
import { Kind } from "../types";
import { RAINBOW, keyOf, parseISODate, prettyDow, prettyMonth, nowTimeHHMM, roundUpTimeHHMM } from "../utils";

export function useEventModal() {
  const [open, setOpen] = useState(false);
  const [modalKind, setModalKind] = useState<Kind>("event");
  const [mTitle, setMTitle] = useState("");
  const [mDate, setMDate] = useState<string>(keyOf(new Date()));
  const [mStart, setMStart] = useState("09:00");
  const [mEnd, setMEnd] = useState("09:00");
  const [mAllDay, setMAllDay] = useState(false);
  const [mLocation, setMLocation] = useState("");
  const [mNotes, setMNotes] = useState("");
  const [mColor, setMColor] = useState<string>(RAINBOW[1]);

  const realTodayKey = useMemo(() => keyOf(new Date()), []);
  const isTodaySelected = mDate === realTodayKey;

  // Time rules: no past time if today
  const minStart = useMemo(() => {
    if (!isTodaySelected || mAllDay) return "";
    return roundUpTimeHHMM(nowTimeHHMM(), 5);
  }, [isTodaySelected, mAllDay]);

  useEffect(() => {
    if (mAllDay) return;

    if (isTodaySelected) {
      const ms = roundUpTimeHHMM(nowTimeHHMM(), 5);
      if (mStart < ms) setMStart(ms);
      if (mEnd < ms) setMEnd(ms);
      if (mEnd < mStart) setMEnd(mStart);
    } else {
      if (mEnd < mStart) setMEnd(mStart);
    }
  }, [isTodaySelected, mAllDay, mStart, mEnd]);

  function openModal() {
    setModalKind("event");
    setMTitle("");
    setMDate(realTodayKey);
    setMStart("09:00");
    setMEnd("09:00");
    setMAllDay(false);
    setMLocation("");
    setMNotes("");
    setMColor(RAINBOW[1]);
    setOpen(true);
  }

  const prettyDate = useMemo(() => {
    const dt = parseISODate(mDate);
    return `${prettyDow(dt)}, ${dt.getDate()} ${prettyMonth(dt)}`;
  }, [mDate]);

  return {
    open,
    setOpen,
    modalKind,
    setModalKind,
    mTitle,
    setMTitle,
    mDate,
    setMDate,
    mStart,
    setMStart,
    mEnd,
    setMEnd,
    mAllDay,
    setMAllDay,
    mLocation,
    setMLocation,
    mNotes,
    setMNotes,
    mColor,
    setMColor,
    minStart,
    openModal,
    prettyDate,
    realTodayKey,
    isTodaySelected,
  };
}