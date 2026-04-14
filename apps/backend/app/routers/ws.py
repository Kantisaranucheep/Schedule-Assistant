"""WebSocket endpoints."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uuid import UUID
from app.core.websockets import manager

router = APIRouter(tags=["websockets"])

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: UUID):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # We don't necessarily expect messages from the client in this app, 
            # but we need to keep the connection open and listen for disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
