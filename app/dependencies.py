from fastapi import Header, HTTPException, Depends, WebSocket
from typing import Any, Optional
from supabase import create_client, Client, ClientOptions
from app.config import get_settings
from app.storage.database import get_service_client

settings = get_settings()
SUPABASE_URL = settings.supabase_url
SUPABASE_ANON_KEY = settings.supabase_anon_key


ROLE_USER = "user"
ROLE_ASTROLOGER_PENDING = "astrologer_pending"
ROLE_ASTROLOGER_VERIFIED = "astrologer_verified"
ROLE_ADMIN = "admin"
VALID_ROLES = {
    ROLE_USER,
    ROLE_ASTROLOGER_PENDING,
    ROLE_ASTROLOGER_VERIFIED,
    ROLE_ADMIN,
}


def _mock_admin_enabled() -> bool:
    return not get_settings().is_production and get_settings().allow_mock_admin_token


def auth_error(message: str = "Authentication required") -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "unauthorized", "message": message})


def permission_error(message: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(status_code=403, detail={"code": "forbidden", "message": message})


def normalize_role(profile: Optional[dict[str, Any]]) -> str:
    if not profile:
        return ROLE_USER

    raw_role = str(profile.get("role") or ROLE_USER).lower()
    verification_status = str(profile.get("verification_status") or "").lower()
    community_status = str(profile.get("community_verification_status") or "").lower()
    community_access = profile.get("community_access") is True

    if raw_role == ROLE_ADMIN:
        return ROLE_ADMIN
    if raw_role in {ROLE_ASTROLOGER_VERIFIED, "verified_astrologer"}:
        return ROLE_ASTROLOGER_VERIFIED
    if raw_role in {ROLE_ASTROLOGER_PENDING, "pending_astrologer"}:
        if verification_status in {"verified", "approved"} or community_status in {"verified", "approved"} or community_access:
            return ROLE_ASTROLOGER_VERIFIED
        return ROLE_ASTROLOGER_PENDING
    if verification_status in {"verified", "approved"} or community_status in {"verified", "approved"} or community_access:
        return ROLE_ASTROLOGER_VERIFIED
    if raw_role == "astrologer":
        if verification_status in {"verified", "approved"} or community_status in {"verified", "approved"} or community_access:
            return ROLE_ASTROLOGER_VERIFIED
        return ROLE_ASTROLOGER_PENDING
    if raw_role in VALID_ROLES:
        return raw_role
    return ROLE_USER


class AuthState:
    def __init__(
        self,
        client: Optional[Client],
        user_id: str,
        email: str,
        user_metadata: Optional[dict] = None,
        role: str = ROLE_USER,
        profile: Optional[dict[str, Any]] = None,
    ):
        self.client = client
        self.user_id = user_id
        self.email = email
        self.user_metadata = user_metadata or {}
        self.role = role
        self.profile = profile or {}

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_verified_astrologer(self) -> bool:
        return self.role == ROLE_ASTROLOGER_VERIFIED


def _load_user_profile(user_id: str, fallback_client: Optional[Client] = None) -> dict[str, Any]:
    db = get_service_client() or fallback_client
    if not db:
        return {}
    profile: dict[str, Any] = {}
    try:
        res = (
            db.table("users")
            .select("id, email, name, full_name, role, verification_status, community_access, community_verification_status")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        profile = dict(res.data[0]) if res.data else {}
    except Exception:
        profile = {}

    if normalize_role(profile) in {ROLE_ADMIN, ROLE_ASTROLOGER_VERIFIED}:
        return profile

    try:
        app_res = (
            db.table("community_applications")
            .select("status")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_status = str((app_res.data[0] if app_res.data else {}).get("status") or "").lower()
        if latest_status in {"approved", "verified"}:
            return {
                **profile,
                "id": profile.get("id") or user_id,
                "role": ROLE_ASTROLOGER_VERIFIED,
                "verification_status": "verified",
                "community_access": True,
                "community_verification_status": "APPROVED",
            }
    except Exception:
        pass

    return profile


def _auth_state_from_user(client: Optional[Client], user: Any) -> AuthState:
    user_metadata = getattr(user, "user_metadata", None) or {}
    app_metadata = getattr(user, "app_metadata", None) or {}
    profile = _load_user_profile(user.id, client)
    profile_role = normalize_role(profile)
    metadata_role = normalize_role({**app_metadata, **user_metadata})
    role = profile_role
    if ROLE_ADMIN in {profile_role, metadata_role}:
        role = ROLE_ADMIN
    elif ROLE_ASTROLOGER_VERIFIED in {profile_role, metadata_role}:
        role = ROLE_ASTROLOGER_VERIFIED
    elif profile_role == ROLE_USER and metadata_role == ROLE_ASTROLOGER_PENDING:
        role = ROLE_ASTROLOGER_PENDING
    return AuthState(
        client=client,
        user_id=user.id,
        email=user.email,
        user_metadata=user_metadata,
        role=role,
        profile={**user_metadata, **app_metadata, **profile},
    )

def get_current_user(authorization: str = Header(None)) -> AuthState:
    if not authorization or not authorization.startswith("Bearer "):
        raise auth_error("Missing or invalid authorization token")
    token = authorization.split(" ")[1]
    
    if token == "mock-admin-token":
        if not _mock_admin_enabled():
            raise auth_error("Invalid token")
        # Local development bypass using service role key
        service_role_key = get_settings().supabase_service_role_key
        if service_role_key:
            import httpx
            timeout = httpx.Timeout(60.0)
            custom_client = httpx.Client(timeout=timeout)
            options = ClientOptions(
                headers={"Authorization": f"Bearer {service_role_key}"},
                httpx_client=custom_client,
            )
            client = create_client(SUPABASE_URL, service_role_key, options=options)
            return AuthState(client=client, user_id="mock-admin", email="admin@local.dev", role=ROLE_ADMIN)
        return AuthState(client=None, user_id="mock-admin", email="admin@local.dev", role=ROLE_ADMIN)
    try:
        # Initialize request-scoped Supabase client with user's JWT token
        import httpx
        timeout = httpx.Timeout(60.0)
        custom_client = httpx.Client(timeout=timeout)
        options = ClientOptions(
            headers={"Authorization": f"Bearer {token}"},
            httpx_client=custom_client,
            storage_client_timeout=120,
            postgrest_client_timeout=120
        )
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=options)
        
        # Verify the token against Supabase auth server
        res = client.auth.get_user(token)
        if not res or not res.user:
            raise auth_error("Invalid token")
            
        return _auth_state_from_user(client, res.user)
    except HTTPException:
        raise
    except Exception:
        raise auth_error("Authentication failed")

def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[AuthState]:
    if not authorization:
        return None
    return get_current_user(authorization)

class RequireRole:
    def __init__(self, role: str):
        self.role = role

    def __call__(self, auth_state: AuthState = Depends(get_current_user)):
        required_role = normalize_role({"role": self.role})
        if auth_state.role != required_role:
            raise permission_error(f"Requires {required_role} role")
        return auth_state


class RequireAnyRole:
    def __init__(self, *roles: str):
        self.roles = {normalize_role({"role": role}) for role in roles}

    def __call__(self, auth_state: AuthState = Depends(get_current_user)):
        if auth_state.role not in self.roles:
            allowed = ", ".join(sorted(self.roles))
            raise permission_error(f"Requires one of: {allowed}")
        return auth_state


class RequireAdmin:
    def __call__(self, auth_state: AuthState = Depends(get_current_user)):
        if not auth_state.is_admin:
            raise permission_error("Admin access required")
        return auth_state


class RequireVerifiedAstrologer:
    def __call__(self, auth_state: AuthState = Depends(get_current_user)):
        if auth_state.role == ROLE_ADMIN or auth_state.role == ROLE_ASTROLOGER_VERIFIED:
            return auth_state
        raise permission_error("Verified astrologer access required")


def get_current_user_from_token(token: str) -> Optional[AuthState]:
    if not token:
        return None
    try:
        import httpx
        custom_client = httpx.Client(timeout=httpx.Timeout(60.0))
        options = ClientOptions(
            headers={"Authorization": f"Bearer {token}"},
            httpx_client=custom_client,
            storage_client_timeout=120,
            postgrest_client_timeout=120,
        )
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=options)
        res = client.auth.get_user(token)
        if not res or not res.user:
            return None
        return _auth_state_from_user(client, res.user)
    except Exception:
        return None


async def close_ws_unauthorized(websocket: WebSocket, reason: str = "Unauthorized") -> None:
    await websocket.close(code=1008, reason=reason[:120])
