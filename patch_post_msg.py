import re

with open('app/api/community.py', 'r') as f:
    content = f.read()

post_api_code = """
from app.storage.community_db import save_message

class SendMessagePayload(BaseModel):
    content: str
    content_type: str = "STANDARD"
    chart_id: str = None
    image_base64: str = None

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
"""

if "api_send_message" not in content:
    content = content.replace('@router.get("/messages/{message_id}/replies")', post_api_code + '\n@router.get("/messages/{message_id}/replies")')

with open('app/api/community.py', 'w') as f:
    f.write(content)
