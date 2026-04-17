/**
 * Collaborators API Service
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface InvitationResponse {
    id: string;
    event_id: string;
    inviter_id: string;
    invitee_id: string;
    status: string;
    created_at: string;
    updated_at: string;
    event_title: string;
    event_date: string;
    inviter_username: string;
}

export interface ConflictingEventInfo {
    event_id: string;
    title: string;
    start_time: string;
    end_time: string;
    calendar_id: string;
}

export interface AcceptInvitationResult {
    status: "accepted" | "conflict";
    collaborator?: {
        id: string;
        event_id: string;
        user_id: string;
        role: string;
        created_at: string;
        updated_at: string;
    };
    has_conflict: boolean;
    conflicts: ConflictingEventInfo[];
    collab_event_title?: string;
    collab_event_start?: string;
    collab_event_end?: string;
    invitation_id?: string;
    message?: string;
}

export async function fetchInvitations(userId: string): Promise<InvitationResponse[]> {
    const res = await fetch(`${API_BASE}/collaborators/invitations/${userId}`);
    if (!res.ok) {
        throw new Error(`Failed to fetch invitations: ${res.statusText}`);
    }
    return res.json();
}

export async function acceptInvitation(invitationId: string): Promise<AcceptInvitationResult> {
    const res = await fetch(`${API_BASE}/collaborators/invitation/${invitationId}/accept`, {
        method: "POST"
    });
    if (!res.ok) {
        throw new Error(`Failed to accept invitation: ${res.statusText}`);
    }
    return res.json();
}

export async function forceAcceptInvitation(invitationId: string): Promise<AcceptInvitationResult> {
    const res = await fetch(`${API_BASE}/collaborators/invitation/${invitationId}/force-accept`, {
        method: "POST"
    });
    if (!res.ok) {
        throw new Error(`Failed to force-accept invitation: ${res.statusText}`);
    }
    return res.json();
}

export async function reportConflict(invitationId: string, message?: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/collaborators/invitation/${invitationId}/report-conflict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invitation_id: invitationId, message }),
    });
    if (!res.ok) {
        throw new Error(`Failed to report conflict: ${res.statusText}`);
    }
    return res.json();
}

export async function declineInvitation(invitationId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/collaborators/invitation/${invitationId}/decline`, {
        method: "POST"
    });
    if (!res.ok) {
        throw new Error(`Failed to decline invitation: ${res.statusText}`);
    }
    return res.json();
}

export interface ConflictReport {
    invitation_id: string;
    event_id: string;
    event_title: string;
    reporter_username: string;
    message: string;
}

export async function fetchConflictReports(userId: string): Promise<ConflictReport[]> {
    const res = await fetch(`${API_BASE}/collaborators/conflict-reports/${userId}`);
    if (!res.ok) {
        throw new Error(`Failed to fetch conflict reports: ${res.statusText}`);
    }
    return res.json();
}

export async function dismissConflictReport(invitationId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/collaborators/conflict-reports/${invitationId}/dismiss`, {
        method: "POST"
    });
    if (!res.ok) {
        throw new Error(`Failed to dismiss conflict report: ${res.statusText}`);
    }
}
