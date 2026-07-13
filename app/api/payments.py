import hmac
from hashlib import sha256
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import Field

from app.config import get_settings
from app.core.rate_limiter import payment_limiter
from app.core.consultation_lifecycle import validate_price_amount
from app.dependencies import AuthState, get_optional_current_user
from app.schemas.common import ID_RE, StrictRequestModel
from app.storage.consultation_db import get_consultation_case, mark_consultation_request_paid
from app.storage.database import get_service_client
from app.storage.payments_db import create_payment_record, get_payment_by_provider_ref, update_payment_status

router = APIRouter(prefix="/payments", tags=["payments"])

RAZORPAY_API_URL = "https://api.razorpay.com/v1/orders"


class RazorpayOrderRequest(StrictRequestModel):
    currency: str = Field(default="INR", pattern="^INR$")
    receipt: Optional[str] = Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9_.:-]{1,40}$")
    purpose: str = Field(default="consultation", max_length=80, pattern=r"^[A-Za-z0-9_.:-]{1,80}$")
    consultation_case_id: Optional[str] = Field(default=None, max_length=120, pattern=ID_RE)
    match_request_id: Optional[str] = Field(default=None, max_length=120, pattern=ID_RE)
    requester_email: Optional[str] = Field(default=None, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RazorpayVerifyRequest(StrictRequestModel):
    razorpay_order_id: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9_:-]+$")
    razorpay_payment_id: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9_:-]+$")
    razorpay_signature: str = Field(min_length=20, max_length=256, pattern=r"^[A-Fa-f0-9]+$")


def _razorpay_keys() -> tuple[str, str]:
    settings = get_settings()
    key_id = settings.razorpay_key_id
    key_secret = settings.razorpay_key_secret
    if not key_id or not key_secret:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    return key_id, key_secret


def _consultation_amount_inr() -> float:
    return float(validate_price_amount(get_settings().consultation_price_inr))


def _case_owner_matches(case: dict[str, Any], auth: Optional[AuthState], requester_email: Optional[str]) -> bool:
    if not case:
        return False
    if auth and auth.is_admin:
        return True
    user = case.get("user") or {}
    case_email = str(case.get("email") or user.get("email") or "").strip().lower()
    if auth and (case.get("user_id") == auth.user_id or case_email == (auth.email or "").strip().lower()):
        return True
    return bool(requester_email and case_email and requester_email.strip().lower() == case_email)


def _hmac_hex(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()


def _verify_signature(secret: str, body: bytes, signature: str) -> bool:
    expected = _hmac_hex(secret, body)
    return hmac.compare_digest(expected, signature)


@router.post("/razorpay/order", dependencies=[Depends(payment_limiter)])
async def create_razorpay_order(
    payload: RazorpayOrderRequest,
    auth: Optional[AuthState] = Depends(get_optional_current_user),
) -> dict[str, Any]:
    key_id, key_secret = _razorpay_keys()
    db = auth.client if auth else get_service_client()
    user_id = auth.user_id if auth else None

    if not payload.consultation_case_id:
        raise HTTPException(status_code=400, detail="consultation_case_id is required")

    if payload.consultation_case_id:
        case = await get_consultation_case(payload.consultation_case_id, db)
        if not _case_owner_matches(case or {}, auth, payload.requester_email):
            raise HTTPException(status_code=403, detail="Not allowed to create payment for this consultation case")

    amount_inr = _consultation_amount_inr()
    amount_paise = int(round(amount_inr * 100))
    receipt_owner = (user_id or payload.requester_email or "guest").replace("@", "_").replace(".", "_")[:12]
    receipt = payload.receipt or f"ks_{receipt_owner}_{amount_paise}"

    request_payload = {
        "amount": amount_paise,
        "currency": payload.currency,
        "receipt": receipt[:40],
        "notes": {
            "user_id": user_id or "",
            "requester_email": payload.requester_email or "",
            "purpose": payload.purpose,
            "consultation_case_id": payload.consultation_case_id or "",
            "match_request_id": payload.match_request_id or "",
        },
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
        response = await client.post(
            RAZORPAY_API_URL,
            json=request_payload,
            auth=(key_id, key_secret),
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Razorpay order creation failed")

    order = response.json()
    create_payment_record(
        db=db,
        user_id=user_id,
        amount=amount_inr,
        currency=payload.currency,
        provider="razorpay",
        provider_ref=order["id"],
        status=order.get("status") or "created",
        booking_id=payload.consultation_case_id,
        match_request_id=payload.match_request_id,
    )
    return {
        "provider": "razorpay",
        "key_id": key_id,
        "amount_inr": amount_inr,
        "order": order,
    }


@router.post("/razorpay/verify", dependencies=[Depends(payment_limiter)])
async def verify_razorpay_payment(
    payload: RazorpayVerifyRequest,
    auth: Optional[AuthState] = Depends(get_optional_current_user),
) -> dict[str, Any]:
    _, key_secret = _razorpay_keys()
    db = auth.client if auth else get_service_client()
    existing_payment = get_payment_by_provider_ref(
        provider="razorpay",
        provider_ref=payload.razorpay_order_id,
        db=db,
    )
    if not existing_payment:
        raise HTTPException(status_code=404, detail="Payment order not found")

    body = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode("utf-8")
    if not _verify_signature(key_secret, body, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay payment signature")

    payment = update_payment_status(
        provider="razorpay",
        provider_ref=payload.razorpay_order_id,
        status="paid",
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment order not found")

    paid_case = None
    if payment.get("booking_id"):
        paid_case = await mark_consultation_request_paid(
            payment["booking_id"],
            provider="razorpay",
            provider_ref=payload.razorpay_order_id,
            payment_id=payload.razorpay_payment_id,
        )

    return {
        "status": "paid",
        "provider": "razorpay",
        "provider_ref": payload.razorpay_order_id,
        "payment_id": payload.razorpay_payment_id,
        "case": paid_case,
    }


@router.post("/razorpay/webhook", dependencies=[Depends(payment_limiter)])
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
) -> dict[str, str]:
    webhook_secret = get_settings().razorpay_webhook_secret
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Razorpay webhook is not configured")

    body = await request.body()
    if not x_razorpay_signature or not _verify_signature(webhook_secret, body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay webhook signature")

    event = await request.json()
    event_name = event.get("event", "")
    payload = event.get("payload", {})
    payment_entity = payload.get("payment", {}).get("entity", {})
    order_entity = payload.get("order", {}).get("entity", {})
    order_id = payment_entity.get("order_id") or order_entity.get("id")

    if order_id and event_name in {"payment.captured", "order.paid"}:
        payment = update_payment_status(provider="razorpay", provider_ref=order_id, status="paid")
        if payment and payment.get("booking_id"):
            await mark_consultation_request_paid(
                payment["booking_id"],
                provider="razorpay",
                provider_ref=order_id,
                payment_id=payment_entity.get("id"),
            )
    elif order_id and event_name in {"payment.failed"}:
        update_payment_status(provider="razorpay", provider_ref=order_id, status="failed")

    return {"status": "ok"}
