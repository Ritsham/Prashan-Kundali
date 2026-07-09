from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from typing import Dict, List, Optional
import json
import logging
import os
from supabase import create_client, ClientOptions

from app.storage.community_db import (
    get_channels,
    save_message,
    get_messages,
    delete_message,
    star_message,
    save_thread_reply,
    get_thread_replies,
)
from app.dependencies import AuthState, RequireVerifiedAstrologer, get_current_user
from app.storage.community_access_db import has_active_community_membership

router = APIRouter(prefix="/community", tags=["community"])

logger = logging.getLogger(__name__)


def websocket_has_verified_access(token: str) -> bool:
    if not token:
        return False
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
        client = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_ANON_KEY", ""), options=options)
        user_res = client.auth.get_user(token)
        if not user_res or not user_res.user:
            return False
        membership = has_active_community_membership(client, user_res.user.id)
        if membership is not None:
            return membership
        profile_res = client.table("users").select("role, verification_status, community_access").eq("id", user_res.user.id).execute()
        if not profile_res.data:
            return False
        profile = profile_res.data[0]
        
        is_verified_astrologer = (
            profile.get("role") == "astrologer"
            and profile.get("verification_status") == "verified"
        )
        has_community_access = profile.get("community_access") is True
        
        return is_verified_astrologer or has_community_access
    except Exception as exc:
        logger.error("Community websocket auth failed: %s", exc)
        return False

class ConnectionManager:
    def __init__(self):
        # Maps channel names to a list of active websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_name: str):
        await websocket.accept()
        if channel_name not in self.active_connections:
            self.active_connections[channel_name] = []
        self.active_connections[channel_name].append(websocket)

    def disconnect(self, websocket: WebSocket, channel_name: str):
        if channel_name in self.active_connections:
            self.active_connections[channel_name].remove(websocket)

    async def broadcast(self, message: str, channel_name: str):
        if channel_name in self.active_connections:
            for connection in self.active_connections[channel_name]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending message to websocket: {e}")


manager = ConnectionManager()


@router.get("/channels")
async def api_get_channels(auth: AuthState = Depends(RequireVerifiedAstrologer())):
    return await get_channels()


@router.get("/messages/{channel_name}")
async def api_get_messages(channel_name: str, limit: int = 50, cursor: str = None, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    return await get_messages(channel_name, limit, cursor)


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
    if not websocket_has_verified_access(token):
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, channel_name)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action")
                
                if action == "send_message":
                    saved_msg = await save_message(
                        channel_name=channel_name,
                        user_name=payload.get("user_name", "Anonymous"),
                        content=payload.get("content", ""),
                        image_base64=payload.get("image_base64"),
                        content_type=payload.get("content_type", "STANDARD"),
                        chart_id=payload.get("chart_id")
                    )
                    await manager.broadcast(
                        json.dumps({"type": "new_message", "data": saved_msg}), 
                        channel_name
                    )
                
                
                elif action == "toggle_reaction":
                    msg_id = payload.get("message_id")
                    reaction_type = payload.get("reaction_type")
                    user_id = payload.get("user_id") # Normally from auth token, trusting payload over WS for now
                    await manager.broadcast(
                        json.dumps({"type": "reaction_updated", "message_id": msg_id, "reaction_type": reaction_type, "user_id": user_id}),
                        channel_name
                    )

                elif action == "delete_message":
                    msg_id = payload.get("message_id")
                    await delete_message(msg_id)
                    await manager.broadcast(
                        json.dumps({"type": "message_deleted", "message_id": msg_id}),
                        channel_name
                    )
                    
                elif action == "star_message":
                    msg_id = payload.get("message_id")
                    await star_message(msg_id)
                    await manager.broadcast(
                        json.dumps({"type": "message_starred", "message_id": msg_id}),
                        channel_name
                    )
                    
                elif action == "send_thread_reply":
                    saved_reply = await save_thread_reply(
                        parent_message_id=payload.get("parent_message_id"),
                        user_name=payload.get("user_name", "Anonymous"),
                        content=payload.get("content", ""),
                        image_base64=payload.get("image_base64")
                    )
                    await manager.broadcast(
                        json.dumps({"type": "new_thread_reply", "data": saved_reply}),
                        channel_name
                    )
            except json.JSONDecodeError:
                logger.error("Received non-JSON message over websocket")
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_name)

from app.dependencies import RequireRole

@router.get("/admin/applications")
async def admin_list_applications(auth: AuthState = Depends(RequireRole("admin"))):
    try:
        app_res = auth.client.table("community_applications").select("*").order("created_at", desc=True).execute()
        apps = app_res.data
        
        sys_res = auth.client.table("community_application_systems").select("*").execute()
        proof_res = auth.client.table("community_application_proofs").select("application_id").execute()
        
        systems_by_app = {}
        for s in sys_res.data:
            sys_name = s["system_name"]
            app_id = s["application_id"]
            if app_id not in systems_by_app:
                systems_by_app[app_id] = []
            systems_by_app[app_id].append(sys_name)
            
        proof_counts = {}
        for p in proof_res.data:
            app_id = p["application_id"]
            proof_counts[app_id] = proof_counts.get(app_id, 0) + 1
            
        for app in apps:
            app["systems"] = systems_by_app.get(app["id"], [])
            app["proofs_count"] = proof_counts.get(app["id"], 0)
            
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
        
        # Log the review
        auth.client.table("community_application_reviews").insert({
            "application_id": app_id,
            "admin_id": auth.user_id,
            "previous_status": current_status,
            "new_status": payload.status,
            "admin_notes": payload.message
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
        raise HTTPException(status_code=500, detail="Failed to update application status.")

@router.get("/profile")
async def api_get_profile(auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        res = auth.client.table("community_profiles").select("*").eq("user_id", auth.user_id).execute()
        if not res.data:
            return None
        return res.data[0]
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return None

class ProfilePayload(BaseModel):
    username: str
    display_name: str
    bio: str
    state: str
    country: str
    experience_years: str
    specializations: List[str]
    languages: List[str]
    systems_practiced: List[str]

@router.post("/profile")
async def api_upsert_profile(payload: ProfilePayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        data = payload.model_dump()
        data["user_id"] = auth.user_id
        data["updated_at"] = "now()"
        auth.client.table("community_profiles").upsert(data).execute()
        return {"status": "success", "profile": data}
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
    chart_id: str = None
    image_base64: str = None


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

@router.post("/messages/{channel_name}")
async def api_send_message(channel_name: str, payload: SendMessagePayload, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        saved_msg = await save_message(
            channel_name=channel_name,
            user_name=auth.user_id, # Can map to display name later
            content=payload.content,
            image_base64=payload.image_base64,
            content_type=payload.content_type,
            chart_id=payload.chart_id
        )
        
        # Broadcast the new message via WS
        await manager.broadcast(
            json.dumps({"type": "new_message", "message": saved_msg}),
            channel_name
        )
        
        return {"status": "success", "message": saved_msg}
    except Exception as e:
        logger.error(f"Error sending message via POST: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message.")

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
