from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union


ROOT_DIR = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT_DIR / "content" / "modules"
DATA_DIR = ROOT_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "learning.sqlite3"
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"
DEV_FRONTEND_ORIGIN = os.environ.get("LEARNING_APP_DEV_ORIGIN", "http://127.0.0.1:5173")


def resolve_db_path(explicit: Optional[Union[str, Path]] = None) -> Path:
    raw_value = explicit or os.environ.get("LEARNING_APP_DB")
    if raw_value:
        return Path(raw_value).expanduser().resolve()
    return DEFAULT_DB_PATH
