from dotenv import load_dotenv
load_dotenv()

from fastapi import Header, HTTPException, Depends
from supabase import create_client, Client, ClientOptions
import os

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
        options = ClientOptions(headers={"Authorization": f"Bearer {token}"})
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
        res = auth_state.client.table("users").select("role, verification_status, community_access").eq("id", auth_state.user_id).execute()
        if not res.data:
            raise HTTPException(status_code=403, detail="Community access requires verified astrologer status")

        user = res.data[0]
        is_verified_astrologer = (
            user.get("role") == "astrologer"
            and user.get("verification_status") == "verified"
            and bool(user.get("community_access", True))
        )
        if not is_verified_astrologer:
            raise HTTPException(status_code=403, detail="Community access requires verified astrologer status")
        return auth_state
