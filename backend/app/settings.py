import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT_DIR / "content" / "modules"
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"
DEFAULT_DEV_FRONTEND_ORIGIN = "http://127.0.0.1:5173"
DEFAULT_AUTH_COOKIE_NAME = "learning_app_session"
DEFAULT_POSTGRES_HOST = "127.0.0.1"
DEFAULT_POSTGRES_PORT = "5432"
DEFAULT_AUTH_SESSION_TTL_SECONDS = 60 * 60 * 24 * 30
DEFAULT_DEMO_SESSION_TTL_SECONDS = 60 * 60 * 8
_SETTINGS_ENV_NAMES = (
    "LEARNING_APP_DEV_ORIGIN",
    "LEARNING_APP_ENV",
    "LEARNING_APP_DATABASE_URL",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "LEARNING_APP_CORS_ORIGINS",
    "LEARNING_APP_SEED_ON_BOOT",
    "LEARNING_APP_INSTANCE_KEY",
    "LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE",
    "LEARNING_APP_BOOTSTRAP_ADMIN_DISPLAY_NAME",
    "LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD",
    "LEARNING_APP_AUTH_COOKIE_NAME",
    "LEARNING_APP_AUTH_COOKIE_SECURE",
    "LEARNING_APP_AUTH_SESSION_TTL_SECONDS",
    "LEARNING_APP_DEMO_SESSION_TTL_SECONDS",
)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    learning_app_dev_origin: str | None = None
    learning_app_env: str | None = None
    learning_app_database_url: str | None = None
    postgres_db: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_host: str | None = None
    postgres_port: str | None = None
    learning_app_cors_origins: str | None = None
    learning_app_seed_on_boot: bool = True
    learning_app_instance_key: str | None = None
    learning_app_bootstrap_admin_handle: str | None = None
    learning_app_bootstrap_admin_display_name: str | None = None
    learning_app_bootstrap_admin_password: str | None = None
    learning_app_auth_cookie_name: str | None = None
    learning_app_auth_cookie_secure: bool = False
    learning_app_auth_session_ttl_seconds: int | None = None
    learning_app_demo_session_ttl_seconds: int | None = None

    @field_validator(
        "learning_app_dev_origin",
        "learning_app_env",
        "learning_app_database_url",
        "postgres_db",
        "postgres_user",
        "postgres_password",
        "postgres_host",
        "postgres_port",
        "learning_app_cors_origins",
        "learning_app_instance_key",
        "learning_app_bootstrap_admin_handle",
        "learning_app_bootstrap_admin_display_name",
        "learning_app_bootstrap_admin_password",
        "learning_app_auth_cookie_name",
        mode="before",
    )
    @classmethod
    def strip_optional_strings(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        return cleaned or None


def _settings_cache_key() -> tuple[tuple[str, str | None], ...]:
    return tuple((name, os.environ.get(name)) for name in _SETTINGS_ENV_NAMES)


@lru_cache(maxsize=16)
def _load_settings(_: tuple[tuple[str, str | None], ...]) -> AppSettings:
    return AppSettings()


def _settings() -> AppSettings:
    return _load_settings(_settings_cache_key())


def _build_database_url_from_postgres_env() -> str:
    settings = _settings()
    database_name = settings.postgres_db
    user = settings.postgres_user
    password = settings.postgres_password
    if database_name is None and user is None and password is None:
        raise RuntimeError(
            "Database configuration is missing. Set LEARNING_APP_DATABASE_URL or POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD."
        )

    missing = [
        name
        for name, value in (
            ("POSTGRES_DB", database_name),
            ("POSTGRES_USER", user),
            ("POSTGRES_PASSWORD", password),
        )
        if value is None
    ]
    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            "Database configuration is incomplete. Set LEARNING_APP_DATABASE_URL or all of "
            f"POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD. Missing: {missing_list}."
        )

    host = settings.postgres_host or DEFAULT_POSTGRES_HOST
    port = settings.postgres_port or DEFAULT_POSTGRES_PORT
    return (
        f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{quote(database_name, safe='')}"
    )


def cors_origins() -> list[str]:
    settings = _settings()
    configured = [
        origin.strip()
        for origin in (settings.learning_app_cors_origins or "").split(",")
        if origin.strip()
    ]
    if configured:
        return configured
    if (settings.learning_app_env or "development").lower() == "development":
        return [
            settings.learning_app_dev_origin or DEFAULT_DEV_FRONTEND_ORIGIN,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    return []


def seed_on_boot() -> bool:
    return _settings().learning_app_seed_on_boot


def instance_key() -> str:
    return _settings().learning_app_instance_key or "default"


def resolve_database_url(explicit: str | Path | None = None) -> str:
    if explicit is not None:
        cleaned_explicit = str(explicit).strip()
        if cleaned_explicit:
            return cleaned_explicit

    raw_value = _settings().learning_app_database_url
    if raw_value is not None:
        return raw_value
    return _build_database_url_from_postgres_env()


def bootstrap_admin_credentials() -> tuple[str, str, str] | None:
    settings = _settings()
    handle = settings.learning_app_bootstrap_admin_handle
    display_name = settings.learning_app_bootstrap_admin_display_name
    password = settings.learning_app_bootstrap_admin_password
    if not any((handle, display_name, password)):
        return None
    if not all((handle, display_name, password)):
        return None
    return handle, display_name, password


def auth_cookie_name() -> str:
    return _settings().learning_app_auth_cookie_name or DEFAULT_AUTH_COOKIE_NAME


def auth_cookie_secure() -> bool:
    return _settings().learning_app_auth_cookie_secure


def auth_session_ttl_seconds() -> int:
    value = _settings().learning_app_auth_session_ttl_seconds
    return max(value or DEFAULT_AUTH_SESSION_TTL_SECONDS, 60)


def demo_session_ttl_seconds() -> int:
    value = _settings().learning_app_demo_session_ttl_seconds
    return max(value or DEFAULT_DEMO_SESSION_TTL_SECONDS, 60)
