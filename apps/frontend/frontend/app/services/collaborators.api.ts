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

export async function fetchInvitations(userId: string): Promise<InvitationResponse[]> {
    const res = await fetch(`${API_BASE}/collaborators/invitations/${userId}`);
    if (!res.ok) {
        throw new Error(`Failed to fetch invitations: ${res.statusText}`);
    }
    return res.json();
}

export async function acceptInvitation(invitationId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/collaborators/invitation/${invitationId}/accept`, {
        method: "POST"
    });
    if (!res.ok) {
        throw new Error(`Failed to accept invitation: ${res.statusText}`);
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
