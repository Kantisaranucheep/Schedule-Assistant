import React from "react";

interface HotkeysModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function HotkeysModal({ isOpen, onClose }: HotkeysModalProps) {
    return (
        <div
            className={`position-fixed inset-0 z-3 p-4 d-flex align-items-center justify-content-center ${isOpen ? "" : "d-none"
                }`}
            style={{
                backgroundColor: "rgba(0,0,0,.5)",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
            }}
            aria-hidden={!isOpen}
        >
            <div
                className="bg-dark bg-opacity-75 text-white rounded-4 shadow-lg border border-start-0 border-top-0 border-end-0 border-bottom-0 border-secondary overflow-hidden position-relative"
                style={{
                    width: "min(920px, 94vw)",
                    height: "min(520px, 82vh)",
                    backdropFilter: "blur(10px)",
                }}
            >
                <div className="d-flex align-items-center justify-content-between p-3">
                    <div className="small fw-bold text-uppercase letter-spacing-2 text-white-50">
                        HotKeys
                    </div>
                    <button
                        type="button"
                        className="btn btn-sm btn-outline-light rounded-3"
                        onClick={onClose}
                        aria-label="Close HotKeys"
                    >
                        ×
                    </button>
                </div>

                <div
                    className="d-grid align-items-center justify-items-center h-100 p-4"
                    style={{
                        gridTemplateColumns: "1fr 280px 1fr",
                        gridTemplateRows: "1fr 140px 1fr 1fr",
                        gridTemplateAreas: `". top ." "leftTop core rightTop" "leftBottom core rightBottom" ". bottom ."`,
                    }}
                >
                    {/* center = CLOSE */}
                    <button
                        type="button"
                        className="rounded-circle bg-white border-0 shadow-lg d-flex align-items-center justify-content-center"
                        style={{
                            gridArea: "core",
                            width: 130,
                            height: 130,
                            cursor: "pointer",
                        }}
                        onClick={onClose}
                        aria-label="Close HotKeys"
                        title="Close"
                    >
                        <span className="h1 mb-0">×</span>
                    </button>

                    <button
                        type="button"
                        className="btn btn-light rounded-pill shadow fw-bold p-3"
                        style={{ gridArea: "top", width: "min(320px, 90%)" }}
                    >
                        Placeholder
                    </button>
                    <button
                        type="button"
                        className="btn btn-light rounded-pill shadow fw-bold p-3"
                        style={{ gridArea: "leftTop", width: "min(320px, 90%)" }}
                    >
                        Placeholder
                    </button>
                    <button
                        type="button"
                        className="btn btn-light rounded-pill shadow fw-bold p-3"
                        style={{ gridArea: "rightTop", width: "min(320px, 90%)" }}
                    >
                        Placeholder
                    </button>
                    <button
                        type="button"
                        className="btn btn-light rounded-pill shadow fw-bold p-3"
                        style={{ gridArea: "leftBottom", width: "min(320px, 90%)" }}
                    >
                        Placeholder
                    </button>
                    <button
                        type="button"
                        className="btn btn-light rounded-pill shadow fw-bold p-3"
                        style={{ gridArea: "rightBottom", width: "min(320px, 90%)" }}
                    >
                        Placeholder
                    </button>
                    <button
                        type="button"
                        className="btn btn-light rounded-pill shadow fw-bold p-3 align-self-start mt-2"
                        style={{ gridArea: "bottom", width: "min(320px, 90%)" }}
                    >
                        Placeholder
                    </button>
                </div>
            </div>
        </div>
    );
}
