import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


CURRENT_SCHEMA_VERSION = 8
SCHEMA_VERSION_TABLE = "app_schema_version"
SCHEMA_SQL = Path(__file__).with_name("schema.sql").read_text()


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


def _backfill_question_prompt_keys(connection: DatabaseConnection) -> None:
    from .service.questions import question_prompt_key

    rows = connection.execute(
        """
        SELECT id, question_type, prompt, type_config_json
        FROM questions
        """
    ).fetchall()
    for row in rows:
        type_config = json.loads(row["type_config_json"])
        connection.execute(
            "UPDATE questions SET prompt_key = ? WHERE id = ?",
            (question_prompt_key(row["question_type"], row["prompt"], type_config), row["id"]),
        )


def initialize_database(database_url: str) -> None:
    with connect(database_url) as connection:
        current_version = _schema_version(connection)
        existing_tables = _existing_table_names(connection)

        if existing_tables and current_version == 0:
            raise RuntimeError("Existing PostgreSQL database has no schema version. Refusing to mutate it automatically.")
        if current_version not in {0, 1, 2, 3, 4, 5, 6, 7, CURRENT_SCHEMA_VERSION}:
            raise RuntimeError(f"Unsupported PostgreSQL schema version {current_version}.")

        if current_version == 0:
            connection.executescript(SCHEMA_SQL)
        if current_version == 1:
            connection.execute("ALTER TABLE users DROP COLUMN IF EXISTS disabled_at")
        if current_version in {1, 2, 3, 4}:
            connection.execute("ALTER TABLE modules DROP COLUMN IF EXISTS source_id")
            connection.execute("ALTER TABLE modules DROP COLUMN IF EXISTS title")
            connection.execute("ALTER TABLE modules DROP COLUMN IF EXISTS ui_copy_json")
        if current_version in {1, 2, 3, 4}:
            connection.execute("ALTER TABLE questions DROP COLUMN IF EXISTS source_id")
        if current_version in {1, 2, 3, 4}:
            connection.execute("DROP TABLE IF EXISTS question_import_session_rows")
            connection.execute("DROP TABLE IF EXISTS question_import_sessions")
        if current_version in {1, 2, 3, 4, 5}:
            connection.execute("ALTER TABLE quiz_session_items ADD COLUMN IF NOT EXISTS resolved_prompt TEXT")
            connection.execute(
                "ALTER TABLE quiz_session_items ADD COLUMN IF NOT EXISTS resolved_type_config_json TEXT"
            )
        if current_version in {1, 2, 3, 4, 5, 6}:
            connection.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'")
            connection.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)")
            connection.execute("ALTER TABLE modules DROP CONSTRAINT IF EXISTS modules_full_slug_key")
            connection.execute("ALTER TABLE modules ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL")
            connection.execute("ALTER TABLE modules ADD COLUMN IF NOT EXISTS admin_verified INTEGER NOT NULL DEFAULT 1")
            connection.execute(
                "ALTER TABLE modules ADD COLUMN IF NOT EXISTS moderation_status TEXT NOT NULL DEFAULT 'verified'"
            )
            connection.execute(
                "ALTER TABLE modules ADD COLUMN IF NOT EXISTS admin_review_note TEXT NOT NULL DEFAULT ''"
            )
            connection.execute(
                "ALTER TABLE modules ADD COLUMN IF NOT EXISTS reviewed_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL"
            )
            connection.execute("ALTER TABLE modules ADD COLUMN IF NOT EXISTS reviewed_at TEXT")
            connection.execute(
                "UPDATE modules SET admin_verified = COALESCE(admin_verified, 1), moderation_status = COALESCE(moderation_status, 'verified')"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_modules_parent_id ON modules(parent_id)")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_modules_created_by_status ON modules(created_by_user_id, admin_verified, moderation_status)"
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_verified_full_slug
                ON modules (LOWER(full_slug))
                WHERE admin_verified = 1
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_pending_owner_full_slug
                ON modules (created_by_user_id, LOWER(full_slug))
                WHERE admin_verified = 0
                  AND created_by_user_id IS NOT NULL
                  AND moderation_status = 'pending'
                """
            )
            connection.execute(
                "ALTER TABLE questions ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL"
            )
            connection.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS admin_verified INTEGER NOT NULL DEFAULT 1")
            connection.execute(
                "ALTER TABLE questions ADD COLUMN IF NOT EXISTS moderation_status TEXT NOT NULL DEFAULT 'verified'"
            )
            connection.execute(
                "ALTER TABLE questions ADD COLUMN IF NOT EXISTS admin_review_note TEXT NOT NULL DEFAULT ''"
            )
            connection.execute(
                "ALTER TABLE questions ADD COLUMN IF NOT EXISTS reviewed_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL"
            )
            connection.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS reviewed_at TEXT")
            connection.execute(
                "UPDATE questions SET admin_verified = COALESCE(admin_verified, 1), moderation_status = COALESCE(moderation_status, 'verified')"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_questions_module_id ON questions(module_id)")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_questions_created_by_status ON questions(created_by_user_id, admin_verified, moderation_status)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS question_revision_proposals (
                    id BIGSERIAL PRIMARY KEY,
                    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                    proposer_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    prompt TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    type_config_json TEXT NOT NULL,
                    delete_requested INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    admin_review_note TEXT NOT NULL DEFAULT '',
                    reviewed_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    reviewed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(question_id, proposer_user_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_question_revision_proposals_proposer ON question_revision_proposals(proposer_user_id, status)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_question_revision_proposals_question ON question_revision_proposals(question_id, status)"
            )
        if current_version in {1, 2, 3, 4, 5, 6, 7}:
            connection.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS prompt_key TEXT")
            _backfill_question_prompt_keys(connection)
            connection.execute("ALTER TABLE questions ALTER COLUMN prompt_key SET NOT NULL")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_questions_module_prompt_key ON questions(module_id, prompt_key)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_questions_prompt_key ON questions(prompt_key)")
        if current_version != 0:
            connection.executescript(SCHEMA_SQL)
        _set_schema_version(connection, CURRENT_SCHEMA_VERSION)
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
