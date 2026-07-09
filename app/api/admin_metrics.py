from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional

from app.dependencies import AuthState, RequireRole
from app.storage.admin_metrics_db import admin_metrics, record_visit_event

router = APIRouter()


class VisitEventRequest(BaseModel):
    visitor_key: str = Field(min_length=8, max_length=160)
    path: str = Field(default="/", max_length=500)
    referrer: str = Field(default="", max_length=500)


@router.post("/analytics/visit")
async def record_visit(payload: VisitEventRequest, request: Request):
    return record_visit_event(
        visitor_key=payload.visitor_key,
        path=payload.path,
        referrer=payload.referrer,
        user_agent=request.headers.get("user-agent", ""),
    )


@router.get("/admin/metrics")
async def get_admin_metrics(auth: AuthState = Depends(RequireRole("admin"))):
    return admin_metrics()
