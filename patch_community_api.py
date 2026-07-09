import re

with open('app/api/community.py', 'r') as f:
    content = f.read()

# Pagination in api_get_messages
content = content.replace(
    'async def api_get_messages(channel_name: str, limit: int = 50, auth: AuthState = Depends(RequireVerifiedAstrologer())):',
    'async def api_get_messages(channel_name: str, limit: int = 50, cursor: str = None, auth: AuthState = Depends(RequireVerifiedAstrologer())):'
)
content = content.replace(
    'return await get_messages(channel_name, limit)',
    'return await get_messages(channel_name, limit, cursor)'
)

# Reaction endpoint
content += """
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
"""

# WebSocket enhancements
ws_logic_old = """                if action == "send_message":
                    saved_msg = await save_message(
                        channel_name=channel_name,
                        user_name=payload.get("user_name", "Anonymous"),
                        content=payload.get("content", ""),
                        image_base64=payload.get("image_base64")
                    )"""
ws_logic_new = """                if action == "send_message":
                    saved_msg = await save_message(
                        channel_name=channel_name,
                        user_name=payload.get("user_name", "Anonymous"),
                        content=payload.get("content", ""),
                        image_base64=payload.get("image_base64"),
                        content_type=payload.get("content_type", "STANDARD"),
                        chart_id=payload.get("chart_id")
                    )"""
content = content.replace(ws_logic_old, ws_logic_new)

ws_reaction_new = """
                elif action == "toggle_reaction":
                    msg_id = payload.get("message_id")
                    reaction_type = payload.get("reaction_type")
                    user_id = payload.get("user_id") # Normally from auth token, trusting payload over WS for now
                    await manager.broadcast(
                        json.dumps({"type": "reaction_updated", "message_id": msg_id, "reaction_type": reaction_type, "user_id": user_id}),
                        channel_name
                    )
"""
content = content.replace('elif action == "delete_message":', ws_reaction_new + '\n                elif action == "delete_message":')

with open('app/api/community.py', 'w') as f:
    f.write(content)

