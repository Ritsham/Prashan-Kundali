with open('app/storage/community_db.py', 'r') as f:
    content = f.read()

notif_code = """
async def get_notifications(user_id: str) -> List[Dict]:
    try:
        if supabase:
            res = supabase.table("community_notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()
            return [dict(row) for row in res.data]
    except Exception as e:
        print(f"Warning: get_notifications failed: {e}")
    return []

async def mark_notifications_read(user_id: str) -> bool:
    try:
        if supabase:
            supabase.table("community_notifications").update({"is_read": True}).eq("user_id", user_id).eq("is_read", False).execute()
            return True
    except Exception as e:
        print(f"Warning: mark_notifications_read failed: {e}")
    return False

async def get_community_reports() -> List[Dict]:
    try:
        if supabase:
            res = supabase.table("community_reports").select("*").order("created_at", desc=True).execute()
            return [dict(row) for row in res.data]
    except Exception as e:
        print(f"Warning: get_community_reports failed: {e}")
    return []

async def delete_community_message(message_id: str) -> bool:
    try:
        if supabase:
            supabase.table("community_messages").update({
                "is_deleted": True,
                "content": "This message was removed by a moderator.",
                "image_base64": None
            }).eq("id", message_id).execute()
            return True
    except Exception as e:
        print(f"Warning: delete_community_message failed: {e}")
    return False

async def ban_community_user(user_id: str) -> bool:
    try:
        if supabase:
            # Simplistic ban approach: we could remove them from `astrologer_applications` or delete their profile
            supabase.table("community_profiles").delete().eq("user_id", user_id).execute()
            supabase.table("channel_memberships").delete().eq("user_id", user_id).execute()
            return True
    except Exception as e:
        print(f"Warning: ban_community_user failed: {e}")
    return False
"""

if "get_notifications" not in content:
    content += "\n" + notif_code

with open('app/storage/community_db.py', 'w') as f:
    f.write(content)
