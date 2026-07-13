from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import Field
from typing import Annotated, List, Optional
import logging
from app.core.rate_limiter import booking_limiter
from app.dependencies import AuthState, RequireAdmin, get_current_user
from app.schemas.common import ID_RE, PHONE_RE, StrictRequestModel
from app.storage.community_access_db import save_community_application, set_community_membership
from app.storage.database import supabase
from app.storage.audit_db import record_admin_audit

router = APIRouter()
logger = logging.getLogger(__name__)

class AstrologerApplyRequest(StrictRequestModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    email: Optional[str] = Field(default=None, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    whatsapp_no: Optional[str] = Field(default=None, max_length=24, pattern=PHONE_RE)
    experience_years: int = Field(ge=0, le=80)
    expertise_areas: List[str] = Field(min_length=1, max_length=30)
    bio: Optional[str] = Field(default=None, max_length=3000)
    social_links: Optional[dict] = None
    proof_document_name: Optional[str] = Field(default=None, max_length=240)
    proof_document_base64: Optional[str] = Field(default=None, max_length=2_000_000)
    proof_document_link: Optional[str] = Field(default=None, max_length=500)
    sample_case_study: Optional[str] = Field(default=None, max_length=5000)
    learning_goals: Optional[str] = Field(default=None, max_length=3000)


class AstrologerApplicationUpdateRequest(StrictRequestModel):
    status: str = Field(pattern="^(approved|approve|rejected|reject|pending)$")
    note: str = Field(default="", max_length=1000)

@router.post("/astrologer/apply", dependencies=[Depends(booking_limiter)])
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
        "role": "astrologer_pending",
        "verification_status": "pending",
        "community_access": False,
    }).eq("id", auth.user_id).execute()
    save_community_application(auth.client, auth.user_id, community_payload)
    return {"status": "success", "message": "Application submitted"}

@router.post("/admin/verify-astrologer")
def verify_astrologer(user_id: str, action: str, note: str = "", auth: AuthState = Depends(RequireAdmin())):
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    if user_id == auth.user_id:
        raise HTTPException(status_code=403, detail="Admins cannot approve or reject their own astrologer application")
        
    status = "verified" if action == "approve" else "rejected"
    role = "astrologer_verified" if action == "approve" else "user"
    community_access = action == "approve"
    
    db = auth.client or supabase
    before_res = db.table("users").select("id, email, role, verification_status, community_access").eq("id", user_id).limit(1).execute()
    before = before_res.data[0] if before_res.data else None
    if not before:
        raise HTTPException(status_code=404, detail="User not found")
    db.table("users").update({
        "verification_status": status,
        "role": role,
        "community_access": community_access,
    }).eq("id", user_id).execute()
    set_community_membership(
        db,
        user_id=user_id,
        active=action == "approve",
        admin_id=auth.user_id,
        reason=note or f"Admin {action} from verification queue.",
    )
    record_admin_audit(
        actor_user_id=auth.user_id,
        entity_type="astrologer",
        entity_id=user_id,
        action=f"verification_{action}",
        before_json=before,
        after_json={"verification_status": status, "role": role, "community_access": community_access, "note": note},
    )
    
    return {"status": "success", "message": f"Astrologer {status}"}

@router.get("/admin/pending-astrologers")
def get_pending_astrologers(auth: AuthState = Depends(RequireAdmin())):
    try:
        db = auth.client or supabase
        res = db.table("users").select("id, name, email").eq("verification_status", "pending").execute()
        if not res.data:
            return {"pending": []}
            
        user_ids = [u["id"] for u in res.data]
        prof_res = db.table("astrologer_profiles").select("*").in_("user_id", user_ids).execute()
        
        profiles_by_user = {p["user_id"]: p for p in (prof_res.data or [])}
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
    except Exception as exc:
        logger.warning("get_pending_astrologers_failed")
        return {"pending": []}


@router.get("/admin/astrologers/applications")
def get_astrologer_applications_for_admin(auth: AuthState = Depends(RequireAdmin())):
    pending = get_pending_astrologers(auth).get("pending", [])
    applications = []
    for item in pending:
        social = item.get("social_links") or {}
        expertise = item.get("expertise_areas") or []
        applications.append({
            "id": item.get("user_id"),
            "name": social.get("full_name") or item.get("name") or "Unknown",
            "email": social.get("email") or item.get("email") or "",
            "phone": social.get("whatsapp_no") or "",
            "experience": item.get("experience_years") or 0,
            "expertise": ", ".join(expertise) if isinstance(expertise, list) else str(expertise or ""),
            "bio": item.get("bio") or social.get("sample_case_study") or social.get("learning_goals") or "",
            "status": "pending",
            "created_at": item.get("created_at") or item.get("updated_at"),
        })
    return {"applications": applications}


@router.post("/admin/astrologers/applications/{user_id}")
def update_astrologer_application_for_admin(
    user_id: Annotated[str, Path(pattern=ID_RE)],
    payload: AstrologerApplicationUpdateRequest,
    auth: AuthState = Depends(RequireAdmin()),
):
    status = payload.status.lower()
    if status in {"approved", "approve"}:
        return verify_astrologer(user_id=user_id, action="approve", note=payload.note, auth=auth)
    if status in {"rejected", "reject"}:
        return verify_astrologer(user_id=user_id, action="reject", note=payload.note, auth=auth)
    if status == "pending":
        if user_id == auth.user_id:
            raise HTTPException(status_code=403, detail="Admins cannot change their own astrologer application status")
        db = auth.client or supabase
        before_res = db.table("users").select("id, email, role, verification_status, community_access").eq("id", user_id).limit(1).execute()
        before = before_res.data[0] if before_res.data else None
        if not before:
            raise HTTPException(status_code=404, detail="User not found")
        db.table("users").update({
            "role": "astrologer_pending",
            "verification_status": "pending",
            "community_access": False,
        }).eq("id", user_id).execute()
        record_admin_audit(
            actor_user_id=auth.user_id,
            entity_type="astrologer",
            entity_id=user_id,
            action="verification_pending",
            before_json=before,
            after_json={"role": "astrologer_pending", "verification_status": "pending", "community_access": False, "note": payload.note},
        )
        return {"status": "success", "message": "Astrologer application reverted to pending"}
    raise HTTPException(status_code=400, detail="Invalid status")
