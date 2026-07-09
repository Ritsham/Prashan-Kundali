from dotenv import load_dotenv
load_dotenv()

from fastapi import Header, HTTPException, Depends
from supabase import create_client, Client, ClientOptions
import os
from app.storage.community_access_db import has_active_community_membership

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

class AuthState:
    def __init__(self, client: Client, user_id: str, email: str):
        self.client = client
        self.user_id = user_id
        self.email = email

def get_current_user(authorization: str = Header(None)) -> AuthState:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
    token = authorization.split(" ")[1]
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
            
        return AuthState(client=client, user_id=res.user.id, email=res.user.email)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

class RequireRole:
    def __init__(self, role: str):
        self.role = role

    def __call__(self, auth_state: AuthState = Depends(get_current_user)):
        res = auth_state.client.table("users").select("role").eq("id", auth_state.user_id).execute()
        if not res.data or res.data[0].get("role") != self.role:
            raise HTTPException(status_code=403, detail=f"Requires {self.role} role")
        return auth_state

class RequireVerifiedAstrologer:
    def __call__(self, auth_state: AuthState = Depends(get_current_user)):
        membership = has_active_community_membership(auth_state.client, auth_state.user_id)
        if membership is True:
            return auth_state
        if membership is False:
            raise HTTPException(status_code=403, detail="Community access requires active Astro Community membership")

        res = auth_state.client.table("users").select("role, verification_status, community_access").eq("id", auth_state.user_id).execute()
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
