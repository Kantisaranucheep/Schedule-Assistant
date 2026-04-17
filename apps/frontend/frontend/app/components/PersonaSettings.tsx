"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  getUserProfile,
  saveUserStory,
  updatePriorities,
  updateStrategy,
  UserProfileResponse,
  PriorityExtractionResponse,
  PriorityConfig,
  getPriorityLabel,
  getPriorityColor,
  STRATEGY_DESCRIPTIONS,
  EVENT_TYPE_LABELS,
} from "../services/user-profile.api";

interface PersonaSettingsProps {
  userId?: string;
  onClose?: () => void;
  isModal?: boolean;
}

function getSessionUserId(): string | null {
  try {
    const sessionItem = localStorage.getItem("scheduler_auth_session");
    if (sessionItem) {
      const sessionData = JSON.parse(sessionItem);
      return sessionData.user_id || null;
    }
  } catch (e) {
    console.error("Error reading session", e);
  }
  return null;
}

export default function PersonaSettings({ 
  userId, 
  onClose,
  isModal = false 
}: PersonaSettingsProps) {
  const resolvedUserId = userId || getSessionUserId();

  if (!resolvedUserId) {
    return (
      <div className="d-flex align-items-center justify-content-center p-5">
        <p className="text-muted">Please log in to manage your persona.</p>
      </div>
    );
  }
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [userStory, setUserStory] = useState("");
  const [extraction, setExtraction] = useState<PriorityExtractionResponse | null>(null);
  const [editedPriorities, setEditedPriorities] = useState<PriorityConfig>({});
  const [selectedStrategy, setSelectedStrategy] = useState<string>("balanced");
  const [showPriorityEditor, setShowPriorityEditor] = useState(false);
  const [activeTab, setActiveTab] = useState<"story" | "priorities" | "strategy">("story");

  // Load user profile on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const data = await getUserProfile(resolvedUserId);
        setProfile(data);
        setUserStory(data.user_story || "");
        setEditedPriorities(data.merged_priorities || {});
        setSelectedStrategy(data.scheduling_strategy || "balanced");
      } catch (err) {
        console.error("Failed to load profile:", err);
        // Profile might not exist yet, that's OK
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, [resolvedUserId]);

  const handleSaveStory = useCallback(async () => {
    if (!userStory.trim() || userStory.length < 10) {
      setError("Please write at least 10 characters describing yourself.");
      return;
    }

    setSaving(true);
    setError(null);
    setExtraction(null);

    try {
      const response = await saveUserStory(resolvedUserId, {
        user_story: userStory,
        extract_priorities: true,
      });

      setProfile(response.profile);
      setEditedPriorities(response.profile.merged_priorities || {});
      setSelectedStrategy(response.profile.scheduling_strategy || "balanced");

      if (response.extraction) {
        setExtraction(response.extraction);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save story");
    } finally {
      setSaving(false);
    }
  }, [userStory, resolvedUserId]);

  const handleSavePriorities = useCallback(async () => {
    setSaving(true);
    setError(null);

    try {
      const response = await updatePriorities(resolvedUserId, {
        priorities: editedPriorities,
        strategy: selectedStrategy,
      });

      setProfile(response);
      setShowPriorityEditor(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update priorities");
    } finally {
      setSaving(false);
    }
  }, [editedPriorities, selectedStrategy, resolvedUserId]);

  const handleStrategyChange = useCallback(async (strategy: string) => {
    setSelectedStrategy(strategy);
    
    if (profile) {
      try {
        const response = await updateStrategy(resolvedUserId, {
          strategy: strategy as "minimize_moves" | "maximize_quality" | "balanced",
        });
        setProfile(response);
      } catch (err) {
        console.error("Failed to update strategy:", err);
      }
    }
  }, [profile, resolvedUserId]);

  const handlePriorityChange = (eventType: string, value: number) => {
    setEditedPriorities(prev => ({
      ...prev,
      [eventType]: Math.max(1, Math.min(10, value)),
    }));
  };

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center p-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  const containerClass = isModal ? "" : "container py-4";

  return (
    <div className={containerClass}>
      {/* Header */}
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h4 className="fw-bold mb-1 d-flex align-items-center gap-2">
            <div className="bg-primary bg-opacity-10 rounded-circle d-flex align-items-center justify-content-center text-primary" style={{ width: 36, height: 36 }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </div>
            Your Persona
          </h4>
          <p className="text-muted small mb-0">
            Tell us about yourself to personalize event priorities
          </p>
        </div>
        {onClose && (
          <button className="btn btn-outline-secondary rounded-circle d-flex align-items-center justify-content-center" onClick={onClose} style={{ width: 36, height: 36, padding: 0 }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert alert-danger border-0 rounded-3 mb-4" role="alert">
          <div className="d-flex align-items-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 20 20" className="me-2">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <small>{error}</small>
            <button className="btn-close ms-auto" onClick={() => setError(null)}></button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <ul className="nav nav-pills nav-fill mb-4 bg-light rounded-3 p-1">
        <li className="nav-item">
          <button
            className={`nav-link rounded-3 ${activeTab === "story" ? "active" : ""}`}
            onClick={() => setActiveTab("story")}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" className="me-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
            Your Story
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link rounded-3 ${activeTab === "priorities" ? "active" : ""}`}
            onClick={() => setActiveTab("priorities")}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" className="me-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
              <line x1="3" y1="6" x2="3.01" y2="6"></line>
              <line x1="3" y1="12" x2="3.01" y2="12"></line>
              <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
            Priorities
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link rounded-3 ${activeTab === "strategy" ? "active" : ""}`}
            onClick={() => setActiveTab("strategy")}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" className="me-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            Strategy
          </button>
        </li>
      </ul>

      {/* Tab Content */}
      {activeTab === "story" && (
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-4">
            <h6 className="fw-bold mb-2">Tell us about yourself</h6>
            <p className="text-muted small mb-3">
              Describe your role, responsibilities, and what matters most to you. 
              Our AI will analyze this to set appropriate priority weights.
            </p>
            <textarea
              className="form-control border-2 rounded-3 mb-3"
              rows={6}
              placeholder="Example: I'm a third year software engineering student at KMITL. My top priority is graduating on time and finding a good internship. I have regular classes, team project meetings, and I'm preparing for technical interviews. I also try to exercise 3 times a week..."
              value={userStory}
              onChange={(e) => setUserStory(e.target.value)}
              style={{ resize: "none" }}
            />
            <div className="d-flex justify-content-between align-items-center">
              <small className="text-muted">{userStory.length} characters (min 10)</small>
              <button
                className="btn btn-primary rounded-pill px-4"
                onClick={handleSaveStory}
                disabled={saving || userStory.length < 10}
              >
                {saving ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                    Analyzing...
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" className="me-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                      <polyline points="7 10 12 15 17 10"></polyline>
                      <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Analyze & Save
                  </>
                )}
              </button>
            </div>

            {/* Extraction Results */}
            {extraction && (
              <div className="mt-4 pt-4 border-top">
                <h6 className="fw-bold mb-3 d-flex align-items-center gap-2">
                  <span className="badge bg-success">AI Analysis</span>
                </h6>
                {extraction.persona_summary && (
                  <div className="alert alert-primary border-0 rounded-3 mb-3">
                    <strong className="d-block mb-1">Summary</strong>
                    <small>{extraction.persona_summary}</small>
                  </div>
                )}
                {extraction.reasoning && (
                  <div className="alert alert-light border rounded-3">
                    <strong className="d-block mb-1">Reasoning</strong>
                    <small className="text-muted">{extraction.reasoning}</small>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "priorities" && (
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <div>
                <h6 className="fw-bold mb-1">Priority Weights</h6>
                <small className="text-muted">1 = lowest priority, 10 = highest priority</small>
              </div>
              <button
                className={`btn ${showPriorityEditor ? "btn-secondary" : "btn-outline-primary"} rounded-pill btn-sm`}
                onClick={() => setShowPriorityEditor(!showPriorityEditor)}
              >
                {showPriorityEditor ? "Cancel" : "Edit"}
              </button>
            </div>

            <div className="row g-2">
              {Object.entries(profile?.merged_priorities || editedPriorities).map(([eventType, priority]) => (
                <div key={eventType} className="col-6">
                  <div className="d-flex align-items-center justify-content-between p-2 bg-light rounded-3">
                    <div className="d-flex align-items-center gap-2">
                      <div
                        className="rounded-circle flex-shrink-0"
                        style={{
                          width: 10,
                          height: 10,
                          backgroundColor: getPriorityColor(priority as number),
                        }}
                      />
                      <small className="fw-medium text-truncate" style={{ maxWidth: 100 }}>
                        {EVENT_TYPE_LABELS[eventType] || eventType}
                      </small>
                    </div>
                    {showPriorityEditor ? (
                      <input
                        type="number"
                        className="form-control form-control-sm"
                        style={{ width: 50 }}
                        min={1}
                        max={10}
                        value={editedPriorities[eventType] || priority}
                        onChange={(e) => handlePriorityChange(eventType, parseInt(e.target.value) || 5)}
                      />
                    ) : (
                      <small className="badge rounded-pill text-white" style={{ backgroundColor: getPriorityColor(priority as number), fontSize: "10px" }}>
                        {priority}
                      </small>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {showPriorityEditor && (
              <div className="mt-3 pt-3 border-top d-flex justify-content-end">
                <button
                  className="btn btn-primary rounded-pill px-4 btn-sm"
                  onClick={handleSavePriorities}
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "strategy" && (
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-4">
            <h6 className="fw-bold mb-2">Scheduling Strategy</h6>
            <p className="text-muted small mb-3">
              Choose how the system should handle conflicts when rescheduling events
            </p>

            <div className="d-flex flex-column gap-2">
              {Object.entries(STRATEGY_DESCRIPTIONS).map(([strategy, description]) => (
                <div
                  key={strategy}
                  className={`card border-2 rounded-3 cursor-pointer ${
                    selectedStrategy === strategy ? "border-primary bg-primary bg-opacity-10" : "border-light"
                  }`}
                  style={{ cursor: "pointer" }}
                  onClick={() => handleStrategyChange(strategy)}
                >
                  <div className="card-body p-3">
                    <div className="d-flex align-items-center gap-2">
                      <input
                        type="radio"
                        className="form-check-input"
                        checked={selectedStrategy === strategy}
                        onChange={() => handleStrategyChange(strategy)}
                      />
                      <div>
                        <strong className="text-capitalize d-block" style={{ fontSize: "14px" }}>
                          {strategy.replace(/_/g, " ")}
                        </strong>
                        <small className="text-muted">{description}</small>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 p-3 bg-light rounded-3">
        <small className="fw-bold d-block mb-2">Priority Legend</small>
        <div className="d-flex flex-wrap gap-3">
          {[
            { min: 9, label: "Critical", color: getPriorityColor(10) },
            { min: 7, label: "High", color: getPriorityColor(8) },
            { min: 5, label: "Medium", color: getPriorityColor(6) },
            { min: 3, label: "Low", color: getPriorityColor(4) },
            { min: 1, label: "Very Low", color: getPriorityColor(1) },
          ].map((item) => (
            <div key={item.label} className="d-flex align-items-center gap-1">
              <div
                className="rounded-circle"
                style={{ width: 10, height: 10, backgroundColor: item.color }}
              />
              <small className="text-muted">{item.label}</small>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
