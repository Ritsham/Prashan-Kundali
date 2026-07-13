from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


GENERIC_500_MESSAGE = "Internal server error"


def request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "") or request.headers.get("x-request-id", "")


def error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    details: Any = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def _message_from_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        value = detail.get("message") or detail.get("error") or detail.get("detail")
        if isinstance(value, str):
            return value
    return "Request failed"


def _code_for_status(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        402: "payment_required",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_error",
        502: "upstream_error",
        503: "service_unavailable",
        504: "upstream_timeout",
    }.get(status_code, "request_error")


async def http_exception_handler(request: Request, exc: HTTPException | StarletteHTTPException) -> JSONResponse:
    request_id = request_id_from(request)
    status_code = exc.status_code
    detail = getattr(exc, "detail", None)
    content = error_payload(
        code=_code_for_status(status_code),
        message=_message_from_detail(detail),
        request_id=request_id,
        details=detail if isinstance(detail, (dict, list)) and status_code < 500 else None,
    )
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={**(getattr(exc, "headers", None) or {}), "x-request-id": request_id},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = request_id_from(request)
    details = [
        {
            "loc": list(error.get("loc", [])),
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_payload(
            code="validation_error",
            message="Request validation failed",
            request_id=request_id,
            details=details,
        ),
        headers={"x-request-id": request_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_from(request)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload(
            code="internal_error",
            message=GENERIC_500_MESSAGE,
            request_id=request_id,
        ),
        headers={"x-request-id": request_id},
    )
