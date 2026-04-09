from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union


ROOT_DIR = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT_DIR / "content" / "modules"
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"
DEV_FRONTEND_ORIGIN = os.environ.get("LEARNING_APP_DEV_ORIGIN", "http://127.0.0.1:5173")
DEFAULT_DATABASE_URL = os.environ.get(
    "LEARNING_APP_DATABASE_URL",
    "postgresql://learning:learning@127.0.0.1:5432/learning",
)


def env_flag(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def cors_origins() -> list[str]:
    raw_value = os.environ.get("LEARNING_APP_CORS_ORIGINS", "")
    configured = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    if configured:
        return configured
    if os.environ.get("LEARNING_APP_ENV", "development").lower() == "development":
        return [DEV_FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"]
    return []


def seed_on_boot() -> bool:
    return env_flag("LEARNING_APP_SEED_ON_BOOT", True)


def instance_key() -> str:
    raw_value = os.environ.get("LEARNING_APP_INSTANCE_KEY", "default").strip()
    return raw_value or "default"


def resolve_database_url(explicit: Optional[Union[str, Path]] = None) -> str:
    raw_value = explicit or os.environ.get("LEARNING_APP_DATABASE_URL")
    if raw_value is None:
        return DEFAULT_DATABASE_URL
    return str(raw_value)
