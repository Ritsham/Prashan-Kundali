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

async def save_message(channel_name: str, user_name: str, content: str, image_base64: Optional[str] = None) -> Dict[str, Any]:
    msg_id = f"msg_{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    
    data = {
        "id": msg_id,
        "channel_name": channel_name,
        "user_name": user_name,
        "content": content,
        "image_base64": image_base64,
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

async def get_messages(channel_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        if supabase:
            res = supabase.table("community_messages").select("*").eq("channel_name", channel_name).order("created_at", desc=True).limit(limit).execute()
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
