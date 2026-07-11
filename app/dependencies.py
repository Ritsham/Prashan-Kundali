from dotenv import load_dotenv
load_dotenv()

from fastapi import Header, HTTPException, Depends
from typing import Optional
from supabase import create_client, Client, ClientOptions
import os
from app.config import get_supabase_url
from app.storage.community_access_db import has_active_community_membership

SUPABASE_URL = get_supabase_url()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

class AuthState:
    def __init__(self, client: Client, user_id: str, email: str, user_metadata: Optional[dict] = None):
        self.client = client
        self.user_id = user_id
        self.email = email
        self.user_metadata = user_metadata or {}

def get_current_user(authorization: str = Header(None)) -> AuthState:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
    token = authorization.split(" ")[1]
    
    if token == "mock-admin-token":
        # Local development bypass using service role key
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if service_role_key:
            import httpx
            timeout = httpx.Timeout(60.0)
            custom_client = httpx.Client(timeout=timeout)
            options = ClientOptions(
                headers={"Authorization": f"Bearer {service_role_key}"},
                httpx_client=custom_client,
            )
            client = create_client(SUPABASE_URL, service_role_key, options=options)
            return AuthState(client=client, user_id="mock-admin", email="admin@local.dev")
        return AuthState(client=None, user_id="mock-admin", email="admin@local.dev")
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
            raise HTTPException(status_code=401, detail="Invalid token")
            
        return AuthState(
            client=client,
            user_id=res.user.id,
            email=res.user.email,
            user_metadata=getattr(res.user, "user_metadata", None) or {},
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[AuthState]:
    if not authorization:
        return None
    return get_current_user(authorization)

class RequireRole:
    def __init__(self, role: str):
        self.role = role

    def __call__(self, auth_state: AuthState = Depends(get_current_user)):
        if auth_state.user_id == "mock-admin" and self.role == "admin":
            return auth_state
            
        res = auth_state.client.table("users").select("role").eq("id", auth_state.user_id).execute()
        if not res.data or res.data[0].get("role") != self.role:
            raise HTTPException(status_code=403, detail=f"Requires {self.role} role")
        return auth_state

class RequireVerifiedAstrologer:
    def __call__(self, auth_state: AuthState = Depends(get_current_user)):
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not service_role_key:
            raise HTTPException(status_code=500, detail="Server misconfiguration: Missing service role key")
            
        import httpx
        custom_client = httpx.Client(timeout=httpx.Timeout(60.0))
        options = ClientOptions(
            headers={"Authorization": f"Bearer {service_role_key}"},
            httpx_client=custom_client,
        )
        admin_client = create_client(SUPABASE_URL, service_role_key, options=options)

        membership = has_active_community_membership(admin_client, auth_state.user_id)
        if membership is True:
            return auth_state
        if membership is False:
            raise HTTPException(status_code=403, detail="Community access requires active Astro Community membership")

        res = admin_client.table("users").select("role, verification_status, community_access").eq("id", auth_state.user_id).execute()
        if not res.data:
            raise HTTPException(status_code=403, detail="Community access denied")

        user = res.data[0]
        is_verified_astrologer = (
            user.get("role") == "astrologer"
            and user.get("verification_status") == "verified"
        )
        
        has_community_access = user.get("community_access") is True
        
        if not is_verified_astrologer and not has_community_access:
            raise HTTPException(status_code=403, detail="Community access requires verified astrologer status or an approved community application")
        return auth_state
