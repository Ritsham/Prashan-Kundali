with open('app/api/community.py', 'r') as f:
    content = f.read()

members_api_code = """
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
"""

if "api_get_members" not in content:
    content = content.replace('@router.post("/messages/{channel_name}")', members_api_code + '\n@router.post("/messages/{channel_name}")')

with open('app/api/community.py', 'w') as f:
    f.write(content)
