from __future__ import annotations

import os


DEFAULT_OPENAI_MODEL = "gpt-5.2"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
DEFAULT_CEREBRAS_MODEL = "llama-3.3-70b"
DEFAULT_MAX_LLM_EVIDENCE_ITEMS = 8
ENV_LOADED = False
ENV_PATH = ".env"


def load_local_env() -> None:
    global ENV_LOADED
    if ENV_LOADED:
        return
    ENV_LOADED = True
    for path in [".env", ".env.local", ".env.example"]:
        if os.path.exists(path):
            load_env_file(path)


def load_env_file(path: str) -> None:
    with open(path, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ and not is_placeholder_secret(key, value):
                os.environ[key] = value


def is_placeholder_secret(key: str, value: str) -> bool:
    if "KEY" not in key and "TOKEN" not in key and "SECRET" not in key:
        return False
    lowered = value.lower()
    return not value or "your-" in lowered or "first-key" in lowered or "second-key" in lowered


def api_keys_for(prefix: str) -> list[str]:
    keys = []
    for name in [f"{prefix}_API_KEYS", f"{prefix}_API_KEY"]:
        keys.extend(split_keys(os.getenv(name, "")))
    index = 1
    while True:
        value = os.getenv(f"{prefix}_API_KEY_{index}", "")
        if not value:
            break
        keys.extend(split_keys(value))
        index += 1
    deduped = []
    for key in keys:
        if key and key not in deduped:
            deduped.append(key)
    return deduped


def split_keys(value: str) -> list[str]:
    normalized = value.replace("\n", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def provider_order() -> list[str]:
    selected = selected_provider()
    configured_fallbacks = [
        item.strip().lower()
        for item in os.getenv("PRASHNA_LLM_FALLBACK_PROVIDERS", "openrouter,cerebras,groq,openai,gemini").split(",")
        if item.strip()
    ]
    ordered = []
    for provider in [selected, *configured_fallbacks]:
        if provider in {"openai", "gemini", "groq", "openrouter", "cerebras"} and provider_has_keys(provider) and provider not in ordered:
            ordered.append(provider)
    if not ordered:
        raise RuntimeError("No LLM provider/key configured. Add .env with PRASHNA_LLM_PROVIDER and matching API keys.")
    return ordered


def selected_provider() -> str:
    configured = os.getenv("PRASHNA_LLM_PROVIDER", "").strip().lower()
    if configured in {"local", "off"}:
        raise RuntimeError("Local/off interpretation mode is disabled. Configure openai, gemini, groq, openrouter, or cerebras.")
    if configured in {"openai", "gemini", "groq", "openrouter", "cerebras"}:
        return configured
    if configured:
        raise RuntimeError("PRASHNA_LLM_PROVIDER must be openai, gemini, groq, openrouter, or cerebras")
    if api_keys_for("OPENROUTER"):
        return "openrouter"
    if api_keys_for("CEREBRAS"):
        return "cerebras"
    if api_keys_for("GROQ"):
        return "groq"
    if api_keys_for("OPENAI"):
        return "openai"
    if api_keys_for("GEMINI") or api_keys_for("GOOGLE"):
        return "gemini"
    raise RuntimeError("No LLM provider/key configured. Add .env with PRASHNA_LLM_PROVIDER and matching API keys.")


def provider_has_keys(provider: str) -> bool:
    if provider == "gemini":
        return bool(api_keys_for("GEMINI") or api_keys_for("GOOGLE"))
    prefixes = {
        "openai": "OPENAI",
        "groq": "GROQ",
        "openrouter": "OPENROUTER",
        "cerebras": "CEREBRAS",
    }
    return bool(api_keys_for(prefixes.get(provider, "")))


def caller_for_provider(provider: str):
    from app.llm_engine.providers import call_openai, call_gemini, call_groq, call_openrouter, call_cerebras
    callers = {
        "openai": call_openai,
        "gemini": call_gemini,
        "groq": call_groq,
        "openrouter": call_openrouter,
        "cerebras": call_cerebras,
    }
    try:
        return callers[provider]
    except KeyError as exc:
        raise RuntimeError("PRASHNA_LLM_PROVIDER must be openai, gemini, groq, openrouter, or cerebras") from exc


def selected_provider_label() -> str:
    configured = os.getenv("PRASHNA_LLM_PROVIDER", "").strip().lower()
    if configured:
        return configured
    if api_keys_for("OPENROUTER"):
        return "openrouter"
    if api_keys_for("CEREBRAS"):
        return "cerebras"
    if api_keys_for("GROQ"):
        return "groq"
    if api_keys_for("OPENAI"):
        return "openai"
    if api_keys_for("GEMINI") or api_keys_for("GOOGLE"):
        return "gemini"
    return "not_configured"


def max_llm_evidence_items() -> int:
    try:
        configured = int(os.getenv("PRASHNA_LLM_MAX_EVIDENCE_ITEMS", str(DEFAULT_MAX_LLM_EVIDENCE_ITEMS)))
    except ValueError:
        configured = DEFAULT_MAX_LLM_EVIDENCE_ITEMS
    return max(4, min(configured, 20))
