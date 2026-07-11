import os


LEGACY_SUPABASE_URLS = {
    "https://kumkuqiqngilkrbfvouy.supabase.co",
}

CURRENT_SUPABASE_URL = "https://kxsucyoqaihtrnspjuas.supabase.co"


def get_supabase_url() -> str:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if url in LEGACY_SUPABASE_URLS:
        return CURRENT_SUPABASE_URL
    return url
