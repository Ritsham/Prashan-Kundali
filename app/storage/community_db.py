from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone

from app.storage.database import supabase


DEFAULT_CHANNELS: List[Dict[str, Any]] = [
    {"id": "announcements", "name": "announcements", "slug": "announcements", "description": "Admin updates and platform notices.", "category": "Important", "is_read_only": False},
    {"id": "community-guidelines", "name": "community-guidelines", "slug": "community-guidelines", "description": "Shared norms for respectful learning and case privacy.", "category": "Important", "is_read_only": True},
    {"id": "general", "name": "general", "slug": "general", "description": "Daily discussion for verified astrologers.", "category": "General Community", "is_read_only": False},
    {"id": "introductions", "name": "introductions", "slug": "introductions", "description": "Meet practitioners and share your background.", "category": "General Community", "is_read_only": False},
    {"id": "general-discussion", "name": "general-discussion", "slug": "general-discussion", "description": "Open questions, observations, and peer review.", "category": "General Community", "is_read_only": False},
    {"id": "parashar-astrology", "name": "parashar-astrology", "slug": "parashar-astrology", "description": "Classical principles, yogas, dashas, and house judgement.", "category": "Astrology Systems", "is_read_only": False},
    {"id": "kp-astrology", "name": "kp-astrology", "slug": "kp-astrology", "description": "KP significators, ruling planets, and cuspal analysis.", "category": "Astrology Systems", "is_read_only": False},
    {"id": "jaimini-astrology", "name": "jaimini-astrology", "slug": "jaimini-astrology", "description": "Karakas, rashi drishti, padas, and chara dashas.", "category": "Astrology Systems", "is_read_only": False},
    {"id": "nadi-astrology", "name": "nadi-astrology", "slug": "nadi-astrology", "description": "Nadi combinations and research notes.", "category": "Astrology Systems", "is_read_only": False},
    {"id": "tajika-astrology", "name": "tajika-astrology", "slug": "tajika-astrology", "description": "Varshaphal, muntha, saham, and tajika yogas.", "category": "Astrology Systems", "is_read_only": False},
    {"id": "prashna-astrology", "name": "prashna-astrology", "slug": "prashna-astrology", "description": "Question charts, timing, and event judgement.", "category": "Kundali and Prediction", "is_read_only": False},
    {"id": "lagna-kundali", "name": "lagna-kundali", "slug": "lagna-kundali", "description": "Birth chart analysis and rectification support.", "category": "Kundali and Prediction", "is_read_only": False},
    {"id": "chart-discussions", "name": "chart-discussions", "slug": "chart-discussions", "description": "Share charts, compare methods, and discuss outcomes.", "category": "Kundali and Prediction", "is_read_only": False},
    {"id": "marriage-matching", "name": "marriage-matching", "slug": "marriage-matching", "description": "Compatibility, guna milan, and relationship timing.", "category": "Kundali and Prediction", "is_read_only": False},
    {"id": "muhurta", "name": "muhurta", "slug": "muhurta", "description": "Electional astrology and auspicious timings.", "category": "Kundali and Prediction", "is_read_only": False},
    {"id": "case-studies", "name": "case-studies", "slug": "case-studies", "description": "Anonymized cases, peer review, and documented predictions.", "category": "Learning and Research", "is_read_only": False},
    {"id": "techniques-and-learning", "name": "techniques-and-learning", "slug": "techniques-and-learning", "description": "Frameworks, lessons, and guided learning notes.", "category": "Learning and Research", "is_read_only": False},
    {"id": "research-and-books", "name": "research-and-books", "slug": "research-and-books", "description": "Texts, references, translations, and research papers.", "category": "Learning and Research", "is_read_only": False},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _safe_data(result) -> list:
    return list(getattr(result, "data", None) or [])


async def init_community_db() -> None:
    pass


async def get_channels() -> List[Dict[str, Any]]:
    channels = [dict(channel) for channel in DEFAULT_CHANNELS]
    try:
        if supabase:
            res = (
                supabase.table("community_channels")
                .select("*")
                .order("name")
                .execute()
            )
            seen = {channel.get("slug") or channel.get("name") or channel.get("id") for channel in channels}
            for row in _safe_data(res):
                channel = dict(row)
                key = channel.get("slug") or channel.get("name") or channel.get("id")
                if key not in seen:
                    channels.append(channel)
                    seen.add(key)
    except Exception as e:
        print(f"Warning: Supabase get_channels failed: {e}")
    return channels


async def save_message(
    channel_name: str,
    user_name: str,
    content: str,
    image_base64: Optional[str] = None,
    content_type: str = "STANDARD",
    chart_id: Optional[str] = None,
    sender_id: Optional[str] = None,
    reply_to_message_id: Optional[str] = None,
    client_id: Optional[str] = None,
) -> Dict[str, Any]:
    created_at = _now()
    data = {
        "id": _id("msg"),
        "channel_name": channel_name,
        "user_name": user_name,
        "sender_id": sender_id or user_name,
        "client_id": client_id,
        "content": content,
        "image_base64": image_base64,
        "content_type": content_type,
        "chart_id": chart_id,
        "reply_to_message_id": reply_to_message_id,
        "is_deleted": False,
        "stars": 0,
        "is_pinned": False,
        "created_at": created_at,
        "updated_at": created_at,
    }

    if supabase and client_id:
        try:
            existing = supabase.table("community_messages").select("*").eq("client_id", client_id).limit(1).execute()
            if _safe_data(existing):
                return dict(_safe_data(existing)[0])
        except Exception as e:
            print(f"Warning: Supabase message dedupe skipped: {e}")

    try:
        if supabase:
            supabase.table("community_messages").insert(data).execute()
            return data
    except Exception as e:
        print(f"Warning: Supabase save_message full insert failed: {e}")
        legacy_data = {
            "id": data["id"],
            "channel_name": channel_name,
            "user_name": user_name,
            "content": content,
            "image_base64": image_base64,
            "content_type": content_type,
            "chart_id": chart_id,
            "is_deleted": False,
            "stars": 0,
            "created_at": created_at,
        }
        try:
            if supabase:
                supabase.table("community_messages").insert(legacy_data).execute()
                return {**data, **legacy_data}
        except Exception as legacy_error:
            print(f"Warning: Supabase save_message legacy insert failed: {legacy_error}")
            minimal_data = {
                "id": data["id"],
                "channel_name": channel_name,
                "user_name": user_name,
                "content": content,
                "image_base64": image_base64,
                "created_at": created_at,
            }
            try:
                if supabase:
                    supabase.table("community_messages").insert(minimal_data).execute()
                    return {**data, **minimal_data}
            except Exception as minimal_error:
                print(f"Warning: Supabase save_message minimal insert failed: {minimal_error}")
    return data


async def get_messages(channel_name: str, limit: int = 50, cursor: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        if supabase:
            query = supabase.table("community_messages").select("*").eq("channel_name", channel_name)
            if cursor:
                query = query.lt("created_at", cursor)
            if search:
                query = query.ilike("content", f"%{search}%")
            res = query.order("created_at", desc=True).limit(limit).execute()
            messages = [dict(row) for row in _safe_data(res)]
            messages.reverse()
            return messages
    except Exception as e:
        print(f"Warning: Supabase get_messages failed: {e}")
    return []


async def update_message_author_name(user_id: str, display_name: str, aliases: List[str]) -> None:
    if not supabase or not display_name:
        return
    normalized_aliases = [alias for alias in dict.fromkeys([user_id, *aliases]) if alias and alias != display_name]
    try:
        supabase.table("community_messages").update({"user_name": display_name}).eq("sender_id", user_id).execute()
    except Exception as e:
        print(f"Warning: sender_id author update skipped: {e}")
    for alias in normalized_aliases:
        try:
            supabase.table("community_messages").update({"user_name": display_name}).eq("user_name", alias).execute()
        except Exception as e:
            print(f"Warning: user_name author update skipped for {alias}: {e}")


async def update_message(message_id: str, user_id: str, content: str) -> Optional[Dict[str, Any]]:
    try:
        if supabase:
            existing = supabase.table("community_messages").select("*").eq("id", message_id).limit(1).execute()
            rows = _safe_data(existing)
            if not rows:
                return None
            row = rows[0]
            if str(row.get("sender_id") or row.get("user_name")) != str(user_id):
                return None
            updated_at = _now()
            res = (
                supabase.table("community_messages")
                .update({"content": content, "edited_at": updated_at, "updated_at": updated_at})
                .eq("id", message_id)
                .execute()
            )
            return dict(_safe_data(res)[0]) if _safe_data(res) else {**row, "content": content, "edited_at": updated_at, "updated_at": updated_at}
    except Exception as e:
        print(f"Warning: update_message failed: {e}")
    return None


async def delete_message(message_id: str, user_id: Optional[str] = None, moderator: bool = False) -> Optional[Dict[str, Any]]:
    try:
        if supabase:
            existing = supabase.table("community_messages").select("*").eq("id", message_id).limit(1).execute()
            rows = _safe_data(existing)
            if not rows:
                return None
            row = rows[0]
            if not moderator and user_id and str(row.get("sender_id") or row.get("user_name")) != str(user_id):
                return None
            deleted_at = _now()
            content = "This message was removed by a moderator." if moderator else "This message was deleted."
            payload = {"is_deleted": True, "content": content, "image_base64": None, "deleted_at": deleted_at, "updated_at": deleted_at}
            res = supabase.table("community_messages").update(payload).eq("id", message_id).execute()
            return dict(_safe_data(res)[0]) if _safe_data(res) else {**row, **payload}
    except Exception as e:
        print(f"Warning: delete_message failed: {e}")
    return None


async def star_message(message_id: str) -> Optional[Dict[str, Any]]:
    try:
        if supabase:
            res = supabase.table("community_messages").select("stars").eq("id", message_id).limit(1).execute()
            rows = _safe_data(res)
            if rows:
                current_stars = int(rows[0].get("stars") or 0)
                updated = supabase.table("community_messages").update({"stars": current_stars + 1}).eq("id", message_id).execute()
                return dict(_safe_data(updated)[0]) if _safe_data(updated) else {"id": message_id, "stars": current_stars + 1}
    except Exception as e:
        print(f"Warning: Supabase star_message failed: {e}")
    return None


async def save_thread_reply(parent_message_id: str, user_name: str, content: str, image_base64: Optional[str] = None, sender_id: Optional[str] = None) -> Dict[str, Any]:
    created_at = _now()
    channel_name = None
    try:
        if supabase:
            parent = supabase.table("community_messages").select("channel_name").eq("id", parent_message_id).limit(1).execute()
            rows = _safe_data(parent)
            if rows:
                channel_name = rows[0].get("channel_name")
    except Exception as e:
        print(f"Warning: Supabase parent message lookup failed: {e}")
    data = {
        "id": _id("thrd"),
        "parent_message_id": parent_message_id,
        "channel_name": channel_name,
        "user_name": user_name,
        "sender_id": sender_id or user_name,
        "content": content,
        "image_base64": image_base64,
        "is_deleted": False,
        "created_at": created_at,
        "updated_at": created_at,
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
            return [dict(row) for row in _safe_data(res)]
    except Exception as e:
        print(f"Warning: Supabase get_thread_replies failed: {e}")
    return []


async def toggle_reaction(message_id: str, user_id: str, reaction_type: str) -> bool:
    try:
        if supabase:
            res = supabase.table("message_reactions").select("*").eq("message_id", message_id).eq("user_id", user_id).eq("reaction_type", reaction_type).execute()
            if _safe_data(res):
                supabase.table("message_reactions").delete().eq("message_id", message_id).eq("user_id", user_id).eq("reaction_type", reaction_type).execute()
                return False
            supabase.table("message_reactions").insert({
                "id": _id("rxn"),
                "message_id": message_id,
                "user_id": user_id,
                "reaction_type": reaction_type,
            }).execute()
            return True
    except Exception as e:
        print(f"Warning: toggle_reaction failed: {e}")
    return False


async def get_reactions(message_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    if not supabase or not message_ids:
        return {}
    try:
        res = supabase.table("message_reactions").select("message_id,reaction_type,user_id").in_("message_id", message_ids).execute()
        reactions: Dict[str, List[Dict[str, Any]]] = {}
        for row in _safe_data(res):
            reactions.setdefault(row["message_id"], []).append(dict(row))
        return reactions
    except Exception as e:
        print(f"Warning: get_reactions failed: {e}")
    return {}


async def set_saved_message(message_id: str, user_id: str) -> bool:
    try:
        if supabase:
            res = supabase.table("community_saved_messages").select("*").eq("message_id", message_id).eq("user_id", user_id).execute()
            if _safe_data(res):
                supabase.table("community_saved_messages").delete().eq("message_id", message_id).eq("user_id", user_id).execute()
                return False
            supabase.table("community_saved_messages").insert({"message_id": message_id, "user_id": user_id}).execute()
            return True
        # Supabase not configured — respond with success so UI still works locally
        print("Warning: set_saved_message called but supabase is not configured")
        return True
    except Exception as e:
        print(f"Warning: set_saved_message failed: {e}")
        raise  # Re-raise so the API endpoint can return a proper 500


async def get_saved_messages(user_id: str) -> List[Dict[str, Any]]:
    if supabase:
        saved = supabase.table("community_saved_messages").select("message_id").eq("user_id", user_id).execute()
        ids = [row["message_id"] for row in _safe_data(saved)]
        if not ids:
            return []
        res = supabase.table("community_messages").select("*").in_("id", ids).order("created_at", desc=True).execute()
        return [dict(row) for row in _safe_data(res)]
    return []


async def mark_channel_read(channel_name: str, user_id: str, last_read_message_id: Optional[str]) -> bool:
    try:
        if supabase:
            supabase.table("community_read_states").upsert({
                "channel_name": channel_name,
                "user_id": user_id,
                "last_read_message_id": last_read_message_id,
                "last_read_at": _now(),
            }).execute()
            return True
    except Exception as e:
        print(f"Warning: mark_channel_read failed: {e}")
    return False


async def toggle_thread_follow(message_id: str, user_id: str) -> bool:
    try:
        if supabase:
            res = supabase.table("thread_follows").select("*").eq("message_id", message_id).eq("user_id", user_id).execute()
            if _safe_data(res):
                supabase.table("thread_follows").delete().eq("message_id", message_id).eq("user_id", user_id).execute()
                return False
            supabase.table("thread_follows").insert({"message_id": message_id, "user_id": user_id}).execute()
            return True
    except Exception as e:
        print(f"Warning: toggle_thread_follow failed: {e}")
    return False


async def get_community_members(query: str = None) -> List[Dict[str, Any]]:
    try:
        if supabase:
            q = supabase.table("community_profiles").select("user_id, display_name, username, bio, systems_practiced")
            if query:
                q = q.ilike("display_name", f"%{query}%")
            res = q.limit(100).execute()
            return [dict(row) for row in _safe_data(res)]
    except Exception as e:
        print(f"Warning: get_community_members failed: {e}")
    return []


async def get_community_member(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        if supabase:
            res = supabase.table("community_profiles").select("*").eq("user_id", user_id).execute()
            if _safe_data(res):
                return dict(_safe_data(res)[0])
    except Exception as e:
        print(f"Warning: get_community_member failed: {e}")
    return None


async def report_message(message_id: str, reporter_id: str, reason: str) -> bool:
    try:
        if supabase:
            supabase.table("community_reports").insert({"id": _id("rpt"), "message_id": message_id, "reporter_id": reporter_id, "reason": reason}).execute()
            return True
    except Exception as e:
        print(f"Warning: report_message failed: {e}")
    return False


async def get_notifications(user_id: str) -> List[Dict[str, Any]]:
    try:
        if supabase:
            res = supabase.table("community_notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()
            return [dict(row) for row in _safe_data(res)]
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


async def get_community_reports() -> List[Dict[str, Any]]:
    try:
        if supabase:
            res = supabase.table("community_reports").select("*").order("created_at", desc=True).execute()
            return [dict(row) for row in _safe_data(res)]
    except Exception as e:
        print(f"Warning: get_community_reports failed: {e}")
    return []


async def delete_community_message(message_id: str) -> bool:
    return await delete_message(message_id, moderator=True) is not None


async def ban_community_user(user_id: str) -> bool:
    try:
        if supabase:
            supabase.table("community_profiles").delete().eq("user_id", user_id).execute()
            supabase.table("channel_memberships").delete().eq("user_id", user_id).execute()
            return True
    except Exception as e:
        print(f"Warning: ban_community_user failed: {e}")
    return False
