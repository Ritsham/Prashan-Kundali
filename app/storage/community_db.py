import json
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
import os

from app.storage.database import supabase

async def init_community_db() -> None:
    # Supabase handles schema via SQL migrations
    pass

async def get_channels() -> List[Dict[str, Any]]:
    try:
         if supabase:
             res = supabase.table("community_channels").select("name").order("name").execute()
             return [{"name": row["name"]} for row in res.data]
    except Exception as e:
         print(f"Warning: Supabase get_channels failed: {e}")
    return [{"name": "general"}, {"name": "astrology-tips"}] # fallback channels

async def save_message(channel_name: str, user_name: str, content: str, image_base64: Optional[str] = None, content_type: str = "STANDARD", chart_id: Optional[str] = None) -> Dict[str, Any]:
    msg_id = f"msg_{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    
    data = {
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
    }
    
    try:
        if supabase:
            supabase.table("community_messages").insert(data).execute()
    except Exception as e:
        print(f"Warning: Supabase save_message failed: {e}")
    return data

async def get_messages(channel_name: str, limit: int = 50, cursor: Optional[str] = None) -> List[Dict[str, Any]]:
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

async def delete_message(message_id: str) -> None:
    try:
        if supabase:
            supabase.table("community_messages").update({
                "is_deleted": True,
                "content": "This message was deleted.",
                "image_base64": None
            }).eq("id", message_id).execute()
    except Exception as e:
        print(f"Warning: Supabase delete_message failed: {e}")

async def star_message(message_id: str) -> None:
    try:
        if supabase:
            res = supabase.table("community_messages").select("stars").eq("id", message_id).execute()
            if res.data:
                current_stars = res.data[0]["stars"]
                supabase.table("community_messages").update({
                    "stars": current_stars + 1
                }).eq("id", message_id).execute()
    except Exception as e:
        print(f"Warning: Supabase star_message failed: {e}")

async def save_thread_reply(parent_message_id: str, user_name: str, content: str, image_base64: Optional[str] = None) -> Dict[str, Any]:
    reply_id = f"thrd_{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    
    data = {
        "id": reply_id,
        "parent_message_id": parent_message_id,
        "user_name": user_name,
        "content": content,
        "image_base64": image_base64,
        "is_deleted": False,
        "created_at": created_at
    }
    
    try:
        if supabase:
            supabase.table("community_threads").insert(data).execute()
    except Exception as e:
        print(f"Warning: Supabase save_thread_reply failed: {e}")
    return data

async def get_thread_replies(parent_message_id: str) -> List[Dict[str, Any]]:
    try:
        if supabase:
            res = supabase.table("community_threads").select("*").eq("parent_message_id", parent_message_id).order("created_at").execute()
            return [dict(row) for row in res.data]
    except Exception as e:
        print(f"Warning: Supabase get_thread_replies failed: {e}")
    return []


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
