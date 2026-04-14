import { useState, useEffect, useCallback } from "react";
import { fetchInvitations, acceptInvitation as apiAccept, declineInvitation as apiDecline, InvitationResponse } from "../services/collaborators.api";

// Allow passing a callback to run after accepting invitation (e.g., reload events)
type AfterAcceptCallback = (() => void) | undefined;

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/^http/, "ws");

export function useInvitations(afterAcceptCallback?: AfterAcceptCallback) {
    const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
    const [loading, setLoading] = useState(false);

    const getUserId = () => {
        try {
            const sessionItem = localStorage.getItem("scheduler_auth_session");
            if (sessionItem) {
                const sessionData = JSON.parse(sessionItem);
                return sessionData.user_id;
            }
        } catch (e) {
            console.error("Error reading session", e);
        }
        return null;
    };

    const loadInvitations = useCallback(async () => {
        const userId = getUserId();
        if (!userId) return;
        
        try {
            setLoading(true);
            const data = await fetchInvitations(userId);
            setInvitations(data);
        } catch (error) {
            console.error("Error loading invitations", error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadInvitations();
        
        const userId = getUserId();
        if (!userId) return;

        let ws: WebSocket | null = null;
        let reconnectTimer: any = null;

        const connect = () => {
            ws = new WebSocket(`${WS_BASE}/ws/${userId}`);
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === "new_invitation") {
                        loadInvitations();
                    }
                } catch (e) {
                    console.error("Error parsing WS message", e);
                }
            };

            ws.onclose = () => {
                // Try to reconnect
                reconnectTimer = setTimeout(connect, 3000);
            };
        }

        connect();

        return () => {
            clearTimeout(reconnectTimer);
            if (ws) ws.close();
        };
    }, [loadInvitations]);

    const acceptInvitation = async (invitationId: string) => {
        await apiAccept(invitationId);
        setInvitations(prev => prev.filter(inv => inv.id !== invitationId));
        if (afterAcceptCallback) {
            afterAcceptCallback();
        }
    };

    const declineInvitation = async (invitationId: string) => {
        await apiDecline(invitationId);
        setInvitations(prev => prev.filter(inv => inv.id !== invitationId));
    };

    return {
        invitations,
        loading,
        acceptInvitation,
        declineInvitation,
        refresh: loadInvitations
    };
}
