from __future__ import annotations

import sys
import inspect
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dependencies import (
    ROLE_ADMIN,
    ROLE_ASTROLOGER_PENDING,
    ROLE_ASTROLOGER_VERIFIED,
    ROLE_USER,
    AuthState,
    RequireAdmin,
    RequireAnyRole,
    RequireVerifiedAstrologer,
    normalize_role,
)
from app.api import astrologer, community
from app.api.payments import _payment_owner_matches


def auth(role: str) -> AuthState:
    return AuthState(client=None, user_id=f"{role}-id", email=f"{role}@example.com", role=role)


def assert_forbidden(callable_obj, state: AuthState) -> None:
    try:
        callable_obj(state)
    except HTTPException as exc:
        assert exc.status_code == 403, f"expected 403, got {exc.status_code}"
        return
    raise AssertionError(f"expected {state.role} to be forbidden")


def main() -> None:
    assert normalize_role({"role": "user"}) == ROLE_USER
    assert normalize_role({"role": "astrologer", "verification_status": "pending"}) == ROLE_ASTROLOGER_PENDING
    assert normalize_role({"role": "astrologer", "verification_status": "verified"}) == ROLE_ASTROLOGER_VERIFIED
    assert normalize_role({"role": "astrologer_pending"}) == ROLE_ASTROLOGER_PENDING
    assert normalize_role({"role": "astrologer_verified"}) == ROLE_ASTROLOGER_VERIFIED
    assert normalize_role({"role": "admin"}) == ROLE_ADMIN

    assert RequireAdmin()(auth(ROLE_ADMIN)).role == ROLE_ADMIN
    assert_forbidden(RequireAdmin(), auth(ROLE_USER))
    assert_forbidden(RequireAdmin(), auth(ROLE_ASTROLOGER_VERIFIED))

    assert RequireVerifiedAstrologer()(auth(ROLE_ASTROLOGER_VERIFIED)).role == ROLE_ASTROLOGER_VERIFIED
    assert RequireVerifiedAstrologer()(auth(ROLE_ADMIN)).role == ROLE_ADMIN
    assert_forbidden(RequireVerifiedAstrologer(), auth(ROLE_USER))
    assert_forbidden(RequireVerifiedAstrologer(), auth(ROLE_ASTROLOGER_PENDING))

    user_or_admin = RequireAnyRole(ROLE_USER, ROLE_ADMIN)
    assert user_or_admin(auth(ROLE_USER)).role == ROLE_USER
    assert user_or_admin(auth(ROLE_ADMIN)).role == ROLE_ADMIN
    assert_forbidden(user_or_admin, auth(ROLE_ASTROLOGER_PENDING))

    astrologer_verify_source = inspect.getsource(astrologer.verify_astrologer)
    assert "user_id == auth.user_id" in astrologer_verify_source
    assert "Admins cannot approve or reject their own astrologer application" in astrologer_verify_source
    assert "record_admin_audit" in astrologer_verify_source

    community_status_source = inspect.getsource(community.admin_update_application_status)
    assert "user_id == auth.user_id" in community_status_source
    assert "Admins cannot approve or reject their own application" in community_status_source
    assert "record_admin_audit" in community_status_source
    assert "except HTTPException" in community_status_source

    owned_payment = {"user_id": "user-id"}
    other_payment = {"user_id": "other-user-id"}
    guest_payment = {"user_id": None}
    assert _payment_owner_matches(owned_payment, auth(ROLE_USER))
    assert not _payment_owner_matches(other_payment, auth(ROLE_USER))
    assert not _payment_owner_matches(owned_payment, None)
    assert _payment_owner_matches(other_payment, auth(ROLE_ADMIN))
    assert _payment_owner_matches(guest_payment, None)

    print("access_control_ok")


if __name__ == "__main__":
    main()
