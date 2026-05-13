import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


CURRENT_SCHEMA_VERSION = 12
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


def _table_columns(connection: DatabaseConnection, table_name: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = ?
        """,
        (table_name,),
    ).fetchall()
    return {row["column_name"] for row in rows}


def _constraint_exists(connection: DatabaseConnection, table_name: str, constraint_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = ?
          AND constraint_name = ?
        """,
        (table_name, constraint_name),
    ).fetchone()
    return row is not None


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


def _ensure_question_version_columns(connection: DatabaseConnection) -> None:
    connection.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS enabled INTEGER NOT NULL DEFAULT 1")
    connection.execute(
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS replaced_by_question_id BIGINT REFERENCES questions(id) ON DELETE SET NULL"
    )
    connection.execute(
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS progress_from_question_id BIGINT REFERENCES questions(id) ON DELETE SET NULL"
    )
    connection.execute("UPDATE questions SET enabled = COALESCE(enabled, 1)")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_questions_enabled_module ON questions(module_id, enabled, moderation_status)"
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_questions_replaced_by ON questions(replaced_by_question_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_questions_progress_from ON questions(progress_from_question_id)")


def _create_question_bundles_table(connection: DatabaseConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS question_bundles (
            id BIGSERIAL PRIMARY KEY,
            question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            variant_index INTEGER NOT NULL,
            prompt_values_json TEXT NOT NULL,
            accepted_answers_json TEXT NOT NULL,
            UNIQUE(question_id, variant_index),
            UNIQUE(id, question_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_question_bundles_question_id
        ON question_bundles(question_id, variant_index)
        """
    )


def _create_question_bundle_summaries_view(connection: DatabaseConnection) -> None:
    connection.execute(
        """
        CREATE OR REPLACE VIEW question_bundle_summaries AS
        SELECT
            question_id,
            json_agg(
                json_build_object(
                    'prompt_values', prompt_values_json::json,
                    'accepted_answers', accepted_answers_json::json
                )
                ORDER BY variant_index ASC
            )::text AS variants_json
        FROM question_bundles
        GROUP BY question_id
        """
    )


def _normalize_legacy_bundle_variant(variant: Any) -> dict[str, list[str]]:
    if not isinstance(variant, dict):
        return {"prompt_values": [], "accepted_answers": []}
    prompt_values = variant.get("prompt_values", [])
    accepted_answers = variant.get("accepted_answers", [])
    if not isinstance(prompt_values, list):
        prompt_values = []
    if not isinstance(accepted_answers, list):
        accepted_answers = []
    return {
        "prompt_values": [str(value) for value in prompt_values],
        "accepted_answers": [str(value) for value in accepted_answers],
    }


def _migrate_question_bundles_to_rows(connection: DatabaseConnection) -> None:
    existing_tables = _existing_table_names(connection)
    if "question_bundles" not in existing_tables:
        _create_question_bundles_table(connection)
        _create_question_bundle_summaries_view(connection)
        return

    columns = _table_columns(connection, "question_bundles")
    if "variants_json" not in columns:
        _create_question_bundles_table(connection)
        _create_question_bundle_summaries_view(connection)
        return

    connection.execute("DROP VIEW IF EXISTS question_bundle_summaries")
    connection.execute("DROP TABLE IF EXISTS question_bundles_legacy_v10")
    connection.execute("ALTER TABLE question_bundles RENAME TO question_bundles_legacy_v10")
    _create_question_bundles_table(connection)

    rows = connection.execute(
        """
        SELECT question_id, variants_json
        FROM question_bundles_legacy_v10
        ORDER BY question_id ASC
        """
    ).fetchall()
    for row in rows:
        variants = json.loads(row["variants_json"])
        if not isinstance(variants, list):
            variants = []
        for index, variant in enumerate(variants):
            normalized = _normalize_legacy_bundle_variant(variant)
            connection.execute(
                """
                INSERT INTO question_bundles (
                    question_id,
                    variant_index,
                    prompt_values_json,
                    accepted_answers_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    row["question_id"],
                    index,
                    json.dumps(normalized["prompt_values"], separators=(",", ":"), sort_keys=True),
                    json.dumps(normalized["accepted_answers"], separators=(",", ":"), sort_keys=True),
                ),
            )
    connection.execute("DROP TABLE question_bundles_legacy_v10")
    _create_question_bundle_summaries_view(connection)


def _create_attempts_table(connection: DatabaseConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
            module_id BIGINT REFERENCES modules(id) ON DELETE SET NULL,
            bundle_variant_id BIGINT,
            score_earned REAL NOT NULL,
            score_possible REAL NOT NULL DEFAULT 1,
            submitted_answer_json TEXT,
            answered_at TEXT NOT NULL,
            UNIQUE(session_id, question_id),
            CONSTRAINT fk_attempts_bundle_variant_question
                FOREIGN KEY (bundle_variant_id, question_id)
                REFERENCES question_bundles(id, question_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attempts_user_question_answered
        ON attempts(user_id, question_id, answered_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attempts_user_session
        ON attempts(user_id, session_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attempts_question_id
        ON attempts(question_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attempts_bundle_variant_id
        ON attempts(bundle_variant_id)
        """
    )


def _render_bundle_variant_prompt(prompt: str, prompt_values: list[str]) -> str:
    segments = prompt.split("{}")
    if len(segments) - 1 != len(prompt_values):
        return ""
    prompt_parts: list[str] = []
    for index, segment in enumerate(segments[:-1]):
        prompt_parts.append(segment)
        prompt_parts.append(prompt_values[index])
    prompt_parts.append(segments[-1].rsplit("[]", 1)[0])
    return "".join(prompt_parts).strip()


def _bundle_variant_id_for_resolved(
    connection: DatabaseConnection,
    *,
    question_id: int,
    resolved_prompt: str | None,
    resolved_type_config_json: str | None,
) -> int | None:
    if not resolved_prompt and not resolved_type_config_json:
        return None
    question = connection.execute(
        """
        SELECT question_type, prompt
        FROM questions
        WHERE id = ?
        """,
        (question_id,),
    ).fetchone()
    if question is None or question["question_type"] != "bundle":
        return None

    expected_answers: list[str] | None = None
    if resolved_type_config_json:
        try:
            type_config = json.loads(resolved_type_config_json)
        except json.JSONDecodeError:
            type_config = {}
        accepted_answers = type_config.get("accepted_answers", [])
        if isinstance(accepted_answers, list) and accepted_answers and isinstance(accepted_answers[0], list):
            expected_answers = [str(value) for value in accepted_answers[0]]

    rows = connection.execute(
        """
        SELECT id, prompt_values_json, accepted_answers_json
        FROM question_bundles
        WHERE question_id = ?
        ORDER BY variant_index ASC
        """,
        (question_id,),
    ).fetchall()
    for row in rows:
        prompt_values = [str(value) for value in json.loads(row["prompt_values_json"])]
        accepted_answers = [str(value) for value in json.loads(row["accepted_answers_json"])]
        if resolved_prompt and _render_bundle_variant_prompt(question["prompt"], prompt_values) != resolved_prompt:
            continue
        if expected_answers is not None and accepted_answers != expected_answers:
            continue
        return int(row["id"])
    return None


def _backfill_attempts_from_quiz_items(connection: DatabaseConnection) -> None:
    rows = connection.execute(
        """
        SELECT
            qs.id AS session_id,
            qs.user_id,
            qsi.question_id,
            qsi.bundle_variant_id,
            q.module_id,
            qsi.score_earned,
            COALESCE(NULLIF(qsi.score_possible, 0), 1) AS score_possible,
            qsi.resolved_prompt,
            qsi.resolved_type_config_json,
            qsi.submitted_answer_json,
            COALESCE(qs.completed_at, qs.created_at) AS answered_at
        FROM quiz_session_items AS qsi
        JOIN quiz_sessions AS qs ON qs.id = qsi.session_id
        LEFT JOIN questions AS q ON q.id = qsi.question_id
        WHERE qsi.score_earned IS NOT NULL
        ORDER BY qs.id ASC, qsi.question_id ASC
        """
    ).fetchall()
    for row in rows:
        bundle_variant_id = row["bundle_variant_id"] or _bundle_variant_id_for_resolved(
            connection,
            question_id=int(row["question_id"]),
            resolved_prompt=row["resolved_prompt"],
            resolved_type_config_json=row["resolved_type_config_json"],
        )
        connection.execute(
            """
            INSERT INTO attempts (
                session_id,
                user_id,
                question_id,
                module_id,
                bundle_variant_id,
                score_earned,
                score_possible,
                submitted_answer_json,
                answered_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (session_id, question_id) DO NOTHING
            """,
            (
                row["session_id"],
                row["user_id"],
                row["question_id"],
                row["module_id"],
                bundle_variant_id,
                row["score_earned"],
                row["score_possible"],
                row["submitted_answer_json"],
                row["answered_at"],
            ),
        )


def _migrate_attempts_to_slim_rows(connection: DatabaseConnection) -> None:
    existing_tables = _existing_table_names(connection)
    if "attempts" not in existing_tables:
        _create_attempts_table(connection)
        _backfill_attempts_from_quiz_items(connection)
        return

    columns = _table_columns(connection, "attempts")
    if "legacy_question_id" not in columns and "resolved_prompt" not in columns and "created_at" not in columns:
        _create_attempts_table(connection)
        return

    connection.execute("DROP TABLE IF EXISTS attempts_legacy_v10")
    connection.execute("ALTER TABLE attempts RENAME TO attempts_legacy_v10")
    _create_attempts_table(connection)

    rows = connection.execute(
        """
        SELECT
            session_id,
            user_id,
            questions.id AS question_id,
            attempts_legacy_v10.module_id,
            score_earned,
            COALESCE(NULLIF(score_possible, 0), 1) AS score_possible,
            resolved_prompt,
            resolved_type_config_json,
            submitted_answer_json,
            answered_at
        FROM attempts_legacy_v10
        JOIN questions ON questions.id = COALESCE(attempts_legacy_v10.question_id, attempts_legacy_v10.legacy_question_id)
        ORDER BY session_id ASC, questions.id ASC
        """
    ).fetchall()
    for row in rows:
        bundle_variant_id = _bundle_variant_id_for_resolved(
            connection,
            question_id=int(row["question_id"]),
            resolved_prompt=row["resolved_prompt"],
            resolved_type_config_json=row["resolved_type_config_json"],
        )
        connection.execute(
            """
            INSERT INTO attempts (
                session_id,
                user_id,
                question_id,
                module_id,
                bundle_variant_id,
                score_earned,
                score_possible,
                submitted_answer_json,
                answered_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (session_id, question_id) DO NOTHING
            """,
            (
                row["session_id"],
                row["user_id"],
                row["question_id"],
                row["module_id"],
                bundle_variant_id,
                row["score_earned"],
                row["score_possible"],
                row["submitted_answer_json"],
                row["answered_at"],
            ),
        )
    connection.execute("DROP TABLE attempts_legacy_v10")


def _ensure_quiz_session_item_variant_column(connection: DatabaseConnection) -> None:
    connection.execute("ALTER TABLE quiz_session_items ADD COLUMN IF NOT EXISTS bundle_variant_id BIGINT")
    if not _constraint_exists(connection, "quiz_session_items", "fk_quiz_session_items_bundle_variant_question"):
        connection.execute(
            """
            ALTER TABLE quiz_session_items
            ADD CONSTRAINT fk_quiz_session_items_bundle_variant_question
            FOREIGN KEY (bundle_variant_id, question_id)
            REFERENCES question_bundles(id, question_id)
            """
        )


def initialize_database(database_url: str) -> None:
    with connect(database_url) as connection:
        current_version = _schema_version(connection)
        existing_tables = _existing_table_names(connection)

        if existing_tables and current_version == 0:
            raise RuntimeError("Existing PostgreSQL database has no schema version. Refusing to mutate it automatically.")
        if current_version not in {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, CURRENT_SCHEMA_VERSION}:
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
        if current_version in {1, 2, 3, 4, 5, 6, 7, 8}:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS question_bundles (
                    question_id BIGINT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
                    variants_json TEXT NOT NULL
                )
                """
            )
        if current_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}:
            _ensure_question_version_columns(connection)
            _migrate_question_bundles_to_rows(connection)
            _ensure_quiz_session_item_variant_column(connection)
            _migrate_attempts_to_slim_rows(connection)
        if current_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}:
            connection.execute("DROP TABLE IF EXISTS user_review_flags")
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
