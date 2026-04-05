from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Union


SCHEMA_VERSION = 5

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE,
    parent_id INTEGER REFERENCES modules(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    full_slug TEXT NOT NULL UNIQUE,
    ui_copy_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_modules_parent_id ON modules(parent_id);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    review_flag INTEGER NOT NULL DEFAULT 0,
    question_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    ranking REAL NOT NULL,
    type_config_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_module_id ON questions(module_id);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER REFERENCES modules(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS quiz_session_items (
    session_id INTEGER NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    score_earned REAL,
    score_possible REAL NOT NULL DEFAULT 1,
    PRIMARY KEY (session_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_session_items_session_id ON quiz_session_items(session_id);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Union[str, Path]) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def _existing_table_names(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()
    with connect(db_path) as connection:
        return {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }


def _schema_version(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with connect(db_path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _reset_database_file(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()


def initialize_database(db_path: Union[str, Path]) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if _existing_table_names(path) and _schema_version(path) != SCHEMA_VERSION:
        _reset_database_file(path)

    with connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()


@contextmanager
def get_connection(db_path: Union[str, Path]) -> Iterator[sqlite3.Connection]:
    connection = connect(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
