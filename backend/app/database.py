import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


CURRENT_SCHEMA_VERSION = 6
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


def initialize_database(database_url: str) -> None:
    with connect(database_url) as connection:
        current_version = _schema_version(connection)
        existing_tables = _existing_table_names(connection)

        if existing_tables and current_version == 0:
            raise RuntimeError("Existing PostgreSQL database has no schema version. Refusing to mutate it automatically.")
        if current_version not in {0, 1, 2, 3, 4, 5, CURRENT_SCHEMA_VERSION}:
            raise RuntimeError(f"Unsupported PostgreSQL schema version {current_version}.")

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
