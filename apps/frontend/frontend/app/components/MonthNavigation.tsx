import React from "react";

interface MonthNavigationProps {
    onPrev: () => void;
    onNext: () => void;
    title: string;
}

export default function MonthNavigation({ onPrev, onNext, title }: MonthNavigationProps) {
    return (
        <div className="d-flex align-items-center gap-3">
            <button
                className="btn btn-link text-dark text-decoration-none p-0 fw-bold fs-4"
                onClick={onPrev}
            >
                &lt;
            </button>
            <div className="text-uppercase fw-bold fs-4 ls-1">{title}</div>
            <button
                className="btn btn-link text-dark text-decoration-none p-0 fw-bold fs-4"
                onClick={onNext}
            >
                &gt;
            </button>
        </div>
    );
}
