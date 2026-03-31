"use client";

import { useState, useMemo } from "react";
import { EventMap, Kind } from "../types";
import { uniq } from "../utils";

export function useFilters(events: EventMap) {
  const [searchText, setSearchText] = useState("");
  const [filterOpen, setFilterOpen] = useState(false);
  const [kindFilter, setKindFilter] = useState<"all" | Kind>("all");
  const [locationFilter, setLocationFilter] = useState("");
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");
  const [selectedColors, setSelectedColors] = useState<string[]>([]);

  function toggleColor(c: string) {
    setSelectedColors((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    );
  }

  const allColors = useMemo(() => {
    const colors: string[] = [];
    Object.values(events).forEach((arr) =>
      arr.forEach((ev) => colors.push(ev.color))
    );
    return uniq(colors.length ? colors : []);
  }, [events]);

  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (searchText.trim()) n++;
    if (kindFilter !== "all") n++;
    if (fromDate) n++;
    if (toDate) n++;
    if (locationFilter.trim()) n++;
    if (selectedColors.length > 0) n++;
    return n;
  }, [searchText, kindFilter, fromDate, toDate, locationFilter, selectedColors]);

  const filteredEvents = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    const locQ = locationFilter.trim().toLowerCase();
    const from = fromDate || "0000-01-01";
    const to = toDate || "9999-12-31";

    const out: EventMap = {};

    Object.entries(events).forEach(([dateKey, arr]) => {
      if (dateKey < from || dateKey > to) return;

      const filteredArr = arr.filter((ev) => {
        if (kindFilter !== "all" && ev.kind !== kindFilter) return false;
        if (selectedColors.length > 0 && !selectedColors.includes(ev.color))
          return false;
        if (q && !ev.title.toLowerCase().includes(q)) return false;
        if (locQ && !(ev.location || "").toLowerCase().includes(locQ))
          return false;
        return true;
      });

      if (filteredArr.length > 0) out[dateKey] = filteredArr;
    });

    return out;
  }, [
    events,
    searchText,
    locationFilter,
    fromDate,
    toDate,
    kindFilter,
    selectedColors,
  ]);

  function clearAllFilters() {
    setKindFilter("all");
    setSelectedColors([]);
    setFromDate("");
    setToDate("");
    setLocationFilter("");
    setSearchText("");
  }

  return {
    searchText,
    setSearchText,
    filterOpen,
    setFilterOpen,
    kindFilter,
    setKindFilter,
    locationFilter,
    setLocationFilter,
    fromDate,
    setFromDate,
    toDate,
    setToDate,
    selectedColors,
    toggleColor,
    allColors,
    activeFilterCount,
    filteredEvents,
    clearAllFilters,
  };
}