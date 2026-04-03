import React, { useState, useMemo, useEffect } from "react";
import { EventMap, FilterCriteria, EventCategory } from "../types";

interface FilterBarProps {
    events: EventMap;
    categories: EventCategory[];
    onFilterChange: (filters: FilterCriteria) => void;
    onAddEvent: () => void;
}

export default function FilterBar({
    events,
    categories,
    onFilterChange,
    onAddEvent,
}: FilterBarProps) {
    const [searchText, setSearchText] = useState("");
    const [filterOpen, setFilterOpen] = useState(false);
    const [kindFilter, setKindFilter] = useState<"all" | "event" | "task">("all");
    const [locationFilter, setLocationFilter] = useState("");
    const [fromDate, setFromDate] = useState<string>("");
    const [toDate, setToDate] = useState<string>("");
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

    const activeFilterCount = useMemo(() => {
        let n = 0;
        if (searchText.trim()) n++;
        if (kindFilter !== "all") n++;
        if (fromDate) n++;
        if (toDate) n++;
        if (locationFilter.trim()) n++;
        if (selectedCategories.length > 0) n++;
        return n;
    }, [searchText, kindFilter, fromDate, toDate, locationFilter, selectedCategories]);

    function toggleCategory(catId: string) {
        setSelectedCategories((prev) =>
            prev.includes(catId) ? prev.filter((x) => x !== catId) : [...prev, catId]
        );
    }

    function clearAllFilters() {
        setKindFilter("all");
        setSelectedCategories([]);
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
            selectedCategories,
        });
    }, [searchText, kindFilter, locationFilter, fromDate, toDate, selectedCategories, onFilterChange]);

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
                                Categories
                            </label>
                            <div className="d-flex gap-2 flex-wrap">
                                {categories.map((cat) => (
                                    <button
                                        key={cat.id}
                                        type="button"
                                        className={`btn btn-sm rounded-pill d-flex align-items-center gap-2 transition-all ${selectedCategories.includes(cat.id)
                                            ? "shadow-sm border-0"
                                            : "opacity-75 hover-opacity-100 border bg-light text-secondary"
                                            }`}
                                        style={{
                                            fontSize: 11,
                                            fontWeight: 600,
                                            backgroundColor: selectedCategories.includes(cat.id) ? `${cat.color}20` : undefined,
                                            color: selectedCategories.includes(cat.id) ? cat.color : undefined,
                                            borderColor: selectedCategories.includes(cat.id) ? cat.color : undefined
                                        }}
                                        onClick={() => toggleCategory(cat.id)}
                                        title={cat.name}
                                    >
                                        <div
                                            className="rounded-circle"
                                            style={{
                                                width: 10,
                                                height: 10,
                                                backgroundColor: cat.color,
                                            }}
                                        />
                                        {cat.name}
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
