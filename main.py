from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import os
import time
import json as log_json
from uuid import uuid4
from typing import Optional
from app.config import get_settings, validate_startup_settings
from app.core.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from app.schemas.common import HealthResponse, ReadinessResponse, TZ_OFFSET_RE

from app.api.prashna import router as prashna_router
from app.api.consultants import router as consultants_router
from app.api.validation import router as validation_router
from app.api.community import router as community_router
from app.api.consultation import router as consultation_router
from app.api.astrologer import router as astrologer_router
from app.api.admin_metrics import router as admin_metrics_router
from app.api.matchmaking import router as matchmaking_router
from app.api.payments import router as payments_router
from app.api.auth import router as auth_router
from app.storage.database import init_db
from app.storage.community_db import init_community_db
from app.storage.consultation_db import init_consultation_db
from app.storage.matchmaking_db import init_matchmaking_db

app = FastAPI(
    title="Shree Lakshmi Astro API",
    version="0.2.0",
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        429: {"description": "Rate Limited"},
        500: {"description": "Internal Server Error"},
    },
)
logger = logging.getLogger("kundali.request")
settings = get_settings()


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return log_json.dumps(payload, default=str)


handler = logging.StreamHandler()
handler.setFormatter(JsonLogFormatter())
logging.basicConfig(level=settings.log_level, handlers=[handler], force=True)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request, call_next):
    request_id = request.headers.get("x-request-id") or f"req_{uuid4().hex[:12]}"
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.on_event("startup")
async def startup() -> None:
    validate_startup_settings()
    logger.info(
        "startup_settings_validated",
        extra={"request_id": "startup", "path": "/startup", "status_code": 200},
    )
    init_db()
    await init_community_db()
    await init_consultation_db()
    await init_matchmaking_db()


@app.get("/api/config")
def get_config():
    return get_settings().frontend_public_config


@app.get("/health", response_model=HealthResponse, tags=["system"])
@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", app_env=settings.app_env, version=app.version)


@app.get("/readyz", response_model=ReadinessResponse, tags=["system"])
@app.get("/api/readyz", response_model=ReadinessResponse, tags=["system"])
async def readiness() -> ReadinessResponse:
    checks = {
        "settings": True,
        "supabase_configured": bool(settings.supabase_url and settings.supabase_anon_key),
        "service_role_configured": bool(settings.supabase_service_role_key),
        "cors_configured": bool(settings.cors_origins),
    }
    if settings.is_production and not all(checks.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Service is not ready", "checks": checks},
        )
    return ReadinessResponse(
        status="ok" if all(checks.values()) else "degraded",
        app_env=settings.app_env,
        checks=checks,
    )


@app.get("/consultation", include_in_schema=False)
def consultation_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend_old/consultation.html")


@app.get("/booking", include_in_schema=False)
def old_react_booking_page_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/consultation", status_code=302)


@app.get("/astro-community", include_in_schema=False)
def astro_community_page():
    from fastapi.responses import FileResponse
    if os.path.isfile("frontend/dist/index.html"):
        return FileResponse("frontend/dist/index.html")
    return FileResponse("frontend_old/community.html")

@app.get("/matchmaking", include_in_schema=False)
def matchmaking_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend_old/matchmaking.html")

@app.get("/matchmaking-booking", include_in_schema=False)
def matchmaking_booking_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend_old/matchmaking-booking.html")

@app.get("/community/apply", include_in_schema=False)
def community_apply_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend_old/apply.html")

@app.get("/community/application-status", include_in_schema=False)
def community_status_page():
    from fastapi.responses import FileResponse
    return FileResponse("frontend_old/community-status.html")

@app.get("/admin/community-applications", include_in_schema=False)
def admin_community_apps_list():
    from fastapi.responses import FileResponse
    return FileResponse("frontend_old/admin-community-applications.html")

@app.get("/admin/community-applications/{app_id}", include_in_schema=False)
def admin_community_apps_detail(app_id: str):
    from fastapi.responses import FileResponse
    return FileResponse("frontend_old/admin-community-application-detail.html")


def serve_react_spa_or_legacy():
    from fastapi.responses import FileResponse
    if os.path.isfile("frontend/dist/index.html"):
        return FileResponse("frontend/dist/index.html")
    return FileResponse("frontend_old/index.html")


@app.get("/return-policy", include_in_schema=False)
@app.get("/refund-policy", include_in_schema=False)
@app.get("/privacy-policy", include_in_schema=False)
@app.get("/disclaimer", include_in_schema=False)
@app.get("/about-contact", include_in_schema=False)
def legal_spa_page():
    return serve_react_spa_or_legacy()


app.include_router(prashna_router, prefix="/api")
app.include_router(consultants_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(community_router, prefix="/api")
app.include_router(consultation_router, prefix="/api")
app.include_router(astrologer_router, prefix="/api")
app.include_router(admin_metrics_router, prefix="/api")
app.include_router(matchmaking_router, prefix="/api")
app.include_router(payments_router, prefix="/api")
app.include_router(auth_router, prefix="/api")

# Realtime WebSockets
from fastapi import WebSocket, WebSocketDisconnect
from app.services.realtime import manager
from app.dependencies import get_current_user_from_token
from app.storage.consultation_db import get_consultation_request
import json

legacy_ws_attempts: dict[str, list[float]] = {}


def legacy_ws_rate_limited(websocket: WebSocket, scope: str, limit: int = 20, window: int = 60) -> bool:
    client_host = websocket.client.host if websocket.client else "unknown"
    key = f"{scope}:{client_host}"
    now = time.time()
    attempts = [stamp for stamp in legacy_ws_attempts.get(key, []) if stamp >= now - window]
    if len(attempts) >= limit:
        legacy_ws_attempts[key] = attempts
        return True
    attempts.append(now)
    legacy_ws_attempts[key] = attempts
    return False


@app.websocket("/ws/community/{channel_name}")
async def websocket_community(websocket: WebSocket, channel_name: str):
    if legacy_ws_rate_limited(websocket, "legacy_community"):
        await websocket.close(code=1008)
        return
    if not get_settings().enable_legacy_unauthenticated_ws:
        await websocket.close(code=1008)
        return
    token = websocket.query_params.get("token", "")
    auth = get_current_user_from_token(token)
    if not auth or (not auth.is_admin and not auth.is_verified_astrologer):
        await websocket.close(code=1008)
        return
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
    if legacy_ws_rate_limited(websocket, "legacy_consultation"):
        await websocket.close(code=1008)
        return
    if not get_settings().enable_legacy_unauthenticated_ws:
        await websocket.close(code=1008)
        return
    token = websocket.query_params.get("token", "")
    auth = get_current_user_from_token(token)
    if not auth:
        await websocket.close(code=1008)
        return
    request = await get_consultation_request(booking_id, auth.client)
    request_user = (request or {}).get("user") or {}
    if not request or not (
        auth.is_admin
        or request.get("user_id") == auth.user_id
        or request.get("assigned_astrologer") == auth.user_id
        or request.get("email") == auth.email
        or request_user.get("email") == auth.email
    ):
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, f"consultation_{booking_id}")
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            await manager.broadcast(f"consultation_{booking_id}", msg)
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"consultation_{booking_id}")

# Today's Panchang API Endpoint (cached)
import httpx
from datetime import datetime, timedelta
from fastapi.responses import FileResponse

panchang_cache = {}

@app.get("/api/panchang")
async def get_panchang(
    lat: float = Query(default=28.6139, ge=-90, le=90),
    lng: float = Query(default=77.2090, ge=-180, le=180),
    date_str: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    tz_offset: str = Query(default="+05:30", pattern=TZ_OFFSET_RE),
):
    if not date_str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
    cache_key = f"{date_str}_{round(lat, 2)}_{round(lng, 2)}_{tz_offset}"
    if cache_key in panchang_cache:
        return panchang_cache[cache_key]
        
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        dt = datetime.utcnow()
        
    formatted_date_slash = dt.strftime("%d/%m/%Y")
    
    tithi_name = "Shukla Ekadashi"
    nakshatra_name = "Anuradha"
    sunrise_time = "05:24 AM"
    sunset_time = "07:12 PM"
    muhurat_time = "11:45 AM - 12:35 PM"
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0)) as client:
        # 1. Fetch Tithi (LunarDay)
        try:
            tithi_url = f"https://api.vedastro.org/api/Calculate/LunarDay/Location/{lat},{lng}/Time/06:00/{formatted_date_slash}/{tz_offset}/Ayanamsa/LAHIRI"
            resp = await client.get(tithi_url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("Status") == "Pass":
                    ld = data["Payload"]["LunarDay"]
                    tithi_name = f"{ld['Paksha']} {ld['Name']}"
        except Exception:
            logging.getLogger("kundali.upstream").warning("panchang_tithi_fetch_failed")
            
        # 2. Fetch Nakshatra (MoonConstellation)
        try:
            nakshatra_url = f"https://api.vedastro.org/api/Calculate/MoonConstellation/Location/{lat},{lng}/Time/06:00/{formatted_date_slash}/{tz_offset}/Ayanamsa/LAHIRI"
            resp = await client.get(nakshatra_url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("Status") == "Pass":
                    nakshatra_name = data["Payload"]["MoonConstellation"]
        except Exception:
            logging.getLogger("kundali.upstream").warning("panchang_nakshatra_fetch_failed")
            
        # 3. Fetch Sunrise/Sunset
        try:
            sunrise_url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&date={date_str}&formatted=1"
            resp = await client.get(sunrise_url, timeout=10.0)
            if resp.status_code == 200:
                s_data = resp.json()
                if s_data.get("status") == "OK":
                    results = s_data["results"]
                    sunrise_utc_str = results["sunrise"]
                    sunset_utc_str = results["sunset"]
                    
                    # Parse timezone offset (e.g. +05:30)
                    sign = 1 if tz_offset[0] == '+' else -1
                    hours = int(tz_offset[1:3])
                    minutes = int(tz_offset[4:6])
                    td = timedelta(hours=hours, minutes=minutes) * sign
                    
                    # Parse UTC times
                    sunrise_utc = datetime.strptime(f"{date_str} {sunrise_utc_str}", "%Y-%m-%d %I:%M:%S %p")
                    sunset_utc = datetime.strptime(f"{date_str} {sunset_utc_str}", "%Y-%m-%d %I:%M:%S %p")
                    
                    # Convert to local
                    sunrise_local = sunrise_utc + td
                    sunset_local = sunset_utc + td
                    
                    sunrise_time = sunrise_local.strftime("%I:%M %p")
                    sunset_time = sunset_local.strftime("%I:%M %p")
                    
                    # Compute Abhijit Muhurat
                    local_noon = sunrise_local + (sunset_local - sunrise_local) / 2
                    muhurat_start = local_noon - timedelta(minutes=24)
                    muhurat_end = local_noon + timedelta(minutes=24)
                    muhurat_time = f"{muhurat_start.strftime('%I:%M %p')} - {muhurat_end.strftime('%I:%M %p')}"
        except Exception:
            logging.getLogger("kundali.upstream").warning("panchang_sunrise_fetch_failed")
            
    payload = {
        "tithi": tithi_name,
        "nakshatra": nakshatra_name,
        "sunrise": sunrise_time,
        "sunset": sunset_time,
        "muhurat": muhurat_time
    }
    
    panchang_cache[cache_key] = payload
    return payload

# Mount static assets for the React App

# Note: The old frontend_old/ styles.css and chart-engine.js might be loaded from root.
# Vercel serverless bundles may omit optional static directories; only mount
# directories that exist so importing api/index.py never crashes.
if os.path.isdir("frontend_old"):
    app.mount("/frontend_old", StaticFiles(directory="frontend_old"), name="frontend_old")

if os.path.isdir("frontend/dist/assets"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")



# Catch-all route for SPA routing
@app.get("/", include_in_schema=False)
async def serve_root_spa():
    return FileResponse("frontend_old/index.html")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    # If the file exists in old frontend root (like styles.css), serve it
    old_file_path = os.path.join("frontend_old", full_path)
    if os.path.isfile(old_file_path):
        return FileResponse(old_file_path)
    
    # Otherwise, return the old frontend entry point
    return FileResponse("frontend_old/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
