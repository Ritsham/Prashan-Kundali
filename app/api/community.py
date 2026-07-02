from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List
import json
import logging

from app.storage.community_db import (
    get_channels,
    save_message,
    get_messages,
    delete_message,
    star_message,
    save_thread_reply,
    get_thread_replies,
)

router = APIRouter(prefix="/community", tags=["community"])

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps channel names to a list of active websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_name: str):
        await websocket.accept()
        if channel_name not in self.active_connections:
            self.active_connections[channel_name] = []
        self.active_connections[channel_name].append(websocket)

    def disconnect(self, websocket: WebSocket, channel_name: str):
        if channel_name in self.active_connections:
            self.active_connections[channel_name].remove(websocket)

    async def broadcast(self, message: str, channel_name: str):
        if channel_name in self.active_connections:
            for connection in self.active_connections[channel_name]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending message to websocket: {e}")


manager = ConnectionManager()


@router.get("/channels")
async def api_get_channels():
    return await get_channels()


@router.get("/messages/{channel_name}")
async def api_get_messages(channel_name: str, limit: int = 50):
    return await get_messages(channel_name, limit)


@router.get("/threads/{message_id}")
async def api_get_threads(message_id: str):
    return await get_thread_replies(message_id)


@router.websocket("/ws/{channel_name}")
async def websocket_endpoint(websocket: WebSocket, channel_name: str):
    await manager.connect(websocket, channel_name)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action")
                
                if action == "send_message":
                    saved_msg = await save_message(
                        channel_name=channel_name,
                        user_name=payload.get("user_name", "Anonymous"),
                        content=payload.get("content", ""),
                        image_base64=payload.get("image_base64")
                    )
                    await manager.broadcast(
                        json.dumps({"type": "new_message", "data": saved_msg}), 
                        channel_name
                    )
                
                elif action == "delete_message":
                    msg_id = payload.get("message_id")
                    await delete_message(msg_id)
                    await manager.broadcast(
                        json.dumps({"type": "message_deleted", "message_id": msg_id}),
                        channel_name
                    )
                    
                elif action == "star_message":
                    msg_id = payload.get("message_id")
                    await star_message(msg_id)
                    await manager.broadcast(
                        json.dumps({"type": "message_starred", "message_id": msg_id}),
                        channel_name
                    )
                    
                elif action == "send_thread_reply":
                    saved_reply = await save_thread_reply(
                        parent_message_id=payload.get("parent_message_id"),
                        user_name=payload.get("user_name", "Anonymous"),
                        content=payload.get("content", ""),
                        image_base64=payload.get("image_base64")
                    )
                    await manager.broadcast(
                        json.dumps({"type": "new_thread_reply", "data": saved_reply}),
                        channel_name
                    )
            except json.JSONDecodeError:
                logger.error("Received non-JSON message over websocket")
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_name)
