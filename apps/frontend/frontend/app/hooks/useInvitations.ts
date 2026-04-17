import { useState, useEffect, useCallback } from "react";
import { 
    fetchInvitations, 
    acceptInvitation as apiAccept, 
    forceAcceptInvitation as apiForceAccept,
    reportConflict as apiReportConflict,
    declineInvitation as apiDecline, 
    fetchConflictReports as apiFetchConflictReports,
    dismissConflictReport as apiDismissConflictReport,
    InvitationResponse, 
    AcceptInvitationResult,
    ConflictReport,
} from "../services/collaborators.api";

type AfterAcceptCallback = (() => void) | undefined;

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/^http/, "ws");

export function useInvitations(afterAcceptCallback?: AfterAcceptCallback) {
    const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
    const [loading, setLoading] = useState(false);
    const [conflictResult, setConflictResult] = useState<AcceptInvitationResult | null>(null);
    const [conflictReportedMessage, setConflictReportedMessage] = useState<string | null>(null);
    const [receivedConflictReports, setReceivedConflictReports] = useState<ConflictReport[]>([]);

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

    const loadConflictReports = useCallback(async () => {
        const userId = getUserId();
        if (!userId) return;
        try {
            const reports = await apiFetchConflictReports(userId);
            setReceivedConflictReports(reports);
        } catch (error) {
            console.error("Error loading conflict reports", error);
        }
    }, []);

    useEffect(() => {
        loadInvitations();
        loadConflictReports();
        
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
                    } else if (data.type === "conflict_reported") {
                        loadConflictReports();
                    }
                } catch (e) {
                    console.error("Error parsing WS message", e);
                }
            };

            ws.onclose = () => {
                reconnectTimer = setTimeout(connect, 3000);
            };
        }

        connect();

        return () => {
            clearTimeout(reconnectTimer);
            if (ws) ws.close();
        };
    }, [loadInvitations, loadConflictReports]);

    const acceptInvitation = async (invitationId: string) => {
        const result = await apiAccept(invitationId);
        
        if (result.status === "conflict") {
            setConflictResult(result);
            return;
        }
        
        setInvitations(prev => prev.filter(inv => inv.id !== invitationId));
        if (afterAcceptCallback) {
            afterAcceptCallback();
        }
    };

    const forceAcceptInvitation = async (invitationId: string) => {
        await apiForceAccept(invitationId);
        setConflictResult(null);
        setInvitations(prev => prev.filter(inv => inv.id !== invitationId));
        if (afterAcceptCallback) {
            afterAcceptCallback();
        }
    };

    const reportConflictToCreator = async (invitationId: string, message?: string) => {
        const result = await apiReportConflict(invitationId, message);
        setConflictResult(null);
        setConflictReportedMessage(result.message);
        setInvitations(prev => prev.filter(inv => inv.id !== invitationId));
        setTimeout(() => setConflictReportedMessage(null), 5000);
    };

    const dismissConflict = () => {
        setConflictResult(null);
    };

    const dismissConflictReport = async (invitationId: string) => {
        try {
            await apiDismissConflictReport(invitationId);
        } catch (e) {
            console.error("Error dismissing conflict report", e);
        }
        setReceivedConflictReports(prev => prev.filter(r => r.invitation_id !== invitationId));
    };

    const declineInvitation = async (invitationId: string) => {
        await apiDecline(invitationId);
        setInvitations(prev => prev.filter(inv => inv.id !== invitationId));
    };

    return {
        invitations,
        loading,
        acceptInvitation,
        forceAcceptInvitation,
        reportConflictToCreator,
        dismissConflict,
        conflictResult,
        conflictReportedMessage,
        receivedConflictReports,
        dismissConflictReport,
        declineInvitation,
        refresh: loadInvitations
    };
}
