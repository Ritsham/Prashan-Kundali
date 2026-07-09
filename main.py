from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.prashna import router as prashna_router
from app.api.consultants import router as consultants_router
from app.api.validation import router as validation_router
from app.api.community import router as community_router
from app.api.consultation import router as consultation_router
from app.api.astrologer import router as astrologer_router
from app.api.admin_metrics import router as admin_metrics_router
from app.api.matchmaking import router as matchmaking_router
from app.storage.database import init_db
from app.storage.community_db import init_community_db
from app.storage.consultation_db import init_consultation_db
from app.storage.matchmaking_db import init_matchmaking_db

app = FastAPI(title="Prashna Kundli MVP", version="0.1.0")

ADMIN_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ADMIN_CORS_ORIGINS", "http://127.0.0.1:8088,http://localhost:8088").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ADMIN_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    await init_community_db()
    await init_consultation_db()
    await init_matchmaking_db()


@app.get("/api/config")
def get_config():
    return {
        "supabaseUrl": os.getenv("SUPABASE_URL", ""),
        "supabaseAnonKey": os.getenv("SUPABASE_ANON_KEY", "")
    }


@app.get("/consultation", include_in_schema=False)
def consultation_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/consultation.html")


@app.get("/astro-community", include_in_schema=False)
def astro_community_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/community.html")

@app.get("/matchmaking", include_in_schema=False)
def matchmaking_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/matchmaking.html")

@app.get("/matchmaking-booking", include_in_schema=False)
def matchmaking_booking_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/matchmaking-booking.html")

@app.get("/community/apply", include_in_schema=False)
def community_apply_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/apply.html")

@app.get("/community/application-status", include_in_schema=False)
def community_status_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/community-status.html")

@app.get("/admin/community-applications", include_in_schema=False)
def admin_community_apps_list():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/admin-community-applications.html")

@app.get("/admin/community-applications/{app_id}", include_in_schema=False)
def admin_community_apps_detail(app_id: str):
    from fastapi.responses import FileResponse
    return FileResponse("frontend/admin-community-application-detail.html")


app.include_router(prashna_router, prefix="/api")
app.include_router(consultants_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(community_router, prefix="/api")
app.include_router(consultation_router, prefix="/api")
app.include_router(astrologer_router, prefix="/api")
app.include_router(admin_metrics_router, prefix="/api")
app.include_router(matchmaking_router, prefix="/api")

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

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
