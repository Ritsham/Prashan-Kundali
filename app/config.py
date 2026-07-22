from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Iterable
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


LOCAL_CORS_ORIGINS = (
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8088",
    "http://localhost:8088",
)

LOCALHOST_NAMES = {"localhost", "127.0.0.1", "0.0.0.0"}
PRODUCTION_ENVS = {"prod", "production"}
NON_PRODUCTION_ENVS = {"development", "dev", "local", "test", "testing", "staging", "stage"}


class SettingsError(RuntimeError):
    pass


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool_env(name: str, default: bool = False) -> bool:
    value = _env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _split_csv(value: str) -> list[str]:
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


def _redact(name: str, value: str) -> str:
    if not value:
        return ""
    if any(marker in name.upper() for marker in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
        return f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
    return value


def is_placeholder_value(name: str, value: str) -> bool:
    if not value:
        return True
    lowered = value.lower()
    placeholder_markers = (
        "your-",
        "example",
        "placeholder",
        "replace-me",
        "changeme",
        "first-key",
        "second-key",
        "sk-proj-your",
        "gsk-your",
        "csk-your",
        "AIza-your".lower(),
    )
    return any(marker in lowered for marker in placeholder_markers)


def _is_url(value: str, *, schemes: Iterable[str]) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in schemes and bool(parsed.netloc)


def _url_host(value: str) -> str:
    return (urlparse(value).hostname or "").lower()


def _public_origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _first_configured_provider_key(prefixes: Iterable[str]) -> bool:
    for prefix in prefixes:
        names = [f"{prefix}_API_KEY", f"{prefix}_API_KEYS"]
        index = 1
        while True:
            indexed = f"{prefix}_API_KEY_{index}"
            if not os.getenv(indexed):
                break
            names.append(indexed)
            index += 1
        for name in names:
            for value in _split_csv(os.getenv(name, "")):
                if value and not is_placeholder_value(name, value):
                    return True
    return False


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    cors_origins: tuple[str, ...]
    redis_url: str
    astrology_engine_url: str
    llm_engine_url: str
    allow_mock_admin_token: bool
    enable_legacy_unauthenticated_ws: bool
    require_verified_payment: bool
    public_site_url: str
    enable_razorpay: bool
    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str
    consultation_price_inr: str
    require_llm_in_production: bool

    @property
    def is_production(self) -> bool:
        return self.app_env in PRODUCTION_ENVS

    @property
    def is_staging(self) -> bool:
        return self.app_env in {"staging", "stage"}

    @property
    def frontend_public_config(self) -> dict[str, str]:
        return {
            "supabaseUrl": self.supabase_url,
            "supabaseAnonKey": self.supabase_anon_key,
        }

    def validate_startup(self) -> None:
        errors: list[str] = []

        if self.app_env not in PRODUCTION_ENVS | NON_PRODUCTION_ENVS:
            errors.append("APP_ENV must be one of development, staging, or production.")

        if self.supabase_url and not _is_url(self.supabase_url, schemes={"https"}):
            errors.append("SUPABASE_URL must be a valid https:// Supabase project URL.")
        if self.supabase_anon_key and is_placeholder_value("SUPABASE_ANON_KEY", self.supabase_anon_key):
            errors.append("SUPABASE_ANON_KEY cannot be a placeholder value.")

        if self.is_production:
            if not self.supabase_url:
                errors.append("SUPABASE_URL is required in production.")
            if is_placeholder_value("SUPABASE_ANON_KEY", self.supabase_anon_key):
                errors.append("SUPABASE_ANON_KEY is required in production.")
            if not _is_url(self.public_site_url, schemes={"https"}):
                errors.append("PUBLIC_SITE_URL must be a valid https URL in production.")
            if _url_host(self.public_site_url) in LOCALHOST_NAMES:
                errors.append("PUBLIC_SITE_URL cannot be localhost in production.")
            if is_placeholder_value("SUPABASE_SERVICE_ROLE_KEY", self.supabase_service_role_key):
                errors.append("SUPABASE_SERVICE_ROLE_KEY is required in production for server-side admin flows.")
            if not self.cors_origins:
                errors.append("CORS_ORIGINS must include the deployed frontend origin in production.")
            if "*" in self.cors_origins:
                errors.append("CORS_ORIGINS cannot contain * in production.")
            for origin in self.cors_origins:
                if not _is_url(origin, schemes={"https"}):
                    errors.append(f"CORS origin must be https in production: {origin}")
                if _url_host(origin) in LOCALHOST_NAMES:
                    errors.append(f"CORS origin cannot be localhost in production: {origin}")
            for name, value in (
                ("REDIS_URL", self.redis_url),
                ("ASTROLOGY_ENGINE_URL", self.astrology_engine_url),
                ("LLM_ENGINE_URL", self.llm_engine_url),
            ):
                if not _is_url(value, schemes={"http", "https", "redis", "rediss"}):
                    errors.append(f"{name} must be a valid URL.")
                if _url_host(value) in LOCALHOST_NAMES:
                    errors.append(f"{name} cannot point at localhost in production.")
            if self.allow_mock_admin_token:
                errors.append("ALLOW_MOCK_ADMIN_TOKEN cannot be enabled in production.")
            if self.enable_legacy_unauthenticated_ws:
                errors.append("ENABLE_LEGACY_UNAUTHENTICATED_WS cannot be enabled in production.")
            if self.require_llm_in_production and not _first_configured_provider_key(("OPENAI", "GEMINI", "GOOGLE", "GROQ", "OPENROUTER", "CEREBRAS")):
                errors.append("At least one production LLM API key is required.")

        if self.enable_razorpay or self.require_verified_payment:
            if is_placeholder_value("RAZORPAY_KEY_ID", self.razorpay_key_id):
                errors.append("RAZORPAY_KEY_ID is required when Razorpay/payments are enabled.")
            if is_placeholder_value("RAZORPAY_KEY_SECRET", self.razorpay_key_secret):
                errors.append("RAZORPAY_KEY_SECRET is required when Razorpay/payments are enabled.")
            if self.is_production and is_placeholder_value("RAZORPAY_WEBHOOK_SECRET", self.razorpay_webhook_secret):
                errors.append("RAZORPAY_WEBHOOK_SECRET is required in production when Razorpay/payments are enabled.")
            try:
                price = Decimal(str(self.consultation_price_inr))
                if price <= 0 or price > Decimal("100000") or abs(price.as_tuple().exponent) > 2:
                    errors.append("CONSULTATION_PRICE_INR must be a positive amount up to 100000 with at most two decimals.")
            except (InvalidOperation, TypeError):
                errors.append("CONSULTATION_PRICE_INR must be a valid decimal amount.")

        if errors:
            raise SettingsError("Invalid environment configuration:\n- " + "\n- ".join(errors))

    def safe_summary(self) -> dict[str, object]:
        return {
            "app_env": self.app_env,
            "supabase_url": self.supabase_url,
            "cors_origins": list(self.cors_origins),
            "redis_url": self.redis_url,
            "astrology_engine_url": self.astrology_engine_url,
            "llm_engine_url": self.llm_engine_url,
            "allow_mock_admin_token": self.allow_mock_admin_token,
            "enable_legacy_unauthenticated_ws": self.enable_legacy_unauthenticated_ws,
            "require_verified_payment": self.require_verified_payment,
            "public_site_url": self.public_site_url,
            "enable_razorpay": self.enable_razorpay,
            "razorpay_key_id": _redact("RAZORPAY_KEY_ID", self.razorpay_key_id),
        }


def _build_settings() -> Settings:
    raw_env = (_env("APP_ENV") or _env("ENVIRONMENT") or "development").lower()
    app_env = "production" if raw_env == "prod" else "staging" if raw_env == "stage" else raw_env
    public_site_url = _env("PUBLIC_SITE_URL", "http://localhost:5173").rstrip("/")
    cors_value = _env("CORS_ORIGINS") or _env("ADMIN_CORS_ORIGINS")
    if cors_value:
        cors_origins = tuple(_split_csv(cors_value))
    elif app_env in PRODUCTION_ENVS and _is_url(public_site_url, schemes={"https"}):
        cors_origins = (public_site_url,)
    else:
        cors_origins = LOCAL_CORS_ORIGINS

    return Settings(
        app_env=app_env,
        log_level=(_env("LOG_LEVEL", "INFO") or "INFO").upper(),
        supabase_url=_env("SUPABASE_URL").rstrip("/"),
        supabase_anon_key=_env("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_env("SUPABASE_SERVICE_ROLE_KEY"),
        cors_origins=tuple(_public_origin(origin) for origin in cors_origins),
        redis_url=_env("REDIS_URL", "redis://localhost:6379/0"),
        astrology_engine_url=_env("ASTROLOGY_ENGINE_URL", "http://localhost:8001").rstrip("/"),
        llm_engine_url=_env("LLM_ENGINE_URL", "http://localhost:8002").rstrip("/"),
        allow_mock_admin_token=_bool_env("ALLOW_MOCK_ADMIN_TOKEN"),
        enable_legacy_unauthenticated_ws=_bool_env("ENABLE_LEGACY_UNAUTHENTICATED_WS"),
        require_verified_payment=_bool_env("REQUIRE_VERIFIED_PAYMENT"),
        public_site_url=public_site_url,
        enable_razorpay=_bool_env("ENABLE_RAZORPAY"),
        razorpay_key_id=_env("RAZORPAY_KEY_ID"),
        razorpay_key_secret=_env("RAZORPAY_KEY_SECRET"),
        razorpay_webhook_secret=_env("RAZORPAY_WEBHOOK_SECRET"),
        consultation_price_inr=_env("CONSULTATION_PRICE_INR", "199.00"),
        require_llm_in_production=_bool_env("REQUIRE_LLM_IN_PRODUCTION", True),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return _build_settings()


def get_supabase_url() -> str:
    return get_settings().supabase_url


def validate_startup_settings() -> Settings:
    settings = get_settings()
    settings.validate_startup()
    return settings
