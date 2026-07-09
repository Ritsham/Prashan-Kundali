from datetime import datetime, timezone
from typing import Any, Dict, Optional, List


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_community_application(db, user_id: str, payload: Dict[str, Any]) -> bool:
    if not db:
        return False

    now = _now_iso()
    
    # 1. Prepare main application record
    app_data = {
        "user_id": user_id,
        "full_name": payload.get("full_name", ""),
        "email": payload.get("email", ""),
        "mobile_number": payload.get("mobile_number", ""),
        "state": payload.get("state", ""),
        "country": payload.get("country", ""),
        "applicant_type": payload.get("applicant_type", ""),
        "experience_range": payload.get("experience_range", ""),
        "background_description": payload.get("background_description", ""),
        "additional_information": payload.get("additional_information", ""),
        "status": "PENDING",
        "updated_at": now
    }

    try:
        # Upsert application to prevent duplicates
        res = db.table("community_applications").upsert(app_data, on_conflict="user_id").execute()
        if not res.data:
            return False
            
        app_id = res.data[0]["id"]
        
        # 2. Save systems
        systems = payload.get("systems", [])
        if systems:
            # Delete old ones first for safe update
            db.table("community_application_systems").delete().eq("application_id", app_id).execute()
            system_rows = [{"application_id": app_id, "system_name": sys} for sys in systems]
            db.table("community_application_systems").insert(system_rows).execute()
            
        # 3. Save proofs
        proofs = payload.get("proofs", [])
        if proofs:
            db.table("community_application_proofs").delete().eq("application_id", app_id).execute()
            proof_rows = []
            for proof in proofs:
                proof_rows.append({
                    "application_id": app_id,
                    "proof_type": proof.get("type", "other"),
                    "file_url": proof.get("file_url"),
                    "external_url": proof.get("external_url"),
                    "original_file_name": proof.get("original_file_name"),
                    "mime_type": proof.get("mime_type"),
                    "file_size": proof.get("file_size")
                })
            db.table("community_application_proofs").insert(proof_rows).execute()
            
        return True
    except Exception as exc:
        print(f"Warning: save_community_application failed: {exc}")
        return False


def get_community_application(db, user_id: str) -> Optional[Dict[str, Any]]:
    if not db:
        return None
    try:
        res = db.table("community_applications").select("*").eq("user_id", user_id).execute()
        if not res.data:
            return None
        return res.data[0]
    except Exception as exc:
        print(f"Warning: get_community_application failed: {exc}")
        return None


def set_community_membership(
    db,
    user_id: str,
    active: bool,
    admin_id: Optional[str] = None,
    reason: str = "",
) -> bool:
    if not db:
        return False

    now = _now_iso()
    status = "APPROVED" if active else "REJECTED"

    try:
        # Update user table access
        db.table("users").update({
            "community_verification_status": status,
            "community_access": active,
            "community_verified_at": now if active else None,
            "community_suspended_at": now if not active else None,
        }).eq("id", user_id).execute()
        
        # Update application status
        app_res = db.table("community_applications").select("id").eq("user_id", user_id).execute()
        if app_res.data:
            app_id = app_res.data[0]["id"]
            
            update_data = {
                "status": status,
                "reviewed_by": admin_id,
                "reviewed_at": now,
                "updated_at": now
            }
            if active:
                update_data["approved_at"] = now
            else:
                update_data["rejected_at"] = now
                
            db.table("community_applications").update(update_data).eq("id", app_id).execute()
            
            # Log review history
            db.table("community_application_reviews").insert({
                "application_id": app_id,
                "admin_id": admin_id,
                "new_status": status,
                "internal_note": reason
            }).execute()

        return True
    except Exception as exc:
        print(f"Warning: set_community_membership failed: {exc}")
        return False


def has_active_community_membership(db, user_id: str) -> bool:
    if not db:
        return False
    try:
        res = db.table("users").select("community_access").eq("id", user_id).execute()
        if not res.data:
            return False
        return bool(res.data[0].get("community_access"))
    except Exception as exc:
        print(f"Warning: community membership lookup failed: {exc}")
        return False
