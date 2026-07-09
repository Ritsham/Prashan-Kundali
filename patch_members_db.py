with open('app/storage/community_db.py', 'r') as f:
    content = f.read()

members_code = """
async def get_community_members(query: str = None) -> List[Dict]:
    try:
        if supabase:
            q = supabase.table("community_profiles").select("user_id, display_name, username, bio, systems_practiced")
            if query:
                q = q.ilike("display_name", f"%{query}%") # Basic search
            res = q.limit(100).execute()
            return [dict(row) for row in res.data]
    except Exception as e:
        print(f"Warning: get_community_members failed: {e}")
    return []

async def get_community_member(user_id: str) -> Optional[Dict]:
    try:
        if supabase:
            res = supabase.table("community_profiles").select("*").eq("user_id", user_id).execute()
            if res.data:
                return dict(res.data[0])
    except Exception as e:
        print(f"Warning: get_community_member failed: {e}")
    return None

async def report_message(message_id: str, reporter_id: str, reason: str) -> bool:
    try:
        if supabase:
            supabase.table("community_reports").insert({
                "message_id": message_id,
                "reporter_id": reporter_id,
                "reason": reason
            }).execute()
            return True
    except Exception as e:
        print(f"Warning: report_message failed: {e}")
    return False
"""

if "get_community_members" not in content:
    content += "\n" + members_code

with open('app/storage/community_db.py', 'w') as f:
    f.write(content)
