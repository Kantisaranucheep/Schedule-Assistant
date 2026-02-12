import React, { useState, useMemo, useEffect } from "react";
import { RAINBOW, uniq } from "../utils";
import { EventMap, FilterCriteria } from "../types";

interface FilterBarProps {
    events: EventMap;
    onFilterChange: (filters: FilterCriteria) => void;
    onAddEvent: () => void;
}

export default function FilterBar({
    events,
    onFilterChange,
    onAddEvent,
}: FilterBarProps) {
    const [searchText, setSearchText] = useState("");
    const [filterOpen, setFilterOpen] = useState(false);
    const [kindFilter, setKindFilter] = useState<"all" | "event" | "task">("all");
    const [locationFilter, setLocationFilter] = useState("");
    const [fromDate, setFromDate] = useState<string>("");
    const [toDate, setToDate] = useState<string>("");
    const [selectedColors, setSelectedColors] = useState<string[]>([]);

    const allColors = useMemo(() => {
        const colors: string[] = [];
        Object.values(events).forEach((arr) =>
            arr.forEach((ev) => colors.push(ev.color))
        );
        return uniq(colors.length ? colors : RAINBOW);
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

    function toggleColor(c: string) {
        setSelectedColors((prev) =>
            prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
        );
    }

    function clearAllFilters() {
        setKindFilter("all");
        setSelectedColors([]);
        setFromDate("");
        setToDate("");
        setLocationFilter("");
        setSearchText("");
    }

    // Notify parent of filter changes
    useEffect(() => {
        onFilterChange({
            searchText,
            kindFilter,
            locationFilter,
            fromDate,
            toDate,
            selectedColors,
        });
    }, [searchText, kindFilter, locationFilter, fromDate, toDate, selectedColors, onFilterChange]);

    return (
        <div
            className="d-flex align-items-center justify-content-end gap-2"
            style={{ width: 340 }}
        >
            <div className="position-relative flex-grow-1">
                <input
                    className="form-control border border-secondary-subtle bg-light text-dark rounded-pill ps-4"
                    placeholder="Search events..."
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    style={{
                        fontSize: 13,
                        height: 36,
                        fontFamily: "var(--font-geist-sans)",
                    }}
                />
                <span className="position-absolute end-0 top-50 translate-middle-y me-3 text-secondary">
                    <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                </span>
            </div>

            <div className="position-relative">
                <button
                    className={`btn d-flex align-items-center justify-content-center p-0 position-relative shadow-sm transition-all ${filterOpen || activeFilterCount > 0
                        ? "btn-dark"
                        : "btn-light border border-secondary-subtle text-dark"
                        }`}
                    style={{ width: 36, height: 36, borderRadius: 10 }}
                    title="Filter"
                    onClick={() => setFilterOpen((v) => !v)}
                >
                    <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
                    </svg>
                    {activeFilterCount > 0 && (
                        <span
                            className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger border border-light p-1"
                            style={{ width: 8, height: 8 }}
                        >
                            {" "}
                        </span>
                    )}
                </button>

                {filterOpen && (
                    <div
                        className="position-absolute end-0 top-100 mt-2 p-4 bg-white rounded-4 shadow-xl border border-light-subtle z-3"
                        style={{ width: 320, fontFamily: "var(--font-geist-sans)" }}
                    >
                        <div className="d-flex align-items-center justify-content-between mb-4">
                            <div className="fw-bold small text-uppercase text-secondary letter-spacing-2">
                                Filters
                            </div>
                            {activeFilterCount > 0 && (
                                <span className="badge bg-primary bg-opacity-10 text-primary rounded-pill small">
                                    {activeFilterCount} Active
                                </span>
                            )}
                        </div>

                        <div className="mb-4">
                            <label className="small fw-bold text-dark mb-2 d-block">
                                Type
                            </label>
                            <div className="d-flex gap-2 p-1 bg-light rounded-pill border">
                                {(["all", "event", "task"] as const).map((k) => (
                                    <button
                                        key={k}
                                        className={`flex-grow-1 btn btn-sm rounded-pill fw-semibold small ${kindFilter === k
                                            ? "btn-white shadow-sm text-dark"
                                            : "text-muted border-0 hover-bg-gray"
                                            }`}
                                        onClick={() => setKindFilter(k)}
                                        type="button"
                                        style={{ transition: "all 0.2s", fontSize: 11 }}
                                    >
                                        {k === "all"
                                            ? "All"
                                            : k.charAt(0).toUpperCase() + k.slice(1)}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="mb-4">
                            <label className="small fw-bold text-dark mb-2 d-block">
                                Date Range
                            </label>
                            <div className="d-flex align-items-center gap-2">
                                <input
                                    type="date"
                                    className="form-control form-control-sm rounded-3 bg-light border-0"
                                    value={fromDate}
                                    onChange={(e) => setFromDate(e.target.value)}
                                    style={{ fontSize: 12 }}
                                />
                                <span className="text-muted small">to</span>
                                <input
                                    type="date"
                                    className="form-control form-control-sm rounded-3 bg-light border-0"
                                    value={toDate}
                                    onChange={(e) => setToDate(e.target.value)}
                                    style={{ fontSize: 12 }}
                                />
                            </div>
                        </div>

                        <div className="mb-4">
                            <label className="small fw-bold text-dark mb-2 d-block">
                                Location
                            </label>
                            <input
                                className="form-control form-control-sm rounded-3 bg-light border-0"
                                placeholder="Filter by location..."
                                value={locationFilter}
                                onChange={(e) => setLocationFilter(e.target.value)}
                                style={{ fontSize: 12 }}
                            />
                        </div>

                        <div className="mb-4">
                            <label className="small fw-bold text-dark mb-2 d-block">
                                Color Tag
                            </label>
                            <div className="d-flex gap-2 flex-wrap">
                                {allColors.map((c) => (
                                    <button
                                        key={c}
                                        type="button"
                                        className={`rounded-circle d-flex align-items-center justify-content-center transition-all ${selectedColors.includes(c)
                                            ? "ring-2 ring-offset-1"
                                            : "opacity-75 hover-opacity-100"
                                            }`}
                                        style={{
                                            width: 28,
                                            height: 28,
                                            background: c,
                                            cursor: "pointer",
                                            border: selectedColors.includes(c)
                                                ? `2px solid ${c}`
                                                : "2px solid transparent", // Fallback
                                            boxShadow: selectedColors.includes(c)
                                                ? "0 0 0 2px white, 0 0 0 4px #e5e7eb"
                                                : "none",
                                            transform: selectedColors.includes(c)
                                                ? "scale(1.1)"
                                                : "scale(1)",
                                        }}
                                        onClick={() => toggleColor(c)}
                                        title={c}
                                    >
                                        {selectedColors.includes(c) && (
                                            <svg
                                                width="14"
                                                height="14"
                                                viewBox="0 0 24 24"
                                                fill="none"
                                                stroke="white"
                                                strokeWidth="3"
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                            >
                                                <polyline points="20 6 9 17 4 12"></polyline>
                                            </svg>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="d-flex justify-content-end gap-2 pt-3 border-top border-light py-1">
                            <button
                                type="button"
                                className="btn btn-sm text-secondary hover-text-dark fw-medium"
                                onClick={clearAllFilters}
                            >
                                Reset
                            </button>
                            <button
                                type="button"
                                className="btn btn-sm btn-dark rounded-pill px-4 fw-bold shadow-sm"
                                onClick={() => setFilterOpen(false)}
                            >
                                Apply
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <div className="position-relative">
                <button
                    className="btn btn-light border border-secondary-subtle text-dark rounded-3 d-flex align-items-center justify-content-center p-0 shadow-sm"
                    style={{ width: 36, height: 36 }}
                    title="Add Event"
                    onClick={onAddEvent}
                >
                    <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                    >
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="16"></line>
                        <line x1="8" y1="12" x2="16" y2="12"></line>
                    </svg>
                </button>
            </div>
        </div>
    );
}
