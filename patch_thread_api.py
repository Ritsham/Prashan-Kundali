import re

with open('app/api/community.py', 'r') as f:
    content = f.read()

# Add get_thread_replies API
thread_replies_api = """
from app.storage.community_db import get_thread_replies

@router.get("/messages/{message_id}/replies")
async def api_get_thread_replies(message_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        return await get_thread_replies(message_id)
    except Exception as e:
        logger.error(f"Error fetching thread replies: {e}")
        return []
"""

if "api_get_thread_replies" not in content:
    content = content.replace('@router.post("/threads/{message_id}/follow")', thread_replies_api + '\n@router.post("/threads/{message_id}/follow")')

# Add WebSocket support for send_thread_reply
ws_logic_old = """                elif action == "delete_message":"""
ws_logic_new = """                elif action == "send_thread_reply":
                    from app.storage.community_db import save_thread_reply
                    saved_reply = await save_thread_reply(
                        parent_message_id=payload.get("parent_message_id"),
                        user_name=payload.get("user_name", "Anonymous"),
                        content=payload.get("content", ""),
                    )
                    await manager.broadcast(
                        json.dumps({"type": "new_thread_reply", "reply": saved_reply}),
                        channel_name
                    )
                elif action == "delete_message":"""
if "send_thread_reply" not in content:
    content = content.replace(ws_logic_old, ws_logic_new)

with open('app/api/community.py', 'w') as f:
    f.write(content)
