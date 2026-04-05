from __future__ import annotations

import csv
import json
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from .database import DatabaseConnection, execute_insert_returning_id, utc_now
from .schemas import ModuleUiCopy, QuestionDraftIn


class ServiceError(Exception):
    status_code = 400


class NotFoundError(ServiceError):
    status_code = 404


class ValidationError(ServiceError):
    status_code = 400


DEFAULT_UI_COPY = ModuleUiCopy().model_dump()
FORCED_UNORDERED_SOURCE_IDS = {"geography-rivers-002", "geography-rivers-005"}
IMPORT_SESSION_TTL_HOURS = 24
UPLOAD_CSV_HEADER = ["prompt", "answers"]
SCHEDULE_INTERVAL_DAYS = [1, 3, 7, 14]
HOT_RECOVERY_TARGET = 2
FULL_CREDIT_TOLERANCE = 1e-9


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return slug or "module"


def normalize_answer(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def normalize_text_key(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def normalize_title_key(value: str) -> str:
    return normalize_text_key(value)


def parse_iso_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def add_days_to_timestamp(value: str, days: int) -> str:
    return (parse_iso_timestamp(value) + timedelta(days=days)).isoformat()


def is_full_credit(score_earned: Optional[float], score_possible: Optional[float]) -> bool:
    if score_earned is None or score_possible is None or score_possible <= 0:
        return False
    return score_earned >= (score_possible - FULL_CREDIT_TOLERANCE)


def json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def parse_json_list(raw_value: Optional[str]) -> list[Any]:
    if not raw_value:
        return []
    parsed = json.loads(raw_value)
    if not isinstance(parsed, list):
        raise ValidationError("Expected a JSON list in seed content.")
    return parsed


def merge_ui_copy(raw_value: Optional[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(DEFAULT_UI_COPY)
    if raw_value:
        merged.update({key: value for key, value in raw_value.items() if value is not None})
    return merged


def render_inline_segments(segments: list[str]) -> str:
    return "[_]".join(segments)


def serialize_type_config(payload: QuestionDraftIn) -> dict[str, Any]:
    type_config = {
        "accepted_answers": payload.accepted_answers,
        "segments": payload.segments,
    }
    if payload.slot_prompts:
        type_config["slot_prompts"] = payload.slot_prompts
    return type_config


def public_type_config(question_type: str, type_config: dict[str, Any]) -> dict[str, Any]:
    if question_type == "single_text":
        return {"expected_slots": 1}
    if question_type in {"multi_text", "ordered_multi"}:
        return {"expected_slots": len(type_config.get("accepted_answers", []))}
    return {"segments": type_config.get("segments", [])}


def canonical_answers(type_config: dict[str, Any]) -> list[str]:
    return [" / ".join(group) for group in type_config.get("accepted_answers", [])]


def score_possible(type_config: dict[str, Any]) -> float:
    return 1.0


def preview_prompt(prompt: str, question_type: str, type_config: dict[str, Any]) -> str:
    if question_type == "inline_cloze":
        rendered = render_inline_segments(type_config.get("segments", []))
        return rendered if len(rendered) <= 120 else f"{rendered[:117]}..."
    return prompt if len(prompt) <= 120 else f"{prompt[:117]}..."


def question_prompt_key(question_type: str, prompt: str, type_config: dict[str, Any]) -> str:
    if question_type == "inline_cloze":
        return normalize_text_key(render_inline_segments(type_config.get("segments", [])))
    return normalize_text_key(prompt)


def ensure_module_exists(connection: DatabaseConnection, module_id: Optional[int]) -> Optional[Any]:
    if module_id is None:
        return None
    row = connection.execute(
        "SELECT id, title, full_slug, instruction FROM modules WHERE id = ?",
        (module_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Module {module_id} was not found.")
    return row


def ensure_leaf_module(connection: DatabaseConnection, module_id: int) -> Any:
    module = ensure_module_exists(connection, module_id)
    child_count = connection.execute(
        "SELECT COUNT(*) AS child_count FROM modules WHERE parent_id = ?",
        (module_id,),
    ).fetchone()["child_count"]
    if child_count:
        raise ValidationError("Questions can only be added to leaf modules.")
    return module


def ensure_module_can_accept_children(connection: DatabaseConnection, module_id: int) -> Any:
    module = ensure_module_exists(connection, module_id)
    question_count = connection.execute(
        "SELECT COUNT(*) AS question_count FROM questions WHERE module_id = ?",
        (module_id,),
    ).fetchone()["question_count"]
    if question_count:
        raise ValidationError("Cannot add child modules under a module that already contains questions.")
    return module


def ensure_unique_module_title(
    connection: DatabaseConnection,
    title: str,
    parent_id: Optional[int],
    *,
    exclude_module_id: Optional[int] = None,
) -> None:
    sibling_rows = connection.execute(
        "SELECT id, title FROM modules WHERE parent_id IS ?",
        (parent_id,),
    ).fetchall()
    candidate_key = normalize_title_key(title)
    for row in sibling_rows:
        if exclude_module_id is not None and row["id"] == exclude_module_id:
            continue
        if normalize_title_key(row["title"]) == candidate_key:
            raise ValidationError("A sibling module with this title already exists.")


def next_unique_slug(connection: DatabaseConnection, title: str, parent_id: Optional[int]) -> tuple[str, str]:
    base_slug = slugify_title(title)
    sibling_rows = connection.execute(
        "SELECT slug FROM modules WHERE parent_id IS ?",
        (parent_id,),
    ).fetchall()
    existing = {row["slug"] for row in sibling_rows}
    slug = base_slug
    suffix = 2
    while slug in existing:
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    if parent_id is None:
        return slug, slug

    parent_row = ensure_module_exists(connection, parent_id)
    return slug, f"{parent_row['full_slug']}/{slug}"


def _module_question_rows(connection: DatabaseConnection, module_id: int) -> list[Any]:
    return connection.execute(
        """
        SELECT id, question_type, prompt, type_config_json
        FROM questions
        WHERE module_id = ?
        """,
        (module_id,),
    ).fetchall()


def ensure_unique_question_prompt(
    connection: DatabaseConnection,
    *,
    module_id: int,
    question_type: str,
    prompt: str,
    type_config: dict[str, Any],
    exclude_question_id: Optional[int] = None,
) -> None:
    candidate_key = question_prompt_key(question_type, prompt, type_config)
    for row in _module_question_rows(connection, module_id):
        if exclude_question_id is not None and row["id"] == exclude_question_id:
            continue
        existing_type_config = json.loads(row["type_config_json"])
        if question_prompt_key(row["question_type"], row["prompt"], existing_type_config) == candidate_key:
            raise ValidationError("Prompt already exists in this leaf module.")


def create_module(
    connection: DatabaseConnection,
    *,
    title: str,
    parent_id: Optional[int],
    instruction: str,
    ui_copy: dict[str, Any],
) -> dict[str, Any]:
    if parent_id is not None:
        ensure_module_can_accept_children(connection, parent_id)
    ensure_unique_module_title(connection, title.strip(), parent_id)
    slug, full_slug = next_unique_slug(connection, title, parent_id)
    module_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO modules (source_id, parent_id, title, slug, full_slug, instruction, ui_copy_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (None, parent_id, title.strip(), slug, full_slug, instruction.strip(), json_dumps(merge_ui_copy(ui_copy)), utc_now()),
    )
    return {
        "id": module_id,
        "title": title.strip(),
        "slug": slug,
        "full_slug": full_slug,
        "instruction": instruction.strip(),
        "ui_copy": merge_ui_copy(ui_copy),
    }


def get_module_tree(connection: DatabaseConnection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, source_id, parent_id, title, slug, full_slug, instruction, ui_copy_json
        FROM modules
        ORDER BY full_slug
        """
    ).fetchall()

    nodes: dict[int, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []
    for row in rows:
        nodes[row["id"]] = {
            "id": row["id"],
            "source_id": row["source_id"],
            "title": row["title"],
            "slug": row["slug"],
            "full_slug": row["full_slug"],
            "instruction": row["instruction"] or "",
            "ui_copy": merge_ui_copy(json.loads(row["ui_copy_json"])),
            "children": [],
            "_parent_id": row["parent_id"],
        }

    for node in nodes.values():
        parent_id = node.pop("_parent_id")
        if parent_id is None:
            roots.append(node)
        else:
            nodes[parent_id]["children"].append(node)
    return roots


def get_scope_module_ids(connection: DatabaseConnection, module_id: Optional[int]) -> list[int]:
    if module_id is None:
        rows = connection.execute("SELECT id FROM modules ORDER BY id").fetchall()
        return [row["id"] for row in rows]

    ensure_module_exists(connection, module_id)
    rows = connection.execute(
        """
        WITH RECURSIVE scope(id) AS (
            SELECT id FROM modules WHERE id = ?
            UNION ALL
            SELECT modules.id
            FROM modules
            JOIN scope ON modules.parent_id = scope.id
        )
        SELECT id FROM scope ORDER BY id
        """,
        (module_id,),
    ).fetchall()
    return [row["id"] for row in rows]


def list_users(connection: DatabaseConnection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, handle, display_name, created_at, disabled_at
        FROM users
        ORDER BY lower(display_name) ASC, id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_user(connection: DatabaseConnection, *, handle: str, display_name: str) -> dict[str, Any]:
    cleaned_handle = handle.strip()
    cleaned_display_name = display_name.strip()
    if not cleaned_handle:
        raise ValidationError("User handle is required.")
    if not cleaned_display_name:
        raise ValidationError("Display name is required.")

    existing = connection.execute(
        "SELECT id FROM users WHERE lower(handle) = lower(?)",
        (cleaned_handle,),
    ).fetchone()
    if existing is not None:
        raise ValidationError("User handle already exists.")

    created_at = utc_now()
    user_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO users (handle, display_name, created_at, disabled_at)
        VALUES (?, ?, ?, NULL)
        """,
        (cleaned_handle, cleaned_display_name, created_at),
    )
    return {
        "id": user_id,
        "handle": cleaned_handle,
        "display_name": cleaned_display_name,
        "created_at": created_at,
        "disabled_at": None,
    }


def ensure_user_exists(connection: DatabaseConnection, user_id: int) -> Any:
    row = connection.execute(
        """
        SELECT id, handle, display_name, created_at, disabled_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None or row["disabled_at"] is not None:
        raise NotFoundError(f"User {user_id} was not found.")
    return row


def _review_flags_by_question(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_ids: Optional[list[int]] = None,
) -> dict[int, bool]:
    if question_ids is not None and not question_ids:
        return {}

    where_sql = ""
    params: list[Any] = [user_id]
    if question_ids is not None:
        placeholders = ",".join("?" for _ in question_ids)
        where_sql = f"AND question_id IN ({placeholders})"
        params.extend(question_ids)

    rows = connection.execute(
        f"""
        SELECT question_id, review_flag
        FROM user_review_flags
        WHERE user_id = ? {where_sql}
        """,
        tuple(params),
    ).fetchall()
    return {row["question_id"]: bool(row["review_flag"]) for row in rows}


def _question_attempt_history(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_ids: Optional[list[int]] = None,
) -> dict[int, list[dict[str, Any]]]:
    if question_ids is not None and not question_ids:
        return {}

    where_sql = "WHERE qs.user_id = ? AND qsi.score_earned IS NOT NULL"
    params: list[Any] = [user_id]
    if question_ids is not None:
        placeholders = ",".join("?" for _ in question_ids)
        where_sql += f" AND qsi.question_id IN ({placeholders})"
        params.extend(question_ids)

    rows = connection.execute(
        f"""
        SELECT
            qsi.question_id,
            qsi.score_earned,
            qsi.score_possible,
            COALESCE(qs.completed_at, qs.created_at) AS answered_at,
            qs.id AS session_id
        FROM quiz_session_items AS qsi
        JOIN quiz_sessions AS qs ON qs.id = qsi.session_id
        {where_sql}
        ORDER BY qsi.question_id ASC, answered_at ASC, session_id ASC
        """,
        tuple(params),
    ).fetchall()

    history: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        history.setdefault(row["question_id"], []).append(
            {
                "score_earned": row["score_earned"],
                "score_possible": row["score_possible"],
                "answered_at": row["answered_at"],
            }
        )
    return history


def _derive_schedule_state_from_attempts(attempts: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    incorrect_indices = [
        index
        for index, attempt in enumerate(attempts)
        if not is_full_credit(attempt["score_earned"], attempt["score_possible"])
    ]
    if not incorrect_indices:
        return None

    last_incorrect_index = incorrect_indices[-1]
    last_incorrect_attempt = attempts[last_incorrect_index]
    later_full_correct_attempts = [
        attempt
        for attempt in attempts[last_incorrect_index + 1 :]
        if is_full_credit(attempt["score_earned"], attempt["score_possible"])
    ]
    latest_attempt = attempts[-1]

    if not is_full_credit(latest_attempt["score_earned"], latest_attempt["score_possible"]):
        return {
            "recovery_streak": 0,
            "interval_step": 0,
            "last_incorrect_at": last_incorrect_attempt["answered_at"],
            "next_due_at": None,
            "last_answered_at": latest_attempt["answered_at"],
        }

    if len(later_full_correct_attempts) == 1:
        return {
            "recovery_streak": 1,
            "interval_step": 0,
            "last_incorrect_at": last_incorrect_attempt["answered_at"],
            "next_due_at": None,
            "last_answered_at": latest_attempt["answered_at"],
        }

    interval_step = min(len(later_full_correct_attempts) - HOT_RECOVERY_TARGET, len(SCHEDULE_INTERVAL_DAYS) - 1)
    return {
        "recovery_streak": HOT_RECOVERY_TARGET,
        "interval_step": interval_step,
        "last_incorrect_at": last_incorrect_attempt["answered_at"],
        "next_due_at": add_days_to_timestamp(
            later_full_correct_attempts[-1]["answered_at"],
            SCHEDULE_INTERVAL_DAYS[interval_step],
        ),
        "last_answered_at": latest_attempt["answered_at"],
    }


def _schedule_snapshot_from_attempts(
    attempts: list[dict[str, Any]],
    *,
    now: str,
) -> dict[str, Any]:
    if not attempts:
        return {
            "bucket": "unseen",
            "recovery_streak": None,
            "interval_step": None,
            "last_incorrect_at": None,
            "next_due_at": None,
            "last_answered_at": None,
        }

    state = _derive_schedule_state_from_attempts(attempts)
    if state is None:
        latest_attempt = attempts[-1]
        if len(attempts) == 1 and is_full_credit(latest_attempt["score_earned"], latest_attempt["score_possible"]):
            bucket = "one_shot_easy"
        else:
            bucket = "backlog_seen_correct"
        return {
            "bucket": bucket,
            "recovery_streak": None,
            "interval_step": None,
            "last_incorrect_at": None,
            "next_due_at": None,
            "last_answered_at": latest_attempt["answered_at"],
        }

    bucket = "hot"
    if state["next_due_at"] is not None:
        bucket = "due_review" if parse_iso_timestamp(state["next_due_at"]) <= parse_iso_timestamp(now) else "not_due_recovered"
    return {
        "bucket": bucket,
        **state,
    }


def create_question(connection: DatabaseConnection, payload: QuestionDraftIn) -> dict[str, int]:
    ensure_leaf_module(connection, payload.module_id)
    type_config = serialize_type_config(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=payload.prompt.strip(),
        type_config=type_config,
    )
    question_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO questions (source_id, module_id, question_type, prompt, rank, type_config_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            None,
            payload.module_id,
            payload.question_type,
            payload.prompt.strip(),
            int(payload.rank),
            json_dumps(type_config),
        ),
    )
    return {"question_id": question_id}


def revise_question(connection: DatabaseConnection, question_id: int, payload: QuestionDraftIn, *, reset_stats: bool) -> dict[str, int]:
    current = connection.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone()
    if current is None:
        raise NotFoundError(f"Question {question_id} was not found.")

    ensure_leaf_module(connection, payload.module_id)
    type_config = serialize_type_config(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=payload.prompt.strip(),
        type_config=type_config,
        exclude_question_id=question_id,
    )
    if reset_stats:
        connection.execute("DELETE FROM quiz_session_items WHERE question_id = ?", (question_id,))
        connection.execute("DELETE FROM user_review_flags WHERE question_id = ?", (question_id,))

    connection.execute(
        """
        UPDATE questions
        SET
            module_id = ?,
            question_type = ?,
            prompt = ?,
            rank = ?,
            type_config_json = ?
        WHERE id = ?
        """,
        (
            payload.module_id,
            payload.question_type,
            payload.prompt.strip(),
            int(payload.rank),
            json_dumps(type_config),
            question_id,
        ),
    )
    connection.execute("DELETE FROM user_review_flags WHERE question_id = ?", (question_id,))
    return {"question_id": question_id}


def set_question_review_flag(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_id: int,
    review_flag: bool,
) -> dict[str, Any]:
    ensure_user_exists(connection, user_id)
    row = connection.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Question {question_id} was not found.")
    connection.execute(
        """
        INSERT INTO user_review_flags (user_id, question_id, review_flag, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, question_id) DO UPDATE SET
            review_flag = excluded.review_flag,
            updated_at = excluded.updated_at
        """,
        (user_id, question_id, int(review_flag), utc_now()),
    )
    return {"question_id": question_id, "review_flag": review_flag}


def _question_stats_by_question(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_ids: Optional[list[int]] = None,
) -> dict[int, dict[str, Any]]:
    if question_ids is not None and not question_ids:
        return {}

    where_sql = "WHERE qs.user_id = ? AND qsi.score_earned IS NOT NULL"
    params: list[Any] = [user_id]
    if question_ids is not None:
        placeholders = ",".join("?" for _ in question_ids)
        where_sql += f" AND qsi.question_id IN ({placeholders})"
        params.extend(question_ids)

    rows = connection.execute(
        f"""
        SELECT
            qsi.question_id,
            COUNT(*) AS attempts_count,
            COALESCE(SUM(qsi.score_earned), 0) AS correct_count,
            COALESCE(SUM(qsi.score_possible - qsi.score_earned), 0) AS incorrect_count,
            MAX(COALESCE(qs.completed_at, qs.created_at)) AS last_asked_at
        FROM quiz_session_items AS qsi
        JOIN quiz_sessions AS qs ON qs.id = qsi.session_id
        {where_sql}
        GROUP BY qsi.question_id
        """,
        tuple(params),
    ).fetchall()
    return {
        row["question_id"]: {
            "attempts_count": row["attempts_count"],
            "correct_count": row["correct_count"],
            "incorrect_count": row["incorrect_count"],
            "last_asked_at": row["last_asked_at"],
        }
        for row in rows
    }


def _recent_incorrect_answers_by_question(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_ids: list[int],
    limit_per_question: int = 5,
) -> dict[int, list[dict[str, Any]]]:
    if not question_ids:
        return {}

    placeholders = ",".join("?" for _ in question_ids)
    rows = connection.execute(
        f"""
        SELECT
            qsi.question_id,
            qsi.submitted_answer_json,
            COALESCE(qs.completed_at, qs.created_at) AS answered_at
        FROM quiz_session_items AS qsi
        JOIN quiz_sessions AS qs ON qs.id = qsi.session_id
        WHERE qs.user_id = ?
          AND qsi.question_id IN ({placeholders})
          AND qsi.score_earned IS NOT NULL
          AND qsi.score_earned + ? < qsi.score_possible
          AND qsi.submitted_answer_json IS NOT NULL
        ORDER BY answered_at DESC, qs.id DESC
        """,
        (user_id, *question_ids, FULL_CREDIT_TOLERANCE),
    ).fetchall()

    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        bucket = grouped.setdefault(row["question_id"], [])
        if len(bucket) >= limit_per_question:
            continue
        bucket.append(
            {
                "submitted_answer": json.loads(row["submitted_answer_json"]),
                "answered_at": row["answered_at"],
            }
        )
    return grouped


def _iso_timestamp_sort_value(value: Optional[str], *, descending: bool = False) -> float:
    if not value:
        return float("-inf") if descending else float("inf")
    timestamp = parse_iso_timestamp(value).timestamp()
    return -timestamp if descending else timestamp


def _bucketed_question_selection(
    candidates: list[dict[str, Any]],
    *,
    count: int,
    now: str,
) -> list[dict[str, Any]]:
    if count <= 0 or not candidates:
        return []

    hot: list[dict[str, Any]] = []
    due_review: list[dict[str, Any]] = []
    unseen: list[dict[str, Any]] = []
    one_shot_easy: list[dict[str, Any]] = []
    backlog_seen_correct: list[dict[str, Any]] = []
    not_due_recovered: list[dict[str, Any]] = []
    _ = now

    for candidate in candidates:
        bucket = candidate["bucket"]
        if bucket == "hot":
            hot.append(candidate)
        elif bucket == "due_review":
            due_review.append(candidate)
        elif bucket == "unseen":
            unseen.append(candidate)
        elif bucket == "one_shot_easy":
            one_shot_easy.append(candidate)
        elif bucket == "not_due_recovered":
            not_due_recovered.append(candidate)
        else:
            backlog_seen_correct.append(candidate)

    hot.sort(
        key=lambda row: (
            _iso_timestamp_sort_value(row.get("last_incorrect_at"), descending=True),
            row.get("recovery_streak", 0),
            row["rank"],
            row["question_id"],
        )
    )
    due_review.sort(
        key=lambda row: (
            _iso_timestamp_sort_value(row.get("next_due_at")),
            row["rank"],
            row["question_id"],
        )
    )
    unseen.sort(key=lambda row: (row["rank"], row["question_id"]))
    one_shot_easy.sort(
        key=lambda row: (
            _iso_timestamp_sort_value(row.get("last_asked_at")),
            row["rank"],
            row["question_id"],
        )
    )
    backlog_seen_correct.sort(
        key=lambda row: (
            _iso_timestamp_sort_value(row.get("last_asked_at")),
            row["rank"],
            row["question_id"],
        )
    )
    not_due_recovered.sort(
        key=lambda row: (
            _iso_timestamp_sort_value(row.get("next_due_at")),
            row["rank"],
            row["question_id"],
        )
    )

    selected: list[dict[str, Any]] = []
    for bucket in (hot, due_review, unseen):
        remaining = count - len(selected)
        if remaining <= 0:
            break
        selected.extend(bucket[:remaining])

    unseen_exists = bool(unseen)
    if len(selected) < count and not unseen_exists:
        remaining = count - len(selected)
        selected.extend(one_shot_easy[:remaining])

    for bucket in (backlog_seen_correct, not_due_recovered):
        remaining = count - len(selected)
        if remaining <= 0:
            break
        selected.extend(bucket[:remaining])

    return selected


def create_quiz_session(
    connection: DatabaseConnection,
    *,
    user_id: int,
    module_id: Optional[int],
    count: int,
    rng: Optional[random.Random] = None,
) -> dict[str, Any]:
    _ = rng
    ensure_user_exists(connection, user_id)
    scope_module_ids = get_scope_module_ids(connection, module_id)
    placeholders = ",".join("?" for _ in scope_module_ids) or "NULL"
    candidate_rows = connection.execute(
        f"""
        SELECT
            q.id AS question_id,
            q.module_id,
            m.title AS module_title,
            m.instruction AS module_instruction,
            q.prompt,
            q.question_type,
            q.rank,
            q.type_config_json
        FROM questions AS q
        JOIN modules AS m ON m.id = q.module_id
        WHERE q.module_id IN ({placeholders})
        ORDER BY q.id
        """,
        tuple(scope_module_ids),
    ).fetchall()

    question_ids = [row["question_id"] for row in candidate_rows]
    review_flags = _review_flags_by_question(connection, user_id=user_id, question_ids=question_ids)
    stats_by_question = _question_stats_by_question(connection, user_id=user_id, question_ids=question_ids)
    history_by_question = _question_attempt_history(connection, user_id=user_id, question_ids=question_ids)
    now = utc_now()
    scheduled_candidates: list[dict[str, Any]] = []
    for row in candidate_rows:
        stats = stats_by_question.get(
            row["question_id"],
            {"attempts_count": 0, "correct_count": 0.0, "incorrect_count": 0.0, "last_asked_at": None},
        )
        schedule = _schedule_snapshot_from_attempts(history_by_question.get(row["question_id"], []), now=now)
        scheduled_candidates.append(
            {
                **dict(row),
                **stats,
                **schedule,
                "review_flag": review_flags.get(row["question_id"], False),
            }
        )

    chosen_rows = _bucketed_question_selection(
        scheduled_candidates,
        count=min(count, len(scheduled_candidates)),
        now=now,
    )
    session_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO quiz_sessions (user_id, module_id, created_at)
        VALUES (?, ?, ?)
        """,
        (user_id, module_id, now),
    )

    items: list[dict[str, Any]] = []
    for index, row in enumerate(chosen_rows, start=1):
        type_config = json.loads(row["type_config_json"])
        connection.execute(
            """
            INSERT INTO quiz_session_items (session_id, question_id, score_earned, score_possible)
            VALUES (?, ?, NULL, ?)
            """,
            (session_id, row["question_id"], score_possible(type_config)),
        )
        items.append(
            {
                "id": row["question_id"],
                "position": index,
                "question_id": row["question_id"],
                "module_id": row["module_id"],
                "module_title": row["module_title"],
                "module_instruction": row["module_instruction"] or "",
                "review_flag": bool(row["review_flag"]),
                "prompt": row["prompt"],
                "question_type": row["question_type"],
                "rank": row["rank"],
                "type_config": public_type_config(row["question_type"], type_config),
                "submitted_answer": None,
                "is_correct": None,
                "score_earned": None,
                "score_possible": score_possible(type_config),
            }
        )

    return {
        "id": session_id,
        "module_id": module_id,
        "completed_at": None,
        "items": items,
    }


def _unordered_multi_alignment(expected_groups: list[list[str]], normalized_inputs: list[str]) -> list[Optional[int]]:
    normalized_expected_groups = [{normalize_answer(answer) for answer in group} for group in expected_groups]
    padded_inputs = normalized_inputs[: len(expected_groups)] + [""] * max(0, len(expected_groups) - len(normalized_inputs))

    def match_slots(input_index: int, remaining_indices: list[int]) -> list[Optional[int]]:
        if input_index >= len(padded_inputs):
            return []

        best_match = [None, *match_slots(input_index + 1, remaining_indices)]
        best_score = sum(1 for value in best_match if value is not None)
        submitted = padded_inputs[input_index]
        for expected_index in remaining_indices:
            if submitted in normalized_expected_groups[expected_index]:
                next_remaining = [value for value in remaining_indices if value != expected_index]
                candidate = [expected_index, *match_slots(input_index + 1, next_remaining)]
                candidate_score = sum(1 for value in candidate if value is not None)
                if candidate_score > best_score:
                    best_match = candidate
                    best_score = candidate_score
        return best_match

    return match_slots(0, list(range(len(normalized_expected_groups))))


def evaluate_answers(
    question_type: str,
    type_config: dict[str, Any],
    answers: list[str],
) -> tuple[bool, float, float, list[dict[str, Any]]]:
    normalized_inputs = [normalize_answer(answer) for answer in answers]
    expected_groups = type_config.get("accepted_answers", [])
    possible_score = float(score_possible(type_config))
    slot_total = max(len(expected_groups), 1)

    if question_type == "multi_text":
        aligned_expected_indices = _unordered_multi_alignment(expected_groups, normalized_inputs)
        used_expected_indices = {value for value in aligned_expected_indices if value is not None}
        remaining_expected_indices = [index for index in range(len(expected_groups)) if index not in used_expected_indices]
        slot_results = []
        for index, matched_expected_index in enumerate(aligned_expected_indices):
            if matched_expected_index is not None:
                expected_text = " / ".join(expected_groups[matched_expected_index])
            elif remaining_expected_indices:
                expected_text = " / ".join(expected_groups[remaining_expected_indices.pop(0)])
            elif expected_groups:
                expected_text = " / ".join(expected_groups[min(index, len(expected_groups) - 1)])
            else:
                expected_text = ""
            slot_results.append(
                {
                    "index": index,
                    "is_correct": matched_expected_index is not None,
                    "expected": expected_text,
                }
            )
        earned_score = len(used_expected_indices) / slot_total
        return earned_score == possible_score, earned_score, possible_score, slot_results

    slot_results = []
    all_correct = True
    correct_slots = 0
    for index, expected_group in enumerate(expected_groups):
        submitted = normalized_inputs[index] if index < len(normalized_inputs) else ""
        expected_normalized = {normalize_answer(answer) for answer in expected_group}
        is_correct = submitted in expected_normalized
        slot_results.append({"index": index, "is_correct": is_correct, "expected": " / ".join(expected_group)})
        all_correct = all_correct and is_correct
        if is_correct:
            correct_slots += 1

    earned_score = correct_slots / slot_total
    if question_type == "single_text" and len(expected_groups) == 1:
        return slot_results[0]["is_correct"], earned_score, possible_score, slot_results
    return all_correct, earned_score, possible_score, slot_results


def submit_answer(
    connection: DatabaseConnection,
    *,
    user_id: int,
    session_id: int,
    item_id: int,
    answers: list[str],
) -> dict[str, Any]:
    ensure_user_exists(connection, user_id)
    row = connection.execute(
        """
        SELECT
            qsi.question_id,
            qsi.score_earned,
            qsi.score_possible,
            q.question_type,
            q.type_config_json
        FROM quiz_session_items AS qsi
        JOIN quiz_sessions AS qs ON qs.id = qsi.session_id
        JOIN questions AS q ON q.id = qsi.question_id
        WHERE qsi.session_id = ? AND qsi.question_id = ? AND qs.user_id = ?
        """,
        (session_id, item_id, user_id),
    ).fetchone()
    if row is None:
        raise NotFoundError("Quiz session item was not found.")
    if row["score_earned"] is not None:
        raise ValidationError("Quiz session item has already been answered.")

    type_config = json.loads(row["type_config_json"])
    is_correct, earned_score, possible_score, slot_results = evaluate_answers(row["question_type"], type_config, answers)
    answered_at = utc_now()
    connection.execute(
        """
        UPDATE quiz_session_items
        SET score_earned = ?, score_possible = ?, submitted_answer_json = ?
        WHERE session_id = ? AND question_id = ?
        """,
        (earned_score, possible_score, json_dumps(answers), session_id, item_id),
    )

    pending = connection.execute(
        """
        SELECT COUNT(*) AS pending_count
        FROM quiz_session_items
        WHERE session_id = ? AND score_earned IS NULL
        """,
        (session_id,),
    ).fetchone()["pending_count"]
    session_completed = pending == 0
    if session_completed:
        connection.execute(
            "UPDATE quiz_sessions SET completed_at = COALESCE(completed_at, ?) WHERE id = ?",
            (answered_at, session_id),
        )

    return {
        "item_id": item_id,
        "is_correct": is_correct,
        "score_earned": earned_score,
        "score_possible": possible_score,
        "slot_results": slot_results,
        "canonical_answers": canonical_answers(type_config),
        "session_completed": session_completed,
        "submitted_answer": answers,
    }


def get_stats(
    connection: DatabaseConnection,
    *,
    user_id: int,
    module_id: Optional[int],
    review_only: bool,
) -> dict[str, Any]:
    ensure_user_exists(connection, user_id)
    scope_ids = get_scope_module_ids(connection, module_id)
    placeholders = ",".join("?" for _ in scope_ids) or "NULL"

    question_rows = connection.execute(
        f"""
        SELECT
            q.id AS question_id,
            q.module_id,
            m.title AS module_title,
            m.full_slug AS module_full_slug,
            q.prompt,
            q.question_type,
            q.rank,
            q.type_config_json
        FROM questions AS q
        JOIN modules AS m ON m.id = q.module_id
        WHERE q.module_id IN ({placeholders})
        ORDER BY q.id ASC
        """,
        tuple(scope_ids),
    ).fetchall()

    question_ids = [row["question_id"] for row in question_rows]
    review_flags = _review_flags_by_question(connection, user_id=user_id, question_ids=question_ids)
    stats_by_question = _question_stats_by_question(connection, user_id=user_id, question_ids=question_ids)
    history_by_question = _question_attempt_history(connection, user_id=user_id, question_ids=question_ids)
    recent_incorrect_answers = _recent_incorrect_answers_by_question(
        connection,
        user_id=user_id,
        question_ids=question_ids,
    )

    now = utc_now()
    questions = []
    for row in question_rows:
        review_flag = review_flags.get(row["question_id"], False)
        if review_only and not review_flag:
            continue

        stats = stats_by_question.get(
            row["question_id"],
            {"attempts_count": 0, "correct_count": 0.0, "incorrect_count": 0.0, "last_asked_at": None},
        )
        schedule = _schedule_snapshot_from_attempts(history_by_question.get(row["question_id"], []), now=now)
        type_config = json.loads(row["type_config_json"])
        denominator = stats["correct_count"] + stats["incorrect_count"]
        questions.append(
            {
                "question_id": row["question_id"],
                "module_id": row["module_id"],
                "module_title": row["module_title"],
                "module_full_slug": row["module_full_slug"],
                "prompt": row["prompt"],
                "prompt_preview": preview_prompt(row["prompt"], row["question_type"], type_config),
                "question_type": row["question_type"],
                "rank": row["rank"],
                "attempts": stats["attempts_count"],
                "correct_percentage": (stats["correct_count"] / denominator) if denominator else 0.0,
                "last_asked_at": stats["last_asked_at"],
                "review_flag": review_flag,
                "accepted_answers": type_config["accepted_answers"],
                "slot_prompts": type_config.get("slot_prompts", []),
                "segments": type_config.get("segments", []),
                "recent_incorrect_answers": recent_incorrect_answers.get(row["question_id"], []),
                "schedule": {
                    "bucket": schedule["bucket"],
                    "recovery_streak": schedule["recovery_streak"],
                    "interval_step": schedule["interval_step"],
                    "last_incorrect_at": schedule["last_incorrect_at"],
                    "next_due_at": schedule["next_due_at"],
                },
            }
        )

    questions.sort(
        key=lambda row: (
            0 if row["review_flag"] else 1,
            row["last_asked_at"] is None,
            _iso_timestamp_sort_value(row["last_asked_at"], descending=True),
            row["rank"],
            row["question_id"],
        )
    )

    total_questions = len(question_rows)
    reviewed_questions = sum(1 for question_id in question_ids if review_flags.get(question_id, False))
    total_attempts = sum(stats["attempts_count"] for stats in stats_by_question.values())
    total_correct = sum(stats["correct_count"] for stats in stats_by_question.values())
    total_possible = sum(stats["correct_count"] + stats["incorrect_count"] for stats in stats_by_question.values())

    session_scope_filter = "qs.user_id = ? AND qs.module_id IS NULL" if module_id is None else "qs.user_id = ? AND qs.module_id = ?"
    session_scope_params: tuple[Any, ...] = (user_id,) if module_id is None else (user_id, module_id)
    recent_rows = connection.execute(
        f"""
        SELECT *
        FROM (
            SELECT
                qs.id AS session_id,
                qs.created_at,
                COUNT(qsi.question_id) AS answered_count,
                COALESCE(SUM(qsi.score_earned), 0) AS correct_count,
                COALESCE(SUM(qsi.score_possible), 0) AS score_possible
            FROM quiz_sessions AS qs
            JOIN quiz_session_items AS qsi ON qsi.session_id = qs.id
            WHERE {session_scope_filter} AND qsi.score_earned IS NOT NULL
            GROUP BY qs.id, qs.created_at
            ORDER BY qs.created_at DESC
            LIMIT 10
        ) AS recent
        ORDER BY recent.created_at ASC
        """,
        session_scope_params,
    ).fetchall()

    recent_sessions = [
        {
            "session_id": row["session_id"],
            "created_at": row["created_at"],
            "answered_count": row["answered_count"],
            "correct_count": row["correct_count"],
            "score_possible": row["score_possible"],
            "accuracy": (row["correct_count"] / row["score_possible"]) if row["score_possible"] else 0.0,
        }
        for row in recent_rows
    ]

    return {
        "summary": {
            "total_questions": total_questions,
            "reviewed_questions": reviewed_questions,
            "total_attempts": total_attempts,
            "total_correct": total_correct,
            "total_possible": total_possible,
            "accuracy": (total_correct / total_possible) if total_possible else 0.0,
        },
        "recent_sessions": recent_sessions,
        "questions": questions,
    }


def _strip_utf8_bom(value: str) -> str:
    return value[1:] if value.startswith("\ufeff") else value


def _parse_csv_cells(csv_line: str) -> list[str]:
    try:
        cells = next(csv.reader([csv_line]))
    except csv.Error as error:
        raise ValidationError(f"Malformed CSV row: {error}") from error
    if len(cells) != 2:
        raise ValidationError("Rows must contain exactly 2 columns.")
    return cells


def _split_escaped(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escape = False
    for char in text:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == separator:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if escape:
        raise ValidationError("Dangling escape sequence.")
    parts.append("".join(current))
    return parts


def _parse_answer_group(text: str) -> list[str]:
    values = [value.strip() for value in _split_escaped(text, "|")]
    answers = [value for value in values if value]
    if not answers:
        raise ValidationError("Each answer slot needs at least one accepted answer.")
    return answers


def _parse_inline_prompt(prompt: str) -> tuple[list[str], list[list[str]], str]:
    segments: list[str] = []
    answer_groups: list[list[str]] = []
    current_segment: list[str] = []
    current_group: Optional[list[str]] = None
    escape = False
    saw_group = False

    for char in prompt:
        if escape:
            target = current_group if current_group is not None else current_segment
            target.append(char)
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        if current_group is None:
            if char == "[":
                saw_group = True
                segments.append("".join(current_segment))
                current_segment = []
                current_group = []
                continue
            if char == "]":
                raise ValidationError("Malformed inline cloze prompt.")
            current_segment.append(char)
            continue

        if char == "]":
            group_text = "".join(current_group)
            answers = _parse_answer_group(group_text)
            answer_groups.append(answers)
            current_group = None
            continue

        current_group.append(char)

    if escape or current_group is not None:
        raise ValidationError("Malformed inline cloze prompt.")
    if not saw_group:
        raise ValidationError("Prompt does not contain inline cloze blanks.")

    segments.append("".join(current_segment))
    return segments, answer_groups, render_inline_segments(segments)


def _parse_upload_row(prompt: str, answers: str, row_number: int, module_id: int) -> tuple[str, dict[str, Any]]:
    normalized_prompt = prompt.strip()
    normalized_answers = answers.strip()
    if not normalized_prompt:
        raise ValidationError("Prompt is required.")

    has_inline_marker = bool(re.search(r"(?<!\\)\[", normalized_prompt) or re.search(r"(?<!\\)\]", normalized_prompt))
    if has_inline_marker:
        segments, accepted_answers, rendered_prompt = _parse_inline_prompt(normalized_prompt)
        if normalized_answers:
            raise ValidationError("Inline cloze rows must leave answers empty.")
        payload = QuestionDraftIn(
            module_id=module_id,
            prompt=rendered_prompt,
            question_type="inline_cloze",
            rank=row_number,
            accepted_answers=accepted_answers,
            slot_prompts=[],
            segments=segments,
        )
        return "inline_cloze", payload.model_dump()

    if not normalized_answers:
        raise ValidationError("Answers are required for non-inline questions.")

    ordered = False
    answer_text = normalized_answers
    if answer_text[:8].casefold() == "ordered:":
        ordered = True
        answer_text = answer_text[8:].lstrip()
        if not answer_text:
            raise ValidationError("ordered: rows need at least two answer slots.")

    slot_values = [value.strip() for value in _split_escaped(answer_text, ";")]
    if len(slot_values) > 1:
        accepted_answers = [_parse_answer_group(value) for value in slot_values]
        payload = QuestionDraftIn(
            module_id=module_id,
            prompt=normalized_prompt,
            question_type="ordered_multi" if ordered else "multi_text",
            rank=row_number,
            accepted_answers=accepted_answers,
            slot_prompts=[],
            segments=[],
        )
        return payload.question_type, payload.model_dump()

    if ordered:
        raise ValidationError("ordered: rows need at least two answer slots.")

    payload = QuestionDraftIn(
        module_id=module_id,
        prompt=normalized_prompt,
        question_type="single_text",
        rank=row_number,
        accepted_answers=[_parse_answer_group(answer_text)],
        slot_prompts=[],
        segments=[],
    )
    return "single_text", payload.model_dump()


def _existing_prompt_keys(connection: DatabaseConnection, module_id: int) -> set[str]:
    existing_rows = _module_question_rows(connection, module_id)
    return {
        question_prompt_key(row["question_type"], row["prompt"], json.loads(row["type_config_json"]))
        for row in existing_rows
    }


def _report_text(unresolved_rows: list[dict[str, Any]], *, staged_valid_count: int) -> str:
    if not unresolved_rows:
        if staged_valid_count:
            return "All remaining rows are valid. Commit to save them."
        return "No rows remain in this upload session."
    return "\n".join(
        f"row {row['row_number']} | {'; '.join(row['issues'])} | {row['csv_line']}"
        for row in unresolved_rows
    )


def _build_import_session_response(
    connection: DatabaseConnection,
    session_id: int,
    *,
    committed: bool = False,
    committed_count: int = 0,
) -> dict[str, Any]:
    session_row = connection.execute(
        """
        SELECT id, expires_at, committed_at
        FROM question_import_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()
    if session_row is None:
        raise NotFoundError("Question import session was not found.")

    unresolved_rows = [
        {
            "row_number": row["row_number"],
            "csv_line": row["csv_line"],
            "issues": json.loads(row["issues_json"]),
            "inferred_type": row["inferred_type"],
        }
        for row in connection.execute(
            """
            SELECT row_number, csv_line, issues_json, inferred_type
            FROM question_import_session_rows
            WHERE session_id = ? AND status = 'unresolved'
            ORDER BY row_number
            """,
            (session_id,),
        ).fetchall()
    ]
    staged_valid_count = connection.execute(
        """
        SELECT COUNT(*) AS staged_valid_count
        FROM question_import_session_rows
        WHERE session_id = ? AND status = 'staged'
        """,
        (session_id,),
    ).fetchone()["staged_valid_count"]

    return {
        "session_id": session_id,
        "expires_at": session_row["expires_at"],
        "ready_to_commit": bool(not unresolved_rows and staged_valid_count > 0 and session_row["committed_at"] is None),
        "staged_valid_count": staged_valid_count,
        "unresolved_rows": unresolved_rows,
        "report_text": _report_text(unresolved_rows, staged_valid_count=staged_valid_count),
        "committed": committed,
        "committed_count": committed_count,
    }


def _delete_expired_import_sessions(connection: DatabaseConnection) -> None:
    now = utc_now()
    connection.execute(
        "DELETE FROM question_import_sessions WHERE committed_at IS NULL AND expires_at < ?",
        (now,),
    )


def _active_import_session(connection: DatabaseConnection, session_id: int) -> Any:
    _delete_expired_import_sessions(connection)
    row = connection.execute(
        """
        SELECT id, module_id, expires_at, committed_at
        FROM question_import_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError("Question import session was not found.")
    if row["committed_at"] is not None:
        raise ValidationError("Question import session has already been committed.")
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        connection.execute("DELETE FROM question_import_sessions WHERE id = ?", (session_id,))
        raise ValidationError("Question import session has expired. Upload the CSV again.")
    return row


def _insert_import_session_row(
    connection: DatabaseConnection,
    *,
    session_id: int,
    row_number: int,
    csv_line: str,
    status: str,
    inferred_type: Optional[str],
    payload_json: Optional[str],
    issues: list[str],
) -> None:
    connection.execute(
        """
        INSERT INTO question_import_session_rows (
            session_id,
            row_number,
            csv_line,
            status,
            inferred_type,
            payload_json,
            issues_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            row_number,
            csv_line,
            status,
            inferred_type,
            payload_json,
            json_dumps(issues),
        ),
    )


def _reconcile_initial_upload_rows(
    connection: DatabaseConnection,
    *,
    module_id: int,
    parsed_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_keys = _existing_prompt_keys(connection, module_id)
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in parsed_rows:
        if row["issues"]:
            continue
        payload = row["payload"]
        type_config = serialize_type_config(QuestionDraftIn(**payload))
        key = question_prompt_key(payload["question_type"], payload["prompt"], type_config)
        row["prompt_key"] = key
        groups.setdefault(key, []).append(row)

    for key, rows in groups.items():
        if key in existing_keys:
            for row in rows:
                row["issues"].append("Prompt already exists in this leaf module.")
        if len(rows) > 1:
            for row in rows:
                row["issues"].append("Prompt duplicates another row in this upload.")
    return parsed_rows


def _reconcile_revalidated_rows(
    connection: DatabaseConnection,
    *,
    module_id: int,
    parsed_rows: list[dict[str, Any]],
    trusted_keys: set[str],
) -> list[dict[str, Any]]:
    existing_keys = _existing_prompt_keys(connection, module_id)
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in parsed_rows:
        if row["issues"]:
            continue
        payload = row["payload"]
        type_config = serialize_type_config(QuestionDraftIn(**payload))
        key = question_prompt_key(payload["question_type"], payload["prompt"], type_config)
        row["prompt_key"] = key
        groups.setdefault(key, []).append(row)

    for key, rows in groups.items():
        if key in existing_keys:
            for row in rows:
                row["issues"].append("Prompt already exists in this leaf module.")
        if key in trusted_keys:
            for row in rows:
                row["issues"].append("Prompt duplicates another kept row in this upload.")
        if len(rows) > 1:
            for row in rows:
                row["issues"].append("Prompt duplicates another unresolved row in this upload.")
    return parsed_rows


def create_question_import_session(connection: DatabaseConnection, *, module_id: int, csv_text: str) -> dict[str, Any]:
    ensure_leaf_module(connection, module_id)
    _delete_expired_import_sessions(connection)

    lines = csv_text.splitlines()
    if not lines:
        raise ValidationError("CSV must include the prompt,answers header.")

    header_cells = _parse_csv_cells(_strip_utf8_bom(lines[0]))
    if header_cells != UPLOAD_CSV_HEADER:
        raise ValidationError("CSV header must be exactly prompt,answers.")
    if len(lines) == 1:
        raise ValidationError("CSV must include at least one question row.")

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=IMPORT_SESSION_TTL_HOURS)).isoformat()
    session_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO question_import_sessions (module_id, created_at, expires_at)
        VALUES (?, ?, ?)
        """,
        (module_id, utc_now(), expires_at),
    )

    parsed_rows: list[dict[str, Any]] = []
    for row_number, csv_line in enumerate(lines[1:], start=1):
        issues: list[str] = []
        inferred_type: Optional[str] = None
        payload: Optional[dict[str, Any]] = None
        try:
            prompt, answers = _parse_csv_cells(csv_line)
            inferred_type, payload = _parse_upload_row(prompt, answers, row_number, module_id)
        except ValidationError as error:
            issues.append(str(error))
        parsed_rows.append(
            {
                "row_number": row_number,
                "csv_line": csv_line,
                "inferred_type": inferred_type,
                "payload": payload,
                "issues": issues,
            }
        )

    parsed_rows = _reconcile_initial_upload_rows(connection, module_id=module_id, parsed_rows=parsed_rows)
    for row in parsed_rows:
        status = "staged" if not row["issues"] else "unresolved"
        _insert_import_session_row(
            connection,
            session_id=session_id,
            row_number=row["row_number"],
            csv_line=row["csv_line"],
            status=status,
            inferred_type=row["inferred_type"],
            payload_json=json_dumps(row["payload"]) if row["payload"] and not row["issues"] else None,
            issues=row["issues"],
        )

    return _build_import_session_response(connection, session_id)


def revalidate_question_import_session(
    connection: DatabaseConnection,
    *,
    session_id: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    session_row = _active_import_session(connection, session_id)
    unresolved_db_rows = connection.execute(
        """
        SELECT row_number
        FROM question_import_session_rows
        WHERE session_id = ? AND status = 'unresolved'
        ORDER BY row_number
        """,
        (session_id,),
    ).fetchall()
    expected_row_numbers = [row["row_number"] for row in unresolved_db_rows]
    provided_row_numbers = sorted(row["row_number"] for row in rows)
    if provided_row_numbers != expected_row_numbers:
        raise ValidationError("Revalidation must include the current unresolved rows only.")

    trusted_keys = set()
    for row in connection.execute(
        """
        SELECT payload_json
        FROM question_import_session_rows
        WHERE session_id = ? AND status = 'staged'
        """,
        (session_id,),
    ).fetchall():
        payload = json.loads(row["payload_json"])
        type_config = serialize_type_config(QuestionDraftIn(**payload))
        trusted_keys.add(question_prompt_key(payload["question_type"], payload["prompt"], type_config))

    parsed_rows: list[dict[str, Any]] = []
    row_map = {row["row_number"]: row["csv_line"] for row in rows}
    for row_number in expected_row_numbers:
        csv_line = row_map[row_number]
        issues: list[str] = []
        inferred_type: Optional[str] = None
        payload: Optional[dict[str, Any]] = None
        try:
            prompt, answers = _parse_csv_cells(csv_line)
            inferred_type, payload = _parse_upload_row(prompt, answers, row_number, session_row["module_id"])
        except ValidationError as error:
            issues.append(str(error))
        parsed_rows.append(
            {
                "row_number": row_number,
                "csv_line": csv_line,
                "inferred_type": inferred_type,
                "payload": payload,
                "issues": issues,
            }
        )

    parsed_rows = _reconcile_revalidated_rows(
        connection,
        module_id=session_row["module_id"],
        parsed_rows=parsed_rows,
        trusted_keys=trusted_keys,
    )

    for row in parsed_rows:
        status = "staged" if not row["issues"] else "unresolved"
        connection.execute(
            """
            UPDATE question_import_session_rows
            SET
                csv_line = ?,
                status = ?,
                inferred_type = ?,
                payload_json = ?,
                issues_json = ?
            WHERE session_id = ? AND row_number = ?
            """,
            (
                row["csv_line"],
                status,
                row["inferred_type"],
                json_dumps(row["payload"]) if row["payload"] and not row["issues"] else None,
                json_dumps(row["issues"]),
                session_id,
                row["row_number"],
            ),
        )

    return _build_import_session_response(connection, session_id)


def discard_question_import_session_row(connection: DatabaseConnection, *, session_id: int, row_number: int) -> dict[str, Any]:
    _active_import_session(connection, session_id)
    deleted = connection.execute(
        """
        DELETE FROM question_import_session_rows
        WHERE session_id = ? AND row_number = ? AND status = 'unresolved'
        """,
        (session_id, row_number),
    ).rowcount
    if not deleted:
        raise NotFoundError("Unresolved import row was not found.")
    return _build_import_session_response(connection, session_id)


def commit_question_import_session(connection: DatabaseConnection, *, session_id: int) -> dict[str, Any]:
    session_row = _active_import_session(connection, session_id)
    unresolved_count = connection.execute(
        """
        SELECT COUNT(*) AS unresolved_count
        FROM question_import_session_rows
        WHERE session_id = ? AND status = 'unresolved'
        """,
        (session_id,),
    ).fetchone()["unresolved_count"]
    if unresolved_count:
        return _build_import_session_response(connection, session_id)

    staged_rows = connection.execute(
        """
        SELECT row_number, csv_line, inferred_type, payload_json
        FROM question_import_session_rows
        WHERE session_id = ? AND status = 'staged'
        ORDER BY row_number
        """,
        (session_id,),
    ).fetchall()
    if not staged_rows:
        return _build_import_session_response(connection, session_id)

    existing_keys = _existing_prompt_keys(connection, session_row["module_id"])
    conflicting_row_numbers: list[int] = []
    for row in staged_rows:
        payload = json.loads(row["payload_json"])
        type_config = serialize_type_config(QuestionDraftIn(**payload))
        prompt_key = question_prompt_key(payload["question_type"], payload["prompt"], type_config)
        if prompt_key in existing_keys:
            conflicting_row_numbers.append(row["row_number"])

    if conflicting_row_numbers:
        for row in staged_rows:
            if row["row_number"] not in conflicting_row_numbers:
                continue
            connection.execute(
                """
                UPDATE question_import_session_rows
                SET status = 'unresolved', payload_json = NULL, issues_json = ?
                WHERE session_id = ? AND row_number = ?
                """,
                (
                    json_dumps(["Prompt already exists in this leaf module."]),
                    session_id,
                    row["row_number"],
                ),
            )
        return _build_import_session_response(connection, session_id)

    committed_count = 0
    for row in staged_rows:
        payload = QuestionDraftIn(**json.loads(row["payload_json"]))
        create_question(connection, payload)
        committed_count += 1

    connection.execute(
        "UPDATE question_import_sessions SET committed_at = ? WHERE id = ?",
        (utc_now(), session_id),
    )
    return _build_import_session_response(connection, session_id, committed=True, committed_count=committed_count)


def backfill_session_scores(connection: DatabaseConnection) -> None:
    connection.execute(
        """
        UPDATE quiz_session_items
        SET score_possible = 1
        WHERE score_possible IS NULL OR score_possible = 0
        """
    )


def backfill_question_type_defaults(connection: DatabaseConnection) -> None:
    rows = connection.execute(
        "SELECT id, source_id, question_type, type_config_json FROM questions"
    ).fetchall()
    for row in rows:
        type_config = json.loads(row["type_config_json"])
        changed = False
        question_type = row["question_type"]

        if question_type == "multi_text" and type_config.get("answer_order_matters") is True:
            question_type = "ordered_multi"
            changed = True
        if row["source_id"] in FORCED_UNORDERED_SOURCE_IDS and question_type != "multi_text":
            question_type = "multi_text"
            changed = True
        if "answer_order_matters" in type_config:
            type_config.pop("answer_order_matters", None)
            changed = True

        if changed:
            connection.execute(
                """
                UPDATE questions
                SET question_type = ?, type_config_json = ?
                WHERE id = ?
                """,
                (question_type, json_dumps(type_config), row["id"]),
            )


def sync_seed_content(connection: DatabaseConnection, content_root: Path) -> dict[str, int]:
    content_root = Path(content_root)
    imported_modules = 0
    imported_questions = 0
    module_files = sorted(content_root.rglob("module.yaml"), key=lambda path: (len(path.relative_to(content_root).parts), str(path)))

    module_lookup = {
        row["source_id"]: row["id"]
        for row in connection.execute("SELECT id, source_id FROM modules WHERE source_id IS NOT NULL").fetchall()
    }
    for module_file in module_files:
        data = yaml.safe_load(module_file.read_text()) or {}
        source_id = data["source_id"]
        if source_id in module_lookup:
            continue

        parent_source_id = data.get("parent_source_id")
        parent_id = None
        if parent_source_id:
            parent_id = module_lookup.get(parent_source_id)
            if parent_id is None:
                raise ValidationError(f"Parent module {parent_source_id} must be imported before child {source_id}.")
            ensure_module_can_accept_children(connection, parent_id)
        title = data["title"]
        ui_copy = merge_ui_copy(data.get("ui_copy"))
        ensure_unique_module_title(connection, title, parent_id)
        slug, full_slug = next_unique_slug(connection, title, parent_id)
        module_id = execute_insert_returning_id(
            connection,
            """
            INSERT INTO modules (source_id, parent_id, title, slug, full_slug, instruction, ui_copy_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, parent_id, title, slug, full_slug, (data.get("instruction") or "").strip(), json_dumps(ui_copy), utc_now()),
        )
        module_lookup[source_id] = module_id
        imported_modules += 1

    question_lookup = {
        row["source_id"]
        for row in connection.execute("SELECT source_id FROM questions WHERE source_id IS NOT NULL").fetchall()
    }
    question_files = sorted(content_root.rglob("questions.csv"))
    for question_file in question_files:
        with question_file.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for raw_row in reader:
                source_id = raw_row["source_id"]
                if source_id in question_lookup:
                    continue
                payload = QuestionDraftIn(
                    module_id=module_lookup[raw_row["module_source_id"]],
                    prompt=raw_row["prompt"],
                    question_type=raw_row["type"],
                    rank=int(float(raw_row["ranking"])),
                    accepted_answers=parse_json_list(raw_row.get("accepted_answers_json")),
                    slot_prompts=parse_json_list(raw_row.get("slot_prompts_json")),
                    segments=parse_json_list(raw_row.get("segments_json")),
                )
                question_ids = create_question(connection, payload)
                connection.execute(
                    "UPDATE questions SET source_id = ? WHERE id = ?",
                    (source_id, question_ids["question_id"]),
                )
                question_lookup.add(source_id)
                imported_questions += 1

    backfill_question_type_defaults(connection)
    backfill_session_scores(connection)
    return {"modules": imported_modules, "questions": imported_questions}
