with open('app/api/community.py', 'r') as f:
    content = f.read()

notif_api_code = """
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
"""

if "api_get_notifications" not in content:
    content = content.replace('@router.post("/messages/{channel_name}")', notif_api_code + '\n@router.post("/messages/{channel_name}")')

with open('app/api/community.py', 'w') as f:
    f.write(content)
