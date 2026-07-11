from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from typing import Dict, List, Optional
import json
import logging
import os
from supabase import create_client, ClientOptions

from app.config import get_supabase_url
from app.storage.community_db import (
    get_channels,
    save_message,
    get_messages,
    delete_message,
    update_message,
    star_message,
    save_thread_reply,
    get_thread_replies,
    toggle_reaction,
    set_saved_message,
    get_saved_messages,
    mark_channel_read,
    update_message_author_name,
)
from app.dependencies import AuthState, RequireVerifiedAstrologer, get_current_user
from app.storage.community_access_db import has_active_community_membership

router = APIRouter(prefix="/community", tags=["community"])

logger = logging.getLogger(__name__)


def get_websocket_auth_context(token: str) -> Optional[Dict[str, str]]:
    if not token:
        return None
    try:
        import httpx
        timeout = httpx.Timeout(60.0)
        custom_client = httpx.Client(timeout=timeout)
        options = ClientOptions(
            headers={"Authorization": f"Bearer {token}"},
            httpx_client=custom_client,
            storage_client_timeout=120,
            postgrest_client_timeout=120
        )
        client = create_client(get_supabase_url(), os.getenv("SUPABASE_ANON_KEY", ""), options=options)
        user_res = client.auth.get_user(token)
        if not user_res or not user_res.user:
            return None

        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not service_role_key:
            logger.error("Community websocket auth failed: missing SUPABASE_SERVICE_ROLE_KEY")
            return None
        admin_options = ClientOptions(
            headers={"Authorization": f"Bearer {service_role_key}"},
            httpx_client=httpx.Client(timeout=httpx.Timeout(60.0)),
        )
        admin_client = create_client(get_supabase_url(), service_role_key, options=admin_options)

        membership = has_active_community_membership(admin_client, user_res.user.id)
        if membership is not None:
            if not membership:
                return None
            metadata = getattr(user_res.user, "user_metadata", None) or {}
            return {
                "user_id": user_res.user.id,
                "display_name": metadata.get("full_name") or metadata.get("name") or (user_res.user.email or "Astrologer").split("@")[0],
            }
        profile_res = admin_client.table("users").select("full_name, role, verification_status, community_access").eq("id", user_res.user.id).execute()
        if not profile_res.data:
            return None
        profile = profile_res.data[0]
        
        is_verified_astrologer = (
            profile.get("role") == "astrologer"
            and profile.get("verification_status") == "verified"
        )
        has_community_access = profile.get("community_access") is True
        if not is_verified_astrologer and not has_community_access:
            return None

        return {
            "user_id": user_res.user.id,
            "display_name": profile.get("full_name") or (getattr(user_res.user, "user_metadata", None) or {}).get("full_name") or (getattr(user_res.user, "user_metadata", None) or {}).get("name") or (user_res.user.email or "Astrologer").split("@")[0],
        }
    except Exception as exc:
        logger.error("Community websocket auth failed: %s", exc)
        return None


def websocket_has_verified_access(token: str) -> bool:
    return get_websocket_auth_context(token) is not None


def resolve_display_name(auth: AuthState) -> str:
    try:
        res = auth.client.table("users").select("full_name,email").eq("id", auth.user_id).limit(1).execute()
        if res.data:
            user = res.data[0]
            metadata_name = auth.user_metadata.get("full_name") or auth.user_metadata.get("name")
            return user.get("full_name") or metadata_name or (user.get("email") or auth.email or auth.user_id).split("@")[0]
    except Exception as exc:
        logger.error("Community display name lookup failed: %s", exc)
    return auth.user_metadata.get("full_name") or auth.user_metadata.get("name") or (auth.email or auth.user_id).split("@")[0]

class ConnectionManager:
    def __init__(self):
        # Maps channel names to a list of active websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.total_connections: int = 0

    async def connect(self, websocket: WebSocket, channel_name: str):
        await websocket.accept()
        if channel_name not in self.active_connections:
            self.active_connections[channel_name] = []
        self.active_connections[channel_name].append(websocket)
        self.total_connections += 1
        # Send the count directly to this socket first (guaranteed delivery)
        await websocket.send_text(json.dumps({"type": "online_count", "count": self.total_connections}))
        # Also broadcast to all others
        await self.broadcast_all(json.dumps({"type": "online_count", "count": self.total_connections}))

    async def disconnect(self, websocket: WebSocket, channel_name: str):
        if channel_name in self.active_connections and websocket in self.active_connections[channel_name]:
            self.active_connections[channel_name].remove(websocket)
            self.total_connections = max(0, self.total_connections - 1)
            await self.broadcast_all(json.dumps({"type": "online_count", "count": self.total_connections}))

    async def broadcast(self, message: str, channel_name: str):
        if channel_name in self.active_connections:
            for connection in self.active_connections[channel_name]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending message to websocket: {e}")

    async def broadcast_all(self, message: str):
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending message to websocket: {e}")

manager = ConnectionManager()


@router.get("/channels")
async def api_get_channels(auth: AuthState = Depends(RequireVerifiedAstrologer())):
    return await get_channels()


@router.get("/messages/{channel_name}")
async def api_get_messages(
    channel_name: str,
    limit: int = 50,
    cursor: str = None,
    search: str = None,
    auth: AuthState = Depends(RequireVerifiedAstrologer()),
):
    return await get_messages(channel_name, limit, cursor, search)


from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
import uuid
import mimetypes

@router.get("/threads/{message_id}")
async def api_get_threads(message_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    return await get_thread_replies(message_id)


class ApplicationPayload(BaseModel):
    full_name: str
    email: str
    mobile_number: str
    state: str
    country: str
    applicant_type: str
    experience_range: str
    systems: List[str]
    background_description: str
    proofs: List[Dict]
    additional_information: str = ""

@router.get("/application/status")
async def get_application_status(auth: AuthState = Depends(get_current_user)):
    from app.storage.community_access_db import get_community_application
    app_data = get_community_application(auth.client, auth.user_id)
    if not app_data:
        return {"status": "NOT_APPLIED"}
    return app_data

@router.post("/application")
async def submit_application(payload: ApplicationPayload, auth: AuthState = Depends(get_current_user)):
    from app.storage.community_access_db import save_community_application, get_community_application
    
    # Check if already applied and not allowed to reapply
    existing = get_community_application(auth.client, auth.user_id)
    if existing and existing.get("status") not in ["REJECTED", "NOT_APPLIED"] and not existing.get("reapply_allowed"):
        raise HTTPException(status_code=400, detail="Application already submitted or pending.")
        
    if not payload.proofs:
        raise HTTPException(status_code=400, detail="At least one supporting proof is required.")
        
    success = save_community_application(auth.client, auth.user_id, payload.model_dump())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to submit application.")
    return {"message": "Application submitted successfully", "status": "PENDING"}

@router.post("/application/upload-proof")
async def upload_proof(file: UploadFile = File(...), auth: AuthState = Depends(get_current_user)):
    MAX_SIZE = 10 * 1024 * 1024 # 10MB
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")
        
    mime_type, _ = mimetypes.guess_type(file.filename)
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if mime_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF, JPG, JPEG, and PNG are allowed.")
        
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
    safe_filename = f"{auth.user_id}/{uuid.uuid4().hex}.{ext}"
    
    try:
        bucket = auth.client.storage.from_("community-proofs")
        bucket.upload(safe_filename, contents, {"content-type": mime_type})
        # Generate signed URL or just return path
        # Using path so frontend doesn't expose signed URL forever, we generate signed URLs on demand for admins
        return {
            "file_url": safe_filename,
            "original_file_name": file.filename,
            "mime_type": mime_type,
            "file_size": len(contents)
        }
    except Exception as exc:
        logger.error(f"Failed to upload proof: {exc}")
        raise HTTPException(status_code=500, detail="Failed to upload file.")

class MoreInfoPayload(BaseModel):
    response_text: str
    proof: Optional[Dict] = None

@router.post("/application/more-info")
async def submit_more_info(payload: MoreInfoPayload, auth: AuthState = Depends(get_current_user)):
    from app.storage.community_access_db import get_community_application
    app_data = get_community_application(auth.client, auth.user_id)
    if not app_data or app_data.get("status") != "NEEDS_MORE_INFORMATION":
        raise HTTPException(status_code=400, detail="Application is not in NEEDS_MORE_INFORMATION state.")
        
    app_id = app_data["id"]
    
    try:
        # Update status back to PENDING and append to applicant_facing_message or internal notes
        # In a real app we'd save the response text to a history table, but we will append it for now
        update_data = {
            "status": "PENDING",
            "updated_at": "now()"
        }
        auth.client.table("community_applications").update(update_data).eq("id", app_id).execute()
        
        # Save additional proof if provided
        if payload.proof:
            proof_data = {
                "application_id": app_id,
                "proof_type": payload.proof.get("type", "Additional Information"),
                "file_url": payload.proof.get("file_url"),
                "external_url": payload.proof.get("external_url"),
                "original_file_name": payload.proof.get("original_file_name"),
                "mime_type": payload.proof.get("mime_type"),
                "file_size": payload.proof.get("file_size")
            }
            auth.client.table("community_application_proofs").insert(proof_data).execute()
            
        # Log response in reviews table
        auth.client.table("community_application_reviews").insert({
            "application_id": app_id,
            "admin_id": auth.user_id, # using user's id to denote they submitted it, or leave null
            "previous_status": "NEEDS_MORE_INFORMATION",
            "new_status": "PENDING",
            "applicant_message": payload.response_text
        }).execute()
        
        return {"message": "Information submitted successfully"}
    except Exception as exc:
        logger.error(f"Failed to submit more info: {exc}")
        raise HTTPException(status_code=500, detail="Failed to submit additional information.")

@router.websocket("/ws/{channel_name}")
async def websocket_endpoint(websocket: WebSocket, channel_name: str):
    token = websocket.query_params.get("token", "")
    auth_context = get_websocket_auth_context(token)
    if not auth_context:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, channel_name)
    await websocket.send_text(json.dumps({"type": "connection_ready", "channel_name": channel_name}))
    await websocket.send_text(json.dumps({"type": "channel_subscribed", "channel_name": channel_name}))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action")
                
                if action == "send_message":
                    if channel_name == "announcements":
                        await websocket.send_text(json.dumps({"type": "error", "message": "Only admins can post in announcements."}))
                        continue
                    
                    saved_msg = await save_message(
                        channel_name=channel_name,
                        user_name=auth_context["display_name"],
                        content=payload.get("content", ""),
                        image_base64=payload.get("image_base64"),
                        content_type=payload.get("content_type", "STANDARD"),
                        chart_id=payload.get("chart_id"),
                        sender_id=auth_context["user_id"],
                        reply_to_message_id=payload.get("reply_to_message_id"),
                        client_id=payload.get("client_id"),
                    )
                    await manager.broadcast(
                        json.dumps({"type": "message_created", "data": saved_msg}), 
                        channel_name
                    )
                
                
                elif action == "toggle_reaction":
                    msg_id = payload.get("message_id")
                    reaction_type = payload.get("reaction_type")
                    user_id = auth_context["user_id"]
                    added = await toggle_reaction(msg_id, user_id, reaction_type)
                    await manager.broadcast(
                        json.dumps({"type": "reaction_added" if added else "reaction_removed", "message_id": msg_id, "reaction_type": reaction_type, "user_id": user_id}),
                        channel_name
                    )

                elif action == "delete_message":
                    msg_id = payload.get("message_id")
                    await delete_message(msg_id, auth_context["user_id"])
                    await manager.broadcast(
                        json.dumps({"type": "message_deleted", "message_id": msg_id}),
                        channel_name
                    )
                    
                elif action == "star_message":
                    msg_id = payload.get("message_id")
                    await star_message(msg_id)
                    await manager.broadcast(
                        json.dumps({"type": "reaction_added", "message_id": msg_id, "reaction_type": "star"}),
                        channel_name
                    )
                    
                elif action == "send_thread_reply":
                    saved_reply = await save_thread_reply(
                        parent_message_id=payload.get("parent_message_id"),
                        user_name=auth_context["display_name"],
                        content=payload.get("content", ""),
                        image_base64=payload.get("image_base64"),
                        sender_id=auth_context["user_id"],
                    )
                    await manager.broadcast(
                        json.dumps({"type": "thread_reply_created", "data": saved_reply}),
                        channel_name
                    )
                elif action == "typing_started":
                    await manager.broadcast(json.dumps({"type": "typing_started", "user_id": auth_context["user_id"], "display_name": auth_context["display_name"]}), channel_name)
                elif action == "typing_stopped":
                    await manager.broadcast(json.dumps({"type": "typing_stopped", "user_id": auth_context["user_id"], "display_name": auth_context["display_name"]}), channel_name)
            except json.JSONDecodeError:
                logger.error("Received non-JSON message over websocket")
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel_name)

from app.dependencies import RequireRole

@router.get("/admin/applications")
async def admin_list_applications(auth: AuthState = Depends(RequireRole("admin"))):
    try:
        app_res = auth.client.table("community_applications").select("*, community_application_systems(system_name), community_application_proofs(*)").order("created_at", desc=True).execute()
        apps = app_res.data
        
        for app in apps:
            app["systems"] = [s["system_name"] for s in app.get("community_application_systems", [])]
            app["proofs_count"] = len(app.get("community_application_proofs", []))
            app["proofs"] = app.get("community_application_proofs", [])
            
        return apps
    except Exception as exc:
        logger.error(f"Failed to list admin applications: {exc}")
        raise HTTPException(status_code=500, detail="Failed to list applications.")

@router.get("/admin/applications/{app_id}")
async def admin_get_application(app_id: str, auth: AuthState = Depends(RequireRole("admin"))):
    try:
        app_res = auth.client.table("community_applications").select("*").eq("id", app_id).execute()
        if not app_res.data:
            raise HTTPException(status_code=404, detail="Application not found.")
        app_data = app_res.data[0]
        
        sys_res = auth.client.table("community_application_systems").select("system_name").eq("application_id", app_id).execute()
        app_data["systems"] = [s["system_name"] for s in sys_res.data]
        
        proof_res = auth.client.table("community_application_proofs").select("*").eq("application_id", app_id).execute()
        app_data["proofs"] = proof_res.data
        
        review_res = auth.client.table("community_application_reviews").select("*").eq("application_id", app_id).order("created_at", desc=True).execute()
        app_data["reviews"] = review_res.data
        
        return app_data
    except Exception as exc:
        logger.error(f"Failed to get application detail: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get application detail.")

class AdminStatusUpdatePayload(BaseModel):
    status: str
    message: str = ""
    reapply_allowed: bool = False
    reapply_after_days: int = 30

@router.post("/admin/applications/{app_id}/status")
async def admin_update_application_status(app_id: str, payload: AdminStatusUpdatePayload, auth: AuthState = Depends(RequireRole("admin"))):
    try:
        # Get current app state
        app_res = auth.client.table("community_applications").select("status", "user_id").eq("id", app_id).execute()
        if not app_res.data:
            raise HTTPException(status_code=404, detail="Application not found")
            
        current_status = app_res.data[0]["status"]
        user_id = app_res.data[0]["user_id"]
        
        from datetime import datetime, timedelta
        
        update_data = {
            "status": payload.status,
            "updated_at": "now()",
            "applicant_facing_message": payload.message if payload.message else None,
            "reapply_allowed": payload.reapply_allowed,
            "reapply_after": (datetime.utcnow() + timedelta(days=payload.reapply_after_days)).isoformat() if payload.reapply_allowed else None
        }
        
        auth.client.table("community_applications").update(update_data).eq("id", app_id).execute()
        
        # Validate admin_id is UUID (since mock-admin token sets it to non-UUID)
        import uuid
        try:
            uuid.UUID(str(auth.user_id))
            admin_uuid = auth.user_id
        except ValueError:
            admin_uuid = "00000000-0000-0000-0000-000000000000"

        # Log the review
        auth.client.table("community_application_reviews").insert({
            "application_id": app_id,
            "admin_id": admin_uuid,
            "previous_status": current_status,
            "new_status": payload.status,
            "internal_note": payload.message
        }).execute()
        
        # If APPROVED, update user's community_access
        if payload.status == "APPROVED":
            auth.client.table("users").update({"community_access": True}).eq("id", user_id).execute()
        elif payload.status in ["SUSPENDED", "REJECTED"]:
            auth.client.table("users").update({"community_access": False}).eq("id", user_id).execute()
            
        # Send WhatsApp Notification
        try:
            from app.services.whatsapp import send_whatsapp_message
            mobile_number = app_res.data[0].get("mobile_number")
            # If mobile_number isn't in app_res because we only selected status and user_id earlier, we need to fetch it
            if not mobile_number:
                full_app = auth.client.table("community_applications").select("mobile_number").eq("id", app_id).execute()
                mobile_number = full_app.data[0].get("mobile_number") if full_app.data else None
                
            if mobile_number:
                msg = None
                if payload.status == "APPROVED":
                    msg = "Your application for the Astrologer Community has been approved. You can now access the community."
                elif payload.status == "NEEDS_MORE_INFORMATION":
                    msg = "We need a bit more information to verify your application. Please check your application status page."
                elif payload.status == "REJECTED":
                    msg = "Your application for the community was not approved at this time. Please check your status page for details."
                    
                if msg:
                    send_whatsapp_message(mobile_number, msg)
        except Exception as wa_exc:
            logger.error(f"Failed to send WhatsApp notification: {wa_exc}")
            
        return {"message": f"Application status updated to {payload.status}"}
    except Exception as exc:
        logger.error(f"Failed to update application status: {exc}")
        import traceback
        raise HTTPException(status_code=500, detail=f"Failed to update application status: {str(exc)}\n{traceback.format_exc()}")


@router.get("/admin/astrologers/applications")
async def admin_list_astrologer_applications_compat(auth: AuthState = Depends(RequireRole("admin"))):
    apps = await admin_list_applications(auth)
    formatted = []
    for app in apps:
        systems = app.get("systems") or app.get("expertise_areas") or []
        if isinstance(systems, str):
            expertise = systems
        else:
            expertise = ", ".join(systems)
            
        proofs = []
        for proof in app.get("proofs") or []:
            file_url = proof.get("file_url")
            if file_url and not file_url.startswith("http"):
                try:
                    signed = auth.client.storage.from_("community-proofs").create_signed_url(file_url, 3600 * 24)
                    file_url = signed.get("signedURL") or signed.get("signedUrl")
                except Exception as e:
                    logger.error(f"Failed to sign URL for {file_url}: {e}")
            proofs.append({
                "id": proof.get("id"),
                "type": proof.get("proof_type"),
                "url": file_url,
                "filename": proof.get("original_file_name"),
                "mime_type": proof.get("mime_type")
            })

        formatted.append({
            "id": app.get("id"),
            "name": app.get("full_name") or app.get("name") or app.get("display_name") or "Unknown",
            "email": app.get("email") or "",
            "phone": app.get("mobile_number") or app.get("whatsapp_no") or app.get("phone") or "",
            "experience": app.get("experience_years") or app.get("experience_range") or app.get("experience") or 0,
            "expertise": expertise,
            "bio": app.get("background_description") or app.get("bio") or app.get("sample_case_study") or app.get("learning_goals") or "",
            "additional_information": app.get("additional_information") or "",
            "state": app.get("state") or "",
            "country": app.get("country") or "",
            "status": str(app.get("status") or "pending").lower(),
            "proofs": proofs,
            "created_at": app.get("created_at") or app.get("submitted_at"),
        })
    return {"applications": formatted}


class AstrologerApplicationCompatUpdate(BaseModel):
    status: str


@router.post("/admin/astrologers/applications/{app_id}")
async def admin_update_astrologer_application_compat(
    app_id: str,
    payload: AstrologerApplicationCompatUpdate,
    auth: AuthState = Depends(RequireRole("admin")),
):
    status_map = {
        "approved": "APPROVED",
        "approve": "APPROVED",
        "rejected": "REJECTED",
        "reject": "REJECTED",
        "pending": "SUBMITTED",
        "submitted": "SUBMITTED",
    }
    target = status_map.get(payload.status.lower(), payload.status.upper())
    return await admin_update_application_status(
        app_id,
        AdminStatusUpdatePayload(status=target),
        auth,
    )

@router.get("/profile")
async def api_get_profile(auth: AuthState = Depends(RequireVerifiedAstrologer())):
    """Return a minimal profile object so the frontend knows the user has access.
    We derive the profile from the users table since community_profiles may not exist yet."""
    try:
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        import httpx
        custom_client = httpx.Client(timeout=httpx.Timeout(60.0))
        options = ClientOptions(
            headers={"Authorization": f"Bearer {service_role_key}"},
            httpx_client=custom_client,
        )
        admin_client = create_client(get_supabase_url(), service_role_key, options=options)

        res = admin_client.table("users").select(
            "id, email, full_name, role, verification_status, community_access, community_verification_status"
        ).eq("id", auth.user_id).execute()
        if not res.data:
            return None
        u = res.data[0]
        is_verified_astrologer = (
            u.get("role") == "astrologer"
            and u.get("verification_status") == "verified"
        )
        has_community_access = u.get("community_access") is True
        if not is_verified_astrologer and not has_community_access:
            return None
        email_name = u.get("email", "").split("@")[0]
        metadata_name = auth.user_metadata.get("full_name") or auth.user_metadata.get("name")
        display_name = u.get("full_name") or metadata_name or email_name
        await update_message_author_name(
            auth.user_id,
            display_name,
            [email_name, auth.user_metadata.get("preferred_username", ""), auth.user_metadata.get("user_name", "")],
        )
        # Return a profile-shaped object so the frontend proceeds to workspace
        return {
            "user_id": u["id"],
            "display_name": display_name,
            "username": email_name,
            "bio": "",
            "community_access": True,
            "role": u.get("role") or "verified_astrologer",
            "verification_status": u.get("verification_status") or u.get("community_verification_status"),
        }
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return None

class ProfilePayload(BaseModel):
    username: str
    display_name: str
    bio: str
    state: str = ""
    country: str = ""
    experience_years: str = ""
    specializations: List[str] = []
    languages: List[str] = []
    systems_practiced: List[str] = []

@router.post("/profile")
async def api_upsert_profile(payload: ProfilePayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    """Save community profile — stored in users table metadata for now."""
    try:
        # Store display name back to users table
        auth.client.table("users").update({
            "full_name": payload.display_name
        }).eq("id", auth.user_id).execute()
        return {"status": "success", "profile": {"user_id": auth.user_id, "display_name": payload.display_name}}
    except Exception as e:
        logger.error(f"Error upserting profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to save profile.")

@router.post("/channels/{channel_id}/join")
async def api_join_channel(channel_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        auth.client.table("channel_memberships").insert({
            "channel_id": channel_id,
            "user_id": auth.user_id,
            "role": "MEMBER"
        }).execute()
        return {"status": "joined"}
    except Exception as e:
        logger.error(f"Error joining channel: {e}")
        raise HTTPException(status_code=500, detail="Failed to join channel.")


from app.storage.community_db import toggle_reaction
class ReactionPayload(BaseModel):
    reaction_type: str

@router.post("/messages/{message_id}/reactions")
async def api_toggle_reaction(message_id: str, payload: ReactionPayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        added = await toggle_reaction(message_id, auth.user_id, payload.reaction_type)
        return {"status": "success", "added": added}
    except Exception as e:
        logger.error(f"Error toggling reaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle reaction.")


from app.storage.community_db import toggle_thread_follow


from app.storage.community_db import get_thread_replies


from app.storage.community_db import save_message

class SendMessagePayload(BaseModel):
    content: str
    content_type: str = "STANDARD"
    chart_id: Optional[str] = None
    image_base64: Optional[str] = None
    reply_to_message_id: Optional[str] = None
    client_id: Optional[str] = None


class UpdateMessagePayload(BaseModel):
    content: str


class ThreadReplyPayload(BaseModel):
    content: str
    image_base64: Optional[str] = None


class ReadStatePayload(BaseModel):
    last_read_message_id: Optional[str] = None


class AdminCommunityMessagePayload(BaseModel):
    content: str
    content_type: str = "STANDARD"
    image_base64: Optional[str] = None


class AdminCommunityBroadcastPayload(BaseModel):
    channel_name: str
    title: Optional[str] = None
    body: Optional[str] = None
    link_url: Optional[str] = None
    link_label: Optional[str] = None
    image_base64: Optional[str] = None


from app.storage.community_db import get_community_members, get_community_member, report_message
from typing import Optional

@router.get("/members")
async def api_get_members(query: Optional[str] = None, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        return await get_community_members(query)
    except Exception as e:
        logger.error(f"Error fetching members: {e}")
        return []

@router.get("/members/{user_id}")
async def api_get_member(user_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        member = await get_community_member(user_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        return member
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching member: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch member")

class ReportPayload(BaseModel):
    reason: str

@router.post("/messages/{message_id}/report")
async def api_report_message(message_id: str, payload: ReportPayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        success = await report_message(message_id, auth.user_id, payload.reason)
        return {"status": "success" if success else "failed"}
    except Exception as e:
        logger.error(f"Error reporting message: {e}")
        raise HTTPException(status_code=500, detail="Failed to report message")


from app.storage.community_db import get_notifications, mark_notifications_read, get_community_reports, delete_community_message, ban_community_user

@router.get("/notifications")
async def api_get_notifications(auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        return await get_notifications(auth.user_id)
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return []

@router.post("/notifications/read")
async def api_read_notifications(auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        success = await mark_notifications_read(auth.user_id)
        return {"status": "success" if success else "failed"}
    except Exception as e:
        logger.error(f"Error marking notifications read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notifications read")

@router.get("/admin/reports")
async def api_get_reports(auth: AuthState = Depends(RequireRole("admin"))):
    try:
        return await get_community_reports()
    except Exception as e:
        logger.error(f"Error fetching reports: {e}")
        return []

@router.delete("/admin/messages/{message_id}")
async def api_admin_delete_message(message_id: str, auth: AuthState = Depends(RequireRole("admin"))):
    try:
        success = await delete_community_message(message_id)
        if success:
            # Broadcast deletion so clients remove it
            await manager.broadcast(
                json.dumps({"type": "message_deleted", "message_id": message_id}),
                "admin-broadcast" # Note: actual implementation would need channel name, this is a stub
            )
        return {"status": "success" if success else "failed"}
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete message")

@router.post("/admin/users/{user_id}/ban")
async def api_admin_ban_user(user_id: str, auth: AuthState = Depends(RequireRole("admin"))):
    try:
        success = await ban_community_user(user_id)
        return {"status": "success" if success else "failed"}
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        raise HTTPException(status_code=500, detail="Failed to ban user")


@router.post("/admin/messages/{channel_name}")
async def api_admin_send_channel_message(
    channel_name: str,
    payload: AdminCommunityMessagePayload,
    auth: AuthState = Depends(RequireRole("admin")),
):
    if channel_name not in {"announcements", "general"}:
        raise HTTPException(status_code=400, detail="Admin can post only to announcements or general.")
    content = payload.content.strip()
    if not content and not payload.image_base64:
        raise HTTPException(status_code=400, detail="Message content is required.")
    try:
        saved_msg = await save_message(
            channel_name=channel_name,
            user_name="Kundali Admin",
            content=content,
            image_base64=payload.image_base64,
            content_type=payload.content_type,
            sender_id=auth.user_id,
            client_id=f"admin-{channel_name}-{uuid.uuid4().hex}",
        )
        await manager.broadcast(
            json.dumps({"type": "message_created", "data": saved_msg, "message": saved_msg}),
            channel_name,
        )
        return {"status": "success", "message": saved_msg}
    except Exception as e:
        logger.error(f"Error sending admin community message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send community message")


@router.post("/admin/broadcast")
async def api_admin_broadcast_message(
    payload: AdminCommunityBroadcastPayload,
    auth: AuthState = Depends(RequireRole("admin")),
):
    channel_name = payload.channel_name.strip()
    if channel_name not in {"announcements", "general"}:
        raise HTTPException(status_code=400, detail="Admin can post only to announcements or general.")

    title = (payload.title or "").strip()
    body = (payload.body or "").strip()
    link_url = (payload.link_url or "").strip()
    link_label = (payload.link_label or "").strip()

    if not title and not body and not link_url and not payload.image_base64:
        raise HTTPException(status_code=400, detail="Add a title, message, link, or image before broadcasting.")

    post_content = json.dumps({
        "title": title,
        "body": body,
        "link_url": link_url,
        "link_label": link_label or link_url,
    })

    try:
        saved_msg = await save_message(
            channel_name=channel_name,
            user_name="Kundali Admin",
            content=post_content,
            image_base64=payload.image_base64,
            content_type="ADMIN_POST",
            sender_id=auth.user_id,
            client_id=f"admin-post-{channel_name}-{uuid.uuid4().hex}",
        )
        await manager.broadcast(
            json.dumps({"type": "message_created", "data": saved_msg, "message": saved_msg}),
            channel_name,
        )
        return {"status": "success", "message": saved_msg}
    except Exception as e:
        logger.error(f"Error broadcasting admin community post: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast community post")


@router.post("/messages/{channel_name}")
async def api_send_message(channel_name: str, payload: SendMessagePayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    if channel_name == "announcements":
        raise HTTPException(status_code=403, detail="Only admins can post in announcements.")
    try:
        display_name = resolve_display_name(auth)
        saved_msg = await save_message(
            channel_name=channel_name,
            user_name=display_name,
            content=payload.content,
            image_base64=payload.image_base64,
            content_type=payload.content_type,
            chart_id=payload.chart_id,
            sender_id=auth.user_id,
            reply_to_message_id=payload.reply_to_message_id,
            client_id=payload.client_id,
        )
        
        # Broadcast the new message via WS
        await manager.broadcast(
            json.dumps({"type": "message_created", "data": saved_msg, "message": saved_msg}),
            channel_name
        )
        
        return {"status": "success", "message": saved_msg}
    except Exception as e:
        logger.error(f"Error sending message via POST: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message.")


@router.patch("/messages/{message_id}")
async def api_update_message(message_id: str, payload: UpdateMessagePayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        updated = await update_message(message_id, auth.user_id, payload.content)
        if not updated:
            raise HTTPException(status_code=404, detail="Message not found or not editable.")
        await manager.broadcast(
            json.dumps({"type": "message_updated", "data": updated, "message_id": message_id}),
            updated.get("channel_name", "")
        )
        return {"status": "success", "message": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message: {e}")
        raise HTTPException(status_code=500, detail="Failed to update message.")


@router.delete("/messages/{message_id}")
async def api_delete_message(message_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        deleted = await delete_message(message_id, auth.user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Message not found or not deletable.")
        await manager.broadcast(
            json.dumps({"type": "message_deleted", "message_id": message_id, "data": deleted}),
            deleted.get("channel_name", "")
        )
        return {"status": "success", "message": deleted}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete message.")


@router.post("/messages/{message_id}/save")
async def api_save_message(message_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        saved = await set_saved_message(message_id, auth.user_id)
        return {"status": "success", "saved": saved, "message_id": message_id}
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        raise HTTPException(status_code=500, detail="Failed to save message.")


@router.get("/saved-messages")
async def api_get_saved_messages(auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        return await get_saved_messages(auth.user_id)
    except Exception as e:
        logger.error(f"Error fetching saved messages: {e}")
        # Return 503 so the frontend knows the DB is unavailable and keeps its local cache
        raise HTTPException(status_code=503, detail="Saved messages temporarily unavailable")


@router.post("/channels/{channel_name}/read")
async def api_mark_channel_read(channel_name: str, payload: ReadStatePayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        success = await mark_channel_read(channel_name, auth.user_id, payload.last_read_message_id)
        if success:
            await manager.broadcast(
                json.dumps({
                    "type": "read_state_updated",
                    "channel_name": channel_name,
                    "user_id": auth.user_id,
                    "last_read_message_id": payload.last_read_message_id,
                }),
                channel_name,
            )
        return {"status": "success" if success else "failed"}
    except Exception as e:
        logger.error(f"Error marking channel read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update read state.")


@router.post("/messages/{message_id}/replies")
async def api_create_thread_reply(message_id: str, payload: ThreadReplyPayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        display_name = resolve_display_name(auth)
        saved_reply = await save_thread_reply(
            parent_message_id=message_id,
            user_name=display_name,
            content=payload.content,
            image_base64=payload.image_base64,
            sender_id=auth.user_id,
        )
        await manager.broadcast(
            json.dumps({"type": "thread_reply_created", "data": saved_reply, "parent_message_id": message_id}),
            saved_reply.get("channel_name", ""),
        )
        return {"status": "success", "reply": saved_reply}
    except Exception as e:
        logger.error(f"Error creating thread reply: {e}")
        raise HTTPException(status_code=500, detail="Failed to create thread reply.")


@router.get("/messages/{message_id}/replies")
async def api_get_thread_replies(message_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        return await get_thread_replies(message_id)
    except Exception as e:
        logger.error(f"Error fetching thread replies: {e}")
        return []

@router.post("/threads/{message_id}/follow")
async def api_toggle_thread_follow(message_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        following = await toggle_thread_follow(message_id, auth.user_id)
        return {"status": "success", "following": following}
    except Exception as e:
        logger.error(f"Error toggling thread follow: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle thread follow.")
