from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.api.prashna import router as prashna_router
from app.api.consultants import router as consultants_router
from app.api.validation import router as validation_router
from app.api.community import router as community_router
from app.api.consultation import router as consultation_router
from app.api.astrologer import router as astrologer_router
from app.storage.database import init_db
from app.storage.community_db import init_community_db
from app.storage.consultation_db import init_consultation_db

app = FastAPI(title="Prashna Kundli MVP", version="0.1.0")


@app.on_event("startup")
async def startup() -> None:
    init_db()
    await init_community_db()
    await init_consultation_db()


@app.get("/api/config")
def get_config():
    return {
        "supabaseUrl": os.getenv("SUPABASE_URL", ""),
        "supabaseAnonKey": os.getenv("SUPABASE_ANON_KEY", "")
    }


app.include_router(prashna_router, prefix="/api")
app.include_router(consultants_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(community_router, prefix="/api")
app.include_router(consultation_router, prefix="/api")
app.include_router(astrologer_router, prefix="/api")

# Realtime WebSockets
from fastapi import WebSocket, WebSocketDisconnect
from app.services.realtime import manager
import json

@app.websocket("/ws/community/{channel_name}")
async def websocket_community(websocket: WebSocket, channel_name: str):
    await manager.connect(websocket, f"community_{channel_name}")
    try:
        while True:
            data = await websocket.receive_text()
            # For now, just broadcast the received message back to the channel
            # In production, this would be saved to DB first
            msg = json.loads(data)
            await manager.broadcast(f"community_{channel_name}", msg)
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"community_{channel_name}")

@app.websocket("/ws/consultation/{booking_id}")
async def websocket_consultation(websocket: WebSocket, booking_id: str):
    await manager.connect(websocket, f"consultation_{booking_id}")
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            await manager.broadcast(f"consultation_{booking_id}", msg)
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"consultation_{booking_id}")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
