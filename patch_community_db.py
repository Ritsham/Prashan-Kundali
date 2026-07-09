import re

with open('app/storage/community_db.py', 'r') as f:
    content = f.read()

# Update get_messages to support cursor
content = re.sub(
    r'async def get_messages\(channel_name: str, limit: int = 50\) -> List\[Dict\[str, Any\]\]:',
    'async def get_messages(channel_name: str, limit: int = 50, cursor: Optional[str] = None) -> List[Dict[str, Any]]:',
    content
)

new_get_messages = """
    try:
        if supabase:
            query = supabase.table("community_messages").select("*").eq("channel_name", channel_name)
            if cursor:
                query = query.lt("created_at", cursor)
            res = query.order("created_at", desc=True).limit(limit).execute()
            messages = [dict(row) for row in res.data]
            messages.reverse()
            return messages
    except Exception as e:
        print(f"Warning: Supabase get_messages failed: {e}")
    return []
"""
content = re.sub(r'    try:\s+if supabase:.*?return \[\]', new_get_messages, content, flags=re.DOTALL)

# Update save_message to support content_type
content = re.sub(
    r'async def save_message\(channel_name: str, user_name: str, content: str, image_base64: Optional\[str\] = None\) -> Dict\[str, Any\]:',
    'async def save_message(channel_name: str, user_name: str, content: str, image_base64: Optional[str] = None, content_type: str = "STANDARD", chart_id: Optional[str] = None) -> Dict[str, Any]:',
    content
)

save_message_data_old = """    data = {
        "id": msg_id,
        "channel_name": channel_name,
        "user_name": user_name,
        "content": content,
        "image_base64": image_base64,
        "is_deleted": False,
        "stars": 0,
        "created_at": created_at
    }"""
save_message_data_new = """    data = {
        "id": msg_id,
        "channel_name": channel_name,
        "user_name": user_name,
        "content": content,
        "image_base64": image_base64,
        "content_type": content_type,
        "chart_id": chart_id,
        "is_deleted": False,
        "stars": 0,
        "created_at": created_at
    }"""
content = content.replace(save_message_data_old, save_message_data_new)

# Append reaction support
content += """
async def toggle_reaction(message_id: str, user_id: str, reaction_type: str) -> bool:
    try:
        if supabase:
            # Check if reaction exists
            res = supabase.table("message_reactions").select("*").eq("message_id", message_id).eq("user_id", user_id).eq("reaction_type", reaction_type).execute()
            if res.data:
                supabase.table("message_reactions").delete().eq("message_id", message_id).eq("user_id", user_id).eq("reaction_type", reaction_type).execute()
                return False # removed
            else:
                supabase.table("message_reactions").insert({
                    "message_id": message_id,
                    "user_id": user_id,
                    "reaction_type": reaction_type
                }).execute()
                return True # added
    except Exception as e:
        print(f"Warning: toggle_reaction failed: {e}")
    return False

async def get_reactions(message_ids: List[str]) -> Dict[str, List[Dict]]:
    if not supabase or not message_ids:
        return {}
    try:
        res = supabase.table("message_reactions").select("message_id, reaction_type, user_id").in_("message_id", message_ids).execute()
        reactions = {}
        for row in res.data:
            m_id = row["message_id"]
            if m_id not in reactions:
                reactions[m_id] = []
            reactions[m_id].append(row)
        return reactions
    except Exception as e:
        print(f"Warning: get_reactions failed: {e}")
    return {}
"""

with open('app/storage/community_db.py', 'w') as f:
    f.write(content)

