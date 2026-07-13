from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

CONSULTATION_STATUS_REQUESTED = "requested"
CONSULTATION_STATUS_PENDING_PAYMENT = "pending_payment"
CONSULTATION_STATUS_CONFIRMED = "confirmed"
CONSULTATION_STATUS_ACTIVE = "active"
CONSULTATION_STATUS_COMPLETED = "completed"
CONSULTATION_STATUS_CANCELLED = "cancelled"
CONSULTATION_STATUS_REFUNDED = "refunded"

CONSULTATION_STATUSES = {
    CONSULTATION_STATUS_REQUESTED,
    CONSULTATION_STATUS_PENDING_PAYMENT,
    CONSULTATION_STATUS_CONFIRMED,
    CONSULTATION_STATUS_ACTIVE,
    CONSULTATION_STATUS_COMPLETED,
    CONSULTATION_STATUS_CANCELLED,
    CONSULTATION_STATUS_REFUNDED,
}

ACTIVE_CONSULTATION_STATUSES = {
    CONSULTATION_STATUS_REQUESTED,
    CONSULTATION_STATUS_PENDING_PAYMENT,
    CONSULTATION_STATUS_CONFIRMED,
    CONSULTATION_STATUS_ACTIVE,
}

TERMINAL_CONSULTATION_STATUSES = {
    CONSULTATION_STATUS_COMPLETED,
    CONSULTATION_STATUS_CANCELLED,
    CONSULTATION_STATUS_REFUNDED,
}

STATUS_ALIASES = {
    "pending": CONSULTATION_STATUS_REQUESTED,
    "reviewed": CONSULTATION_STATUS_REQUESTED,
    "waiting_queue": CONSULTATION_STATUS_REQUESTED,
    "accepted": CONSULTATION_STATUS_CONFIRMED,
    "scheduled": CONSULTATION_STATUS_CONFIRMED,
    "in_progress": CONSULTATION_STATUS_ACTIVE,
    "queued": CONSULTATION_STATUS_CONFIRMED,
    "answered": CONSULTATION_STATUS_COMPLETED,
    "declined": CONSULTATION_STATUS_CANCELLED,
    "rejected": CONSULTATION_STATUS_CANCELLED,
    "complete": CONSULTATION_STATUS_COMPLETED,
}

ALLOWED_TRANSITIONS = {
    CONSULTATION_STATUS_REQUESTED: {
        CONSULTATION_STATUS_PENDING_PAYMENT,
        CONSULTATION_STATUS_CONFIRMED,
        CONSULTATION_STATUS_CANCELLED,
    },
    CONSULTATION_STATUS_PENDING_PAYMENT: {
        CONSULTATION_STATUS_CONFIRMED,
        CONSULTATION_STATUS_CANCELLED,
        CONSULTATION_STATUS_REFUNDED,
    },
    CONSULTATION_STATUS_CONFIRMED: {
        CONSULTATION_STATUS_ACTIVE,
        CONSULTATION_STATUS_COMPLETED,
        CONSULTATION_STATUS_CANCELLED,
        CONSULTATION_STATUS_REFUNDED,
    },
    CONSULTATION_STATUS_ACTIVE: {
        CONSULTATION_STATUS_COMPLETED,
        CONSULTATION_STATUS_CANCELLED,
        CONSULTATION_STATUS_REFUNDED,
    },
    CONSULTATION_STATUS_COMPLETED: set(),
    CONSULTATION_STATUS_CANCELLED: {CONSULTATION_STATUS_REFUNDED},
    CONSULTATION_STATUS_REFUNDED: set(),
}


def normalize_consultation_status(status: Any) -> str:
    value = str(status or CONSULTATION_STATUS_REQUESTED).strip().lower()
    return STATUS_ALIASES.get(value, value)


def is_valid_consultation_status(status: Any) -> bool:
    return normalize_consultation_status(status) in CONSULTATION_STATUSES


def assert_consultation_transition(current_status: Any, next_status: Any) -> None:
    current = normalize_consultation_status(current_status)
    target = normalize_consultation_status(next_status)
    if target == current:
        return
    if target not in CONSULTATION_STATUSES:
        raise ValueError("Invalid consultation status")
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid consultation status transition: {current} -> {target}")


def validate_price_amount(amount: Any) -> Decimal:
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Consultation price must be a valid amount") from exc
    if value <= 0 or value > Decimal("100000"):
        raise ValueError("Consultation price must be between 0 and 100000")
    if abs(value.as_tuple().exponent) > 2:
        raise ValueError("Consultation price can have at most two decimal places")
    return value
