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
    res = supabase.table("community_channels").select("name").order("name").execute()
    return [{"name": row["name"]} for row in res.data]

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
    
    supabase.table("community_messages").insert(data).execute()
    return data

async def get_messages(channel_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    # Supabase select order by desc, limit, then reverse
    res = supabase.table("community_messages").select("*").eq("channel_name", channel_name).order("created_at", desc=True).limit(limit).execute()
    messages = [dict(row) for row in res.data]
    messages.reverse()
    return messages

async def delete_message(message_id: str) -> None:
    supabase.table("community_messages").update({
        "is_deleted": True,
        "content": "This message was deleted.",
        "image_base64": None
    }).eq("id", message_id).execute()

async def star_message(message_id: str) -> None:
    # Note: Supabase doesn't easily support atomic increments via standard update API yet
    # Need to fetch, then increment, or use a Postgres RPC
    res = supabase.table("community_messages").select("stars").eq("id", message_id).execute()
    if res.data:
        current_stars = res.data[0]["stars"]
        supabase.table("community_messages").update({
            "stars": current_stars + 1
        }).eq("id", message_id).execute()

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
    
    supabase.table("community_threads").insert(data).execute()
    return data

async def get_thread_replies(parent_message_id: str) -> List[Dict[str, Any]]:
    res = supabase.table("community_threads").select("*").eq("parent_message_id", parent_message_id).order("created_at").execute()
    return [dict(row) for row in res.data]
