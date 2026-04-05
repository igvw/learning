from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row


SCHEMA_VERSION = 1
SCHEMA_VERSION_TABLE = "app_schema_version"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS modules (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT UNIQUE,
    parent_id BIGINT REFERENCES modules(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    full_slug TEXT NOT NULL UNIQUE,
    instruction TEXT NOT NULL DEFAULT '',
    ui_copy_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_modules_parent_id ON modules(parent_id);

CREATE TABLE IF NOT EXISTS questions (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT UNIQUE,
    module_id BIGINT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    rank INTEGER NOT NULL,
    type_config_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_module_id ON questions(module_id);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    disabled_at TEXT
);

CREATE TABLE IF NOT EXISTS user_review_flags (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    review_flag INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_user_review_flags_review
    ON user_review_flags(user_id, review_flag);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id BIGINT REFERENCES modules(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user_module_created
    ON quiz_sessions(user_id, module_id, created_at);

CREATE TABLE IF NOT EXISTS quiz_session_items (
    session_id BIGINT NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    score_earned REAL,
    score_possible REAL NOT NULL DEFAULT 1,
    submitted_answer_json TEXT,
    PRIMARY KEY (session_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_session_items_session_id
    ON quiz_session_items(session_id);

CREATE INDEX IF NOT EXISTS idx_quiz_session_items_question_id
    ON quiz_session_items(question_id);

CREATE TABLE IF NOT EXISTS question_import_sessions (
    id BIGSERIAL PRIMARY KEY,
    module_id BIGINT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    committed_at TEXT
);

CREATE TABLE IF NOT EXISTS question_import_session_rows (
    session_id BIGINT NOT NULL REFERENCES question_import_sessions(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    csv_line TEXT NOT NULL,
    status TEXT NOT NULL,
    inferred_type TEXT,
    payload_json TEXT,
    issues_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (session_id, row_number)
);

CREATE INDEX IF NOT EXISTS idx_question_import_session_rows_status
    ON question_import_session_rows(session_id, status);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _translate_sql(query: str) -> str:
    translated = re.sub(r"\bIS\s+\?", "IS NOT DISTINCT FROM %s", query)
    return translated.replace("?", "%s")


def _split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    in_double_quote = False
    previous_char = ""

    for char in script:
        if char == "'" and not in_double_quote and previous_char != "\\":
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote and previous_char != "\\":
            in_double_quote = not in_double_quote

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            previous_char = char
            continue

        current.append(char)
        previous_char = char

    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


class DatabaseConnection:
    def __init__(self, raw: psycopg.Connection[Any]) -> None:
        self._raw = raw

    def __enter__(self) -> "DatabaseConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is None:
            self._raw.commit()
        else:
            self._raw.rollback()
        self._raw.close()

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> Any:
        return self._raw.execute(_translate_sql(query), tuple(params))

    def executescript(self, script: str) -> None:
        for statement in _split_sql_statements(script):
            self._raw.execute(statement)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()


def connect(database_url: str) -> DatabaseConnection:
    raw = psycopg.connect(database_url, autocommit=False, row_factory=dict_row)
    return DatabaseConnection(raw)


def execute_insert_returning_id(connection: DatabaseConnection, query: str, params: tuple[Any, ...] | list[Any]) -> int:
    statement = query.rstrip().rstrip(";")
    row = connection.execute(f"{statement} RETURNING id", params).fetchone()
    if row is None:
        raise RuntimeError("Insert did not return an id.")
    return int(row["id"])


def _ensure_schema_version_table(connection: DatabaseConnection) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
            version INTEGER NOT NULL
        )
        """
    )


def _existing_table_names(connection: DatabaseConnection) -> set[str]:
    rows = connection.execute(
        """
        SELECT table_name AS name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name <> ?
        """,
        (SCHEMA_VERSION_TABLE,),
    ).fetchall()
    return {row["name"] for row in rows}


def _schema_version(connection: DatabaseConnection) -> int:
    _ensure_schema_version_table(connection)
    row = connection.execute(f"SELECT version FROM {SCHEMA_VERSION_TABLE} LIMIT 1").fetchone()
    return int(row["version"]) if row is not None else 0


def _set_schema_version(connection: DatabaseConnection, version: int) -> None:
    _ensure_schema_version_table(connection)
    connection.execute(f"DELETE FROM {SCHEMA_VERSION_TABLE}")
    connection.execute(
        f"INSERT INTO {SCHEMA_VERSION_TABLE} (version) VALUES (?)",
        (version,),
    )


def initialize_database(database_url: str) -> None:
    with connect(database_url) as connection:
        current_version = _schema_version(connection)
        existing_tables = _existing_table_names(connection)

        if existing_tables and current_version == 0:
            raise RuntimeError("Existing PostgreSQL database has no schema version. Refusing to mutate it automatically.")
        if current_version not in {0, SCHEMA_VERSION}:
            raise RuntimeError(f"Unsupported PostgreSQL schema version {current_version}.")

        connection.executescript(SCHEMA_SQL)
        _set_schema_version(connection, SCHEMA_VERSION)
        connection.commit()


@contextmanager
def get_connection(database_url: str) -> Iterator[DatabaseConnection]:
    connection = connect(database_url)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
