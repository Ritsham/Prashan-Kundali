from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.dependencies import AuthState, get_current_user, RequireRole
from app.storage.community_access_db import save_community_application, set_community_membership

router = APIRouter()

class AstrologerApplyRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    whatsapp_no: Optional[str] = None
    experience_years: int
    expertise_areas: List[str]
    bio: Optional[str] = None
    social_links: Optional[dict] = None
    proof_document_name: Optional[str] = None
    proof_document_base64: Optional[str] = None
    proof_document_link: Optional[str] = None
    sample_case_study: Optional[str] = None
    learning_goals: Optional[str] = None

@router.post("/astrologer/apply")
def apply_for_astrologer(req: AstrologerApplyRequest, auth: AuthState = Depends(get_current_user)):
    social_links = req.social_links or {}
    social_links.update({
        "full_name": req.full_name,
        "email": req.email or auth.email,
        "whatsapp_no": req.whatsapp_no,
        "proof_document_name": req.proof_document_name,
        "proof_document_base64": req.proof_document_base64,
        "proof_document_link": req.proof_document_link,
        "sample_case_study": req.sample_case_study,
        "learning_goals": req.learning_goals,
    })
    community_payload = req.model_dump()
    community_payload["social_links"] = social_links
    data = {
        "user_id": auth.user_id,
        "experience_years": req.experience_years,
        "expertise_areas": req.expertise_areas,
        "bio": req.bio,
        "social_links": social_links
    }
    auth.client.table("astrologer_profiles").upsert(data).execute()
    auth.client.table("users").update({
        "role": "astrologer",
        "verification_status": "pending",
        "community_access": False,
    }).eq("id", auth.user_id).execute()
    save_community_application(auth.client, auth.user_id, community_payload)
    return {"status": "success", "message": "Application submitted"}

@router.post("/admin/verify-astrologer")
def verify_astrologer(user_id: str, action: str, auth: AuthState = Depends(RequireRole("admin"))):
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    status = "verified" if action == "approve" else "rejected"
    role = "astrologer" if action == "approve" else "user"
    community_access = action == "approve"
    
    auth.client.table("users").update({
        "verification_status": status,
        "role": role,
        "community_access": community_access,
    }).eq("id", user_id).execute()
    set_community_membership(
        auth.client,
        user_id=user_id,
        active=action == "approve",
        admin_id=auth.user_id,
        reason=f"Admin {action} from verification queue.",
    )
    
    return {"status": "success", "message": f"Astrologer {status}"}

@router.get("/admin/pending-astrologers")
def get_pending_astrologers(auth: AuthState = Depends(RequireRole("admin"))):
    res = auth.client.table("users").select("id, name, email").eq("verification_status", "pending").execute()
    if not res.data:
        return {"pending": []}
        
    user_ids = [u["id"] for u in res.data]
    prof_res = auth.client.table("astrologer_profiles").select("*").in_("user_id", user_ids).execute()
    
    profiles_by_user = {p["user_id"]: p for p in prof_res.data}
    combined = []
    for u in res.data:
        prof = profiles_by_user.get(u["id"], {})
        combined.append({
            "user_id": u["id"],
            "name": u.get("name", "Unknown"),
            "email": u.get("email", ""),
            "experience_years": prof.get("experience_years", 0),
            "expertise_areas": prof.get("expertise_areas", []),
            "bio": prof.get("bio", ""),
            "social_links": prof.get("social_links", {}),
            "created_at": prof.get("created_at"),
            "updated_at": prof.get("updated_at"),
        })
        
    return {"pending": combined}
