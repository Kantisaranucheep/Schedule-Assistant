"use client";

import React, { useState, useEffect } from "react";
import { ChatContainer } from "../components/chat";
import PersonaSettings from "../components/PersonaSettings";
import { getChatHealth, ChatHealthResponse } from "../services/chat-agent.api";
import Link from "next/link";

export default function ChatPage() {
  const [health, setHealth] = useState<ChatHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [showPersonaModal, setShowPersonaModal] = useState(false);

  // Read user ID from localStorage session
  const [userId, setUserId] = useState<string | undefined>(undefined);
  const [calendarId, setCalendarId] = useState<string | undefined>(undefined);

  useEffect(() => {
    try {
      const sessionItem = localStorage.getItem("scheduler_auth_session");
      if (sessionItem) {
        const sessionData = JSON.parse(sessionItem);
        if (sessionData.user_id) setUserId(sessionData.user_id);
        if (sessionData.calendar_id) setCalendarId(sessionData.calendar_id);
      }
    } catch (e) {
      console.error("Error reading session", e);
    }
  }, []);

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
    <div className="min-vh-100" style={{ backgroundColor: "#fbfcfd" }}>
      {/* Persona Modal */}
      {showPersonaModal && (
        <div 
          className="modal d-block" 
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowPersonaModal(false);
          }}
        >
          <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
            <div className="modal-content border-0 rounded-4 shadow-lg">
              <div className="modal-body p-4" style={{ maxHeight: "80vh", overflowY: "auto" }}>
                <PersonaSettings 
                  isModal={true} 
                  onClose={() => setShowPersonaModal(false)} 
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="navbar navbar-light sticky-top" style={{ backgroundColor: "rgba(255, 255, 255, 0.8)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(0,0,0,0.05)" }}>
        <div className="container">
          <Link href="/" className="text-decoration-none d-flex align-items-center gap-2 text-dark hover-lift transition-all">
            <div className="p-2 rounded-circle bg-white border shadow-sm d-flex align-items-center justify-content-center text-primary" style={{ width: 36, height: 36 }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="19" y1="12" x2="5" y2="12"></line>
                <polyline points="12 19 5 12 12 5"></polyline>
              </svg>
            </div>
            <span className="small fw-bold text-uppercase letter-spacing-2" style={{ color: "#495057" }}>Back to Calendar</span>
          </Link>

          <div className="d-flex align-items-center gap-3">
            {/* Persona Settings Button */}
            <button
              onClick={() => setShowPersonaModal(true)}
              className="btn btn-outline-primary rounded-pill d-flex align-items-center gap-2 px-3 py-2"
              style={{ fontSize: "12px" }}
              title="Set up your persona for personalized priorities"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              <span className="fw-bold">MY PERSONA</span>
            </button>

            <div className="d-flex align-items-center gap-2">
              <span className="text-muted" style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.5px" }}>STATUS:</span>
              {healthLoading ? (
                <span className="text-muted small">...</span>
              ) : (
                <span className={`badge rounded-pill d-flex align-items-center gap-2 px-3 py-2 ${
                    health?.status === "healthy" ? "bg-success bg-opacity-10 text-success border border-success border-opacity-10" : "bg-danger bg-opacity-10 text-danger border border-danger border-opacity-10"
                  }`} style={{ fontSize: "11px" }}>
                  <span className="rounded-circle" style={{ width: "6px", height: "6px", backgroundColor: "currentColor" }} />
                  {health?.status === "healthy" ? "SYSTEMS OPERATIONAL" : "SERVICE UNAVAILABLE"}
                </span>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="container py-5">
        {/* Title section */}
        <div className="text-center mb-5">
          <div className="d-inline-flex align-items-center justify-content-center bg-primary bg-opacity-10 rounded-4 p-3 mb-3 text-primary">
            <svg viewBox="0 0 512 512" fill="currentColor" width="32" height="32">
                <title>ai</title>
                <g id="Page-1" stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
                    <g id="icon" fill="currentColor" transform="translate(64.000000, 64.000000)">
                        <path d="M320,64 L320,320 L64,320 L64,64 L320,64 Z M171.749388,128 L146.817842,128 L99.4840387,256 L121.976629,256 L130.913039,230.977 L187.575039,230.977 L196.319607,256 L220.167172,256 L171.749388,128 Z M260.093778,128 L237.691519,128 L237.691519,256 L260.093778,256 L260.093778,128 Z M159.094727,149.47526 L181.409039,213.333 L137.135039,213.333 L159.094727,149.47526 Z M341.333333,256 L384,256 L384,298.666667 L341.333333,298.666667 L341.333333,256 Z M85.3333333,341.333333 L128,341.333333 L128,384 L85.3333333,384 L85.3333333,341.333333 Z M170.666667,341.333333 L213.333333,341.333333 L213.333333,384 L170.666667,384 L170.666667,341.333333 Z M85.3333333,0 L128,0 L128,42.6666667 L85.3333333,42.6666667 L85.3333333,0 Z M256,341.333333 L298.666667,341.333333 L298.666667,384 L256,384 L256,341.333333 Z M170.666667,0 L213.333333,0 L213.333333,42.6666667 L170.666667,42.6666667 L170.666667,0 Z M256,0 L298.666667,0 L298.666667,42.6666667 L256,42.6666667 L256,0 Z M341.333333,170.666667 L384,170.666667 L384,213.333333 L341.333333,213.333333 L341.333333,170.666667 Z M0,256 L42.6666667,256 L42.6666667,298.666667 L0,298.666667 L0,256 Z M341.333333,85.3333333 L384,85.3333333 L384,128 L341.333333,128 L341.333333,85.3333333 Z M0,170.666667 L42.6666667,170.666667 L42.6666667,213.333333 L0,213.333333 L0,170.666667 Z M0,85.3333333 L42.6666667,85.3333333 L42.6666667,128 L0,128 L0,85.3333333 Z" id="Combined-Shape" />
                    </g>
                </g>
            </svg>
          </div>
          <h1 className="h2 fw-bold text-dark mb-1">AI Schedule Assistant</h1>
          <p className="text-secondary opacity-75 mx-auto" style={{ maxWidth: 500 }}>
            Chat naturally to manage your calendar. Add events, check your schedule, and resolve conflicts with AI help.
          </p>
        </div>

        {/* Health warning */}
        {health?.status === "unhealthy" && (
          <div className="alert alert-danger border-0 shadow-sm rounded-4 d-flex align-items-center mb-5 p-3" role="alert">
            <div className="bg-danger bg-opacity-10 p-2 rounded-3 me-3 text-danger">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h6 className="alert-heading mb-0 fw-bold">Service Unavailable</h6>
              <p className="mb-0 small opacity-75">The AI service (Ollama) is not available. Please ensure Ollama is running.</p>
            </div>
          </div>
        )}

        {/* Chat container */}
        <div style={{ height: "calc(100vh - 380px)", minHeight: "550px" }} className="mb-5 shadow-sm rounded-4 overflow-hidden border">
          <ChatContainer calendarId={calendarId} userId={userId} />
        </div>

        {/* Tips section */}
        <div className="row g-4 mt-2">
          {[
            {
              title: "Add Events",
              text: '"Schedule a meeting tomorrow at 2pm"',
              icon: "M12 6v6m0 0v6m0-6h6m-6 0H6",
              color: "#0d6efd",
              bg: "rgba(13, 110, 253, 0.08)"
            },
            {
              title: "Check Schedule",
              text: '"What do I have this week?"',
              icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
              color: "#198754",
              bg: "rgba(25, 135, 84, 0.08)"
            },
            {
              title: "Resolve Conflicts",
              text: "AI helps find free time slots",
              icon: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
              color: "#6f42c1",
              bg: "rgba(111, 66, 193, 0.08)"
            },
            {
              title: "Set Priorities",
              text: "Tell us about yourself for smarter scheduling",
              icon: "M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z",
              color: "#fd7e14",
              bg: "rgba(253, 126, 20, 0.08)"
            }
          ].map((card, idx) => (
            <div className="col-md-3" key={idx}>
              <div className="card h-100 border-0 shadow-sm rounded-4 p-2 transition-all hover-lift">
                <div className="card-body d-flex flex-column align-items-center text-center">
                  <div className="rounded-circle d-flex align-items-center justify-content-center mb-3" style={{ width: 48, height: 48, backgroundColor: card.bg, color: card.color }}>
                    <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={card.icon} />
                    </svg>
                  </div>
                  <h6 className="card-title fw-bold text-dark">{card.title}</h6>
                  <p className="card-text text-secondary small mb-0">{card.text}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>

      <style jsx>{`
        .letter-spacing-1 { letter-spacing: 1px; }
        .letter-spacing-2 { letter-spacing: 2px; }
        .hover-lift:hover { transform: translateY(-5px); transition: transform 0.2s ease; }
        .hover-opacity-75:hover { opacity: 0.75; }
      `}</style>
    </div>
  );
}
