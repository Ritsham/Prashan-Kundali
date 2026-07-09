import re

# Update community_db.py
with open('app/storage/community_db.py', 'r') as f:
    content = f.read()

thread_follow_code = """
async def toggle_thread_follow(message_id: str, user_id: str) -> bool:
    try:
        if supabase:
            res = supabase.table("thread_follows").select("*").eq("message_id", message_id).eq("user_id", user_id).execute()
            if res.data:
                supabase.table("thread_follows").delete().eq("message_id", message_id).eq("user_id", user_id).execute()
                return False
            else:
                supabase.table("thread_follows").insert({
                    "message_id": message_id,
                    "user_id": user_id
                }).execute()
                return True
    except Exception as e:
        print(f"Warning: toggle_thread_follow failed: {e}")
    return False

async def get_thread_followers(message_id: str) -> List[str]:
    try:
        if supabase:
            res = supabase.table("thread_follows").select("user_id").eq("message_id", message_id).execute()
            return [row["user_id"] for row in res.data]
    except Exception as e:
        print(f"Warning: get_thread_followers failed: {e}")
    return []
"""

if "toggle_thread_follow" not in content:
    content += "\n" + thread_follow_code

with open('app/storage/community_db.py', 'w') as f:
    f.write(content)

# Update community.py
with open('app/api/community.py', 'r') as f:
    api_content = f.read()

thread_api_code = """
from app.storage.community_db import toggle_thread_follow

@router.post("/threads/{message_id}/follow")
async def api_toggle_thread_follow(message_id: str, auth: AuthState = Depends(RequireVerifiedAstrologer())):
    try:
        following = await toggle_thread_follow(message_id, auth.user_id)
        return {"status": "success", "following": following}
    except Exception as e:
        logger.error(f"Error toggling thread follow: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle thread follow.")
"""

if "api_toggle_thread_follow" not in api_content:
    api_content += "\n" + thread_api_code

with open('app/api/community.py', 'w') as f:
    f.write(api_content)
