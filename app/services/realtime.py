import asyncio
import json
from typing import Dict, List, Optional
from fastapi import WebSocket
from app.storage.cache import redis_client

class ConnectionManager:
    def __init__(self):
        # Maps channel names to lists of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Keep track of which pubsub tasks are running for which channels
        self.pubsub_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
            
        self.active_connections[channel].append(websocket)

        # Start a Redis pubsub listener for this channel if not already running
        if redis_client and channel not in self.pubsub_tasks:
            task = asyncio.create_task(self._listen_to_redis(channel))
            self.pubsub_tasks[channel] = task

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)
            
            # If no more connections to this channel, cancel the pubsub listener
            if not self.active_connections[channel]:
                del self.active_connections[channel]
                if channel in self.pubsub_tasks:
                    self.pubsub_tasks[channel].cancel()
                    del self.pubsub_tasks[channel]

    async def broadcast(self, channel: str, message: dict):
        # If redis is available, publish to redis (it will be picked up by the listener)
        if redis_client:
            redis_client.publish(channel, json.dumps(message))
        else:
            # Fallback to local memory broadcast
            await self._send_to_local_connections(channel, message)

    async def _send_to_local_connections(self, channel: str, message: dict):
        if channel in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
                    
            for dead in dead_connections:
                self.disconnect(dead, channel)

    async def _listen_to_redis(self, channel: str):
        if not redis_client:
            return
            
        pubsub = redis_client.pubsub()
        pubsub.subscribe(channel)
        
        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self._send_to_local_connections(channel, data)
        except asyncio.CancelledError:
            pubsub.unsubscribe(channel)
        except Exception as e:
            print(f"Redis PubSub Error on {channel}: {e}")

manager = ConnectionManager()
