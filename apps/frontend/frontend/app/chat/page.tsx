"use client";

import React, { useState, useEffect } from "react";
import { ChatContainer } from "../components/chat";
import { getChatHealth, ChatHealthResponse } from "../services/chat-agent.api";
import Link from "next/link";

export default function ChatPage() {
  const [health, setHealth] = useState<ChatHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  // Check health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const healthData = await getChatHealth();
        setHealth(healthData);
      } catch {
        setHealth({
          status: "unhealthy",
          components: {
            llm: { status: "unhealthy", available: false },
            prolog: { status: "unhealthy", available: false },
          },
        });
      } finally {
        setHealthLoading(false);
      }
    };

    checkHealth();
  }, []);

  return (
    <div className="min-vh-100" style={{ background: "linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)" }}>
      {/* Navigation */}
      <nav className="navbar navbar-light bg-white shadow-sm border-bottom">
        <div className="container">
          <Link href="/" className="text-decoration-none d-flex align-items-center gap-2 text-secondary">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
                clipRule="evenodd"
              />
            </svg>
            <span>Back to Calendar</span>
          </Link>

          <div className="d-flex align-items-center gap-2">
            <span className="text-muted small">System Status:</span>
            {healthLoading ? (
              <span className="text-muted small">Checking...</span>
            ) : (
              <span
                className={`badge rounded-pill d-flex align-items-center gap-1 ${
                  health?.status === "healthy"
                    ? "bg-success"
                    : health?.status === "degraded"
                    ? "bg-warning text-dark"
                    : "bg-danger"
                }`}
              >
                <span
                  className="rounded-circle"
                  style={{
                    width: "8px",
                    height: "8px",
                    backgroundColor: health?.status === "healthy"
                      ? "#28a745"
                      : health?.status === "degraded"
                      ? "#ffc107"
                      : "#dc3545",
                  }}
                />
                {health?.status === "healthy"
                  ? "All Systems Operational"
                  : health?.status === "degraded"
                  ? "Degraded (Prolog fallback)"
                  : "Service Unavailable"}
              </span>
            )}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="container py-4">
        {/* Title section */}
        <div className="text-center mb-4">
          <h1 className="h2 fw-bold text-dark">AI Schedule Assistant</h1>
          <p className="text-muted">
            Chat naturally to manage your calendar. Add events, check your
            schedule, and resolve conflicts with AI help.
          </p>
        </div>

        {/* Health warning */}
        {health?.status === "unhealthy" && (
          <div className="alert alert-danger d-flex align-items-start mb-4" role="alert">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="flex-shrink-0 me-2"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <h6 className="alert-heading mb-1">Service Unavailable</h6>
              <p className="mb-0 small">
                The AI service (Ollama) is not available. Please make sure
                Ollama is running with the llama3.2 model.
              </p>
            </div>
          </div>
        )}

        {/* Chat container */}
        <div style={{ height: "calc(100vh - 320px)", minHeight: "500px" }}>
          <ChatContainer />
        </div>

        {/* Tips section */}
        <div className="row g-3 mt-3">
          <div className="col-md-4">
            <div className="card h-100 shadow-sm border-0">
              <div className="card-body">
                <div className="text-primary mb-2">
                  <svg
                    width="24"
                    height="24"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                    />
                  </svg>
                </div>
                <h6 className="card-title fw-semibold">Add Events</h6>
                <p className="card-text text-muted small mb-0">
                  &quot;Schedule a meeting tomorrow at 2pm&quot;
                </p>
              </div>
            </div>
          </div>

          <div className="col-md-4">
            <div className="card h-100 shadow-sm border-0">
              <div className="card-body">
                <div className="text-success mb-2">
                  <svg
                    width="24"
                    height="24"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                </div>
                <h6 className="card-title fw-semibold">Check Schedule</h6>
                <p className="card-text text-muted small mb-0">
                  &quot;What do I have this week?&quot;
                </p>
              </div>
            </div>
          </div>

          <div className="col-md-4">
            <div className="card h-100 shadow-sm border-0">
              <div className="card-body">
                <div className="text-purple mb-2" style={{ color: "#6f42c1" }}>
                  <svg
                    width="24"
                    height="24"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                </div>
                <h6 className="card-title fw-semibold">Resolve Conflicts</h6>
                <p className="card-text text-muted small mb-0">
                  AI helps find free time slots
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
