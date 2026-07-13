from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field
from typing import Optional

from app.core.rate_limiter import public_limiter
from app.dependencies import AuthState, RequireAdmin
from app.schemas.common import StrictRequestModel
from app.storage.admin_metrics_db import admin_metrics, record_visit_event
from app.storage.audit_db import list_admin_audit_logs
from app.storage.database import get_service_client

router = APIRouter()


class VisitEventRequest(StrictRequestModel):
    visitor_key: str = Field(min_length=8, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")
    path: str = Field(default="/", min_length=1, max_length=500)
    referrer: str = Field(default="", max_length=500)


@router.post("/analytics/visit", dependencies=[Depends(public_limiter)])
async def record_visit(payload: VisitEventRequest, request: Request):
    return record_visit_event(
        visitor_key=payload.visitor_key,
        path=payload.path,
        referrer=payload.referrer,
        user_agent=request.headers.get("user-agent", ""),
        db=get_service_client(),
    )


@router.get("/admin/metrics")
async def get_admin_metrics(auth: AuthState = Depends(RequireAdmin())):
    return admin_metrics(auth.client)


@router.get("/admin/dashboard/metrics")
async def get_admin_dashboard_metrics(auth: AuthState = Depends(RequireAdmin())):
    return admin_metrics(auth.client)


@router.get("/admin/audit-logs")
async def get_admin_audit_logs(
    limit: int = Query(default=100, ge=1, le=250),
    entity_type: Optional[str] = Query(default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$"),
    auth: AuthState = Depends(RequireAdmin()),
):
    return {"logs": list_admin_audit_logs(limit=limit, entity_type=entity_type)}
