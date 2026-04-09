from __future__ import annotations

import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import (
    FORCED_UNORDERED_PROMPTS,
    FULL_CREDIT_TOLERANCE,
    SCHEDULE_INTERVALS,
)
from .database import DatabaseConnection, execute_insert_returning_id, utc_now
from .schemas import QuestionDraftIn
from .qml import QMLError, parse_qml_line, qml_lines_from_text, render_prompt_and_answers


class ServiceError(Exception):
    status_code = 400


class NotFoundError(ServiceError):
    status_code = 404


class ValidationError(ServiceError):
    status_code = 400


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.strip().lower()).strip("_")
    return slug or "module"


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def title_from_slug(slug: str) -> str:
    value = slug.replace("_", " ").strip()
    return value[:1].upper() + value[1:] if value else ""


def parse_iso_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def add_interval_to_timestamp(value: str, interval: timedelta) -> str:
    return (parse_iso_timestamp(value) + interval).isoformat()


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


def render_inline_segments(segments: list[str]) -> str:
    return "[_]".join(segments)


def serialize_type_config(payload: QuestionDraftIn) -> dict[str, Any]:
    type_config = {
        "accepted_answers": payload.accepted_answers,
        "segments": payload.segments,
    }
    return type_config


def public_type_config(question_type: str, type_config: dict[str, Any]) -> dict[str, Any]:
    if question_type in {"single_text", "computed_text"}:
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
        return normalize_text(render_inline_segments(type_config.get("segments", [])))
    return normalize_text(prompt)


def _module_question_rank_rows(connection: DatabaseConnection, module_id: int) -> list[Any]:
    return connection.execute(
        """
        SELECT id, rank
        FROM questions
        WHERE module_id = ?
        ORDER BY rank ASC, id ASC
        """,
        (module_id,),
    ).fetchall()


def _append_rank(connection: DatabaseConnection, module_id: int) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(rank), 0) AS max_rank FROM questions WHERE module_id = ?",
        (module_id,),
    ).fetchone()
    return int(row["max_rank"]) + 1


def _shift_ranks_for_insert(
    connection: DatabaseConnection,
    *,
    module_id: int,
    insert_rank: int,
    exclude_question_id: Optional[int] = None,
) -> None:
    rows = _module_question_rank_rows(connection, module_id)
    next_rank = 1
    inserted = False
    for row in rows:
        if exclude_question_id is not None and row["id"] == exclude_question_id:
            continue
        if not inserted and next_rank == insert_rank:
            inserted = True
            next_rank += 1
        connection.execute("UPDATE questions SET rank = ? WHERE id = ?", (next_rank, row["id"]))
        next_rank += 1


def _remove_rank_gap(connection: DatabaseConnection, *, module_id: int, exclude_question_id: int) -> None:
    next_rank = 1
    for row in _module_question_rank_rows(connection, module_id):
        if row["id"] == exclude_question_id:
            continue
        connection.execute("UPDATE questions SET rank = ? WHERE id = ?", (next_rank, row["id"]))
        next_rank += 1


def _clamp_insert_rank(connection: DatabaseConnection, *, module_id: int, rank: int, exclude_question_id: Optional[int] = None) -> int:
    rows = [row for row in _module_question_rank_rows(connection, module_id) if exclude_question_id is None or row["id"] != exclude_question_id]
    return max(1, min(int(rank), len(rows) + 1))


def _priority_insert_rank(connection: DatabaseConnection, *, user_id: Optional[int], module_id: int, priority_mode: str) -> int:
    if user_id is None:
        return _append_rank(connection, module_id)

    question_rows = connection.execute(
        """
        SELECT id AS question_id, rank
        FROM questions
        WHERE module_id = ?
        ORDER BY rank ASC, id ASC
        """,
        (module_id,),
    ).fetchall()
    question_ids = [row["question_id"] for row in question_rows]
    history_by_question = _question_attempt_history(connection, user_id=user_id, question_ids=question_ids)
    unseen_rows = [row for row in question_rows if not history_by_question.get(row["question_id"])]
    if not unseen_rows:
        return _append_rank(connection, module_id)

    if priority_mode == "high":
        return int(unseen_rows[0]["rank"])
    if priority_mode == "mid":
        return int(unseen_rows[len(unseen_rows) // 2]["rank"])
    return int(unseen_rows[-1]["rank"]) + 1


def _resolved_runtime(question_type: str, prompt: str, type_config: dict[str, Any], *, rng: Optional[random.Random] = None) -> tuple[str, dict[str, Any]]:
    if question_type != "computed_text":
        return prompt, type_config

    rendered_prompt, rendered_answers = render_prompt_and_answers(
        prompt=prompt,
        accepted_answers=type_config.get("accepted_answers", []),
        rng=rng,
    )
    return rendered_prompt, {"accepted_answers": rendered_answers, "segments": []}


def ensure_module_exists(connection: DatabaseConnection, module_id: Optional[int]) -> Optional[Any]:
    if module_id is None:
        return None
    row = connection.execute(
        "SELECT id, slug, full_slug, instruction FROM modules WHERE id = ?",
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


def ensure_unique_module_slug(
    connection: DatabaseConnection,
    slug: str,
    parent_id: Optional[int],
    *,
    exclude_module_id: Optional[int] = None,
) -> None:
    sibling_rows = connection.execute(
        "SELECT id, slug FROM modules WHERE parent_id IS ?",
        (parent_id,),
    ).fetchall()
    for row in sibling_rows:
        if exclude_module_id is not None and row["id"] == exclude_module_id:
            continue
        if row["slug"] == slug:
            raise ValidationError("A sibling module with this title already exists.")


def build_full_slug(connection: DatabaseConnection, slug: str, parent_id: Optional[int]) -> str:
    if parent_id is None:
        return slug

    parent_row = ensure_module_exists(connection, parent_id)
    return f"{parent_row['full_slug']}/{slug}"


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
) -> dict[str, Any]:
    if parent_id is not None:
        ensure_module_can_accept_children(connection, parent_id)
    slug = slugify_title(title)
    ensure_unique_module_slug(connection, slug, parent_id)
    full_slug = build_full_slug(connection, slug, parent_id)
    module_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO modules (parent_id, slug, full_slug, instruction, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (parent_id, slug, full_slug, instruction.strip(), utc_now()),
    )
    return {
        "id": module_id,
        "title": title_from_slug(slug),
        "slug": slug,
        "full_slug": full_slug,
        "instruction": instruction.strip(),
    }


def get_module_tree(connection: DatabaseConnection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, parent_id, slug, full_slug, instruction
        FROM modules
        ORDER BY full_slug
        """
    ).fetchall()

    nodes: dict[int, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []
    for row in rows:
        nodes[row["id"]] = {
            "id": row["id"],
            "title": title_from_slug(row["slug"]),
            "slug": row["slug"],
            "full_slug": row["full_slug"],
            "instruction": row["instruction"] or "",
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
        SELECT id, handle, display_name, created_at
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
        INSERT INTO users (handle, display_name, created_at)
        VALUES (?, ?, ?)
        """,
        (cleaned_handle, cleaned_display_name, created_at),
    )
    return {
        "id": user_id,
        "handle": cleaned_handle,
        "display_name": cleaned_display_name,
        "created_at": created_at,
    }


def ensure_user_exists(connection: DatabaseConnection, user_id: int) -> Any:
    row = connection.execute(
        """
        SELECT id, handle, display_name, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
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
                "session_id": row["session_id"],
            }
        )
    return history


def _latest_scored_session_id(connection: DatabaseConnection, *, user_id: int) -> Optional[int]:
    row = connection.execute(
        """
        SELECT qs.id
        FROM quiz_sessions AS qs
        JOIN quiz_session_items AS qsi ON qsi.session_id = qs.id
        WHERE qs.user_id = ? AND qsi.score_earned IS NOT NULL
        GROUP BY qs.id, COALESCE(qs.completed_at, qs.created_at)
        ORDER BY COALESCE(qs.completed_at, qs.created_at) DESC, qs.id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return int(row["id"]) if row is not None else None


def _bucket_step_after_hot_recovery(origin_step: Optional[int], failures_after_bucket_retry: int) -> int:
    if origin_step is None:
        return 0
    if failures_after_bucket_retry > 1:
        return max(origin_step - 1, 0)
    return origin_step


def _derive_schedule_state_from_attempts(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    state: dict[str, Any] = {
        "bucket": "unseen",
        "recovery_streak": None,
        "interval_step": None,
        "last_incorrect_at": None,
        "next_due_at": None,
        "last_answered_at": None,
        "last_session_id": None,
        "retry_pending": False,
        "bucket_origin_step": None,
        "failures_after_bucket_retry": 0,
    }

    for attempt in attempts:
        is_correct = is_full_credit(attempt["score_earned"], attempt["score_possible"])
        answered_at = attempt["answered_at"]
        session_id = attempt["session_id"]
        bucket = state["bucket"]

        if bucket == "unseen":
            if is_correct:
                state.update(
                    {
                        "bucket": "mastery",
                        "recovery_streak": None,
                        "interval_step": None,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                    }
                )
            else:
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "interval_step": None,
                        "last_incorrect_at": answered_at,
                        "next_due_at": None,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "retry_pending": False,
                        "bucket_origin_step": None,
                        "failures_after_bucket_retry": 0,
                    }
                )
            continue

        if bucket == "mastery":
            if is_correct:
                state.update({"last_answered_at": answered_at, "last_session_id": session_id})
            else:
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "interval_step": None,
                        "last_incorrect_at": answered_at,
                        "next_due_at": None,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "retry_pending": False,
                        "bucket_origin_step": None,
                        "failures_after_bucket_retry": 0,
                    }
                )
            continue

        if bucket in {"cooling", "due_review"}:
            current_step = int(state["interval_step"])
            if is_correct:
                if current_step >= len(SCHEDULE_INTERVALS) - 1:
                    state.update(
                        {
                            "bucket": "mastery",
                            "recovery_streak": None,
                            "interval_step": None,
                            "last_answered_at": answered_at,
                            "last_session_id": session_id,
                            "next_due_at": None,
                            "retry_pending": False,
                            "bucket_origin_step": None,
                            "failures_after_bucket_retry": 0,
                        }
                    )
                else:
                    next_step = current_step + 1
                    state.update(
                        {
                            "bucket": "cooling",
                            "recovery_streak": None,
                            "interval_step": next_step,
                            "last_answered_at": answered_at,
                            "last_session_id": session_id,
                            "next_due_at": add_interval_to_timestamp(answered_at, SCHEDULE_INTERVALS[next_step][1]),
                            "retry_pending": False,
                            "bucket_origin_step": None,
                            "failures_after_bucket_retry": 0,
                        }
                    )
            else:
                state.update(
                    {
                        "bucket": "bucket_retry_wait",
                        "recovery_streak": None,
                        "interval_step": current_step,
                        "last_incorrect_at": answered_at,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "next_due_at": None,
                        "retry_pending": True,
                        "bucket_origin_step": current_step,
                        "failures_after_bucket_retry": 0,
                    }
                )
            continue

        if bucket == "bucket_retry_wait":
            origin_step = int(state["bucket_origin_step"])
            if is_correct:
                state.update(
                    {
                        "bucket": "cooling",
                        "recovery_streak": None,
                        "interval_step": origin_step,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "next_due_at": add_interval_to_timestamp(answered_at, SCHEDULE_INTERVALS[origin_step][1]),
                        "retry_pending": False,
                        "bucket_origin_step": None,
                        "failures_after_bucket_retry": 0,
                    }
                )
            else:
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "interval_step": None,
                        "last_incorrect_at": answered_at,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "next_due_at": None,
                        "retry_pending": True,
                        "bucket_origin_step": origin_step,
                        "failures_after_bucket_retry": 1,
                    }
                )
            continue

        if bucket == "hot0":
            if is_correct:
                state.update(
                    {
                        "bucket": "hot1",
                        "recovery_streak": 1,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                    }
                )
            else:
                failures = state["failures_after_bucket_retry"]
                if state["bucket_origin_step"] is not None and failures > 0:
                    failures += 1
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "last_incorrect_at": answered_at,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "failures_after_bucket_retry": failures,
                    }
                )
            continue

        if bucket == "hot1":
            if is_correct:
                resolved_step = _bucket_step_after_hot_recovery(
                    state["bucket_origin_step"],
                    int(state["failures_after_bucket_retry"] or 0),
                )
                state.update(
                    {
                        "bucket": "cooling",
                        "recovery_streak": 2,
                        "interval_step": resolved_step,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "next_due_at": add_interval_to_timestamp(answered_at, SCHEDULE_INTERVALS[resolved_step][1]),
                        "retry_pending": False,
                        "bucket_origin_step": None,
                        "failures_after_bucket_retry": 0,
                    }
                )
            else:
                failures = state["failures_after_bucket_retry"]
                if state["bucket_origin_step"] is not None and failures > 0:
                    failures += 1
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "last_incorrect_at": answered_at,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "next_due_at": None,
                        "failures_after_bucket_retry": failures,
                    }
                )
            continue

    return state


def _schedule_snapshot_from_attempts(
    attempts: list[dict[str, Any]],
    *,
    now: str,
    latest_scored_session_id: Optional[int] = None,
) -> dict[str, Any]:
    if not attempts:
        return {
            "bucket": "unseen",
            "recovery_streak": None,
            "interval_step": None,
            "last_incorrect_at": None,
            "next_due_at": None,
            "last_answered_at": None,
            "retry_pending": False,
        }

    state = _derive_schedule_state_from_attempts(attempts)
    bucket = state["bucket"]
    if bucket == "hot1" and latest_scored_session_id is not None and state.get("last_session_id") == latest_scored_session_id:
        bucket = "hot1_sit_out"
    elif bucket == "bucket_retry_wait" and latest_scored_session_id is not None and state.get("last_session_id") != latest_scored_session_id:
        bucket = "due_review"
    elif bucket == "cooling" and state["next_due_at"] is not None and parse_iso_timestamp(state["next_due_at"]) <= parse_iso_timestamp(now):
        bucket = "due_review"

    return {
        "bucket": bucket,
        "recovery_streak": state["recovery_streak"],
        "interval_step": state["interval_step"],
        "bucket_origin_step": state.get("bucket_origin_step"),
        "last_incorrect_at": state["last_incorrect_at"],
        "next_due_at": state["next_due_at"],
        "last_answered_at": state["last_answered_at"],
        "retry_pending": bool(state.get("retry_pending", False)),
        "last_session_id": state.get("last_session_id"),
    }


def create_question(connection: DatabaseConnection, payload: QuestionDraftIn, *, user_id: Optional[int] = None) -> dict[str, int]:
    ensure_leaf_module(connection, payload.module_id)
    type_config = serialize_type_config(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=payload.prompt.strip(),
        type_config=type_config,
    )
    insert_rank = (
        _priority_insert_rank(connection, user_id=user_id, module_id=payload.module_id, priority_mode=payload.priority_mode)
        if payload.priority_mode
        else int(payload.rank)
    )
    insert_rank = _clamp_insert_rank(connection, module_id=payload.module_id, rank=insert_rank)
    _shift_ranks_for_insert(connection, module_id=payload.module_id, insert_rank=insert_rank)
    question_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO questions (module_id, question_type, prompt, rank, type_config_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            payload.module_id,
            payload.question_type,
            payload.prompt.strip(),
            insert_rank,
            json_dumps(type_config),
        ),
    )
    return {"question_id": question_id}


def revise_question(connection: DatabaseConnection, question_id: int, payload: QuestionDraftIn, *, reset_stats: bool) -> dict[str, int]:
    current = connection.execute("SELECT id, module_id, rank FROM questions WHERE id = ?", (question_id,)).fetchone()
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

    target_rank = _clamp_insert_rank(
        connection,
        module_id=payload.module_id,
        rank=int(payload.rank),
        exclude_question_id=question_id,
    )
    if int(current["module_id"]) != payload.module_id:
        _remove_rank_gap(connection, module_id=int(current["module_id"]), exclude_question_id=question_id)
        _shift_ranks_for_insert(connection, module_id=payload.module_id, insert_rank=target_rank)
    else:
        _remove_rank_gap(connection, module_id=payload.module_id, exclude_question_id=question_id)
        _shift_ranks_for_insert(
            connection,
            module_id=payload.module_id,
            insert_rank=target_rank,
            exclude_question_id=question_id,
        )

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
            target_rank,
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
    limit_per_question: int = 10,
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

    grouped: dict[int, dict[str, dict[str, Any]]] = {}
    for row in rows:
        answer_values = json.loads(row["submitted_answer_json"])
        answer_text = " | ".join(value.strip() for value in answer_values if value and value.strip()) or "No answer recorded"
        bucket = grouped.setdefault(row["question_id"], {})
        entry = bucket.setdefault(
            answer_text,
            {
                "answer_text": answer_text,
                "count": 0,
                "latest_answered_at": row["answered_at"],
            },
        )
        entry["count"] += 1
        if row["answered_at"] > entry["latest_answered_at"]:
            entry["latest_answered_at"] = row["answered_at"]

    summarized: dict[int, list[dict[str, Any]]] = {}
    for question_id, answers in grouped.items():
        summarized[question_id] = sorted(
            answers.values(),
            key=lambda value: (
                -value["count"],
                -parse_iso_timestamp(value["latest_answered_at"]).timestamp(),
                value["answer_text"],
            ),
        )[:limit_per_question]
    return summarized


def _logical_bucket_label(
    *,
    bucket: str,
    interval_step: Optional[int],
    bucket_origin_step: Optional[int],
    review_flag: bool,
) -> str:
    if review_flag:
        return "review"
    if bucket == "unseen":
        return "unseen"
    if bucket == "mastery":
        return "mastery"
    step = interval_step
    if bucket in {"hot0", "hot1", "hot1_sit_out"} and bucket_origin_step is not None:
        step = bucket_origin_step
    if step is None:
        return "unseen"
    return SCHEDULE_INTERVALS[step][0]


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

    hot0: list[dict[str, Any]] = []
    hot1: list[dict[str, Any]] = []
    due_review: list[dict[str, Any]] = []
    unseen: list[dict[str, Any]] = []
    _ = now

    for candidate in candidates:
        bucket = candidate["bucket"]
        if bucket == "hot0":
            hot0.append(candidate)
        elif bucket == "hot1":
            hot1.append(candidate)
        elif bucket == "due_review":
            due_review.append(candidate)
        elif bucket == "unseen":
            unseen.append(candidate)

    hot0.sort(
        key=lambda row: (
            0 if row.get("last_session_id") == row.get("latest_scored_session_id") else 1,
            _iso_timestamp_sort_value(row.get("last_incorrect_at"), descending=True),
            row.get("recovery_streak", 0),
            row["rank"],
            row["question_id"],
        )
    )
    hot1.sort(
        key=lambda row: (
            _iso_timestamp_sort_value(row.get("last_incorrect_at"), descending=True),
            row["rank"],
            row["question_id"],
        )
    )
    due_review.sort(
        key=lambda row: (
            row.get("interval_step") if row.get("interval_step") is not None else len(SCHEDULE_INTERVALS),
            0 if row.get("retry_pending") else 1,
            _iso_timestamp_sort_value(row.get("next_due_at")),
            row["rank"],
            row["question_id"],
        )
    )
    unseen.sort(key=lambda row: (row["rank"], row["question_id"]))

    selected: list[dict[str, Any]] = []
    for bucket in (hot0, hot1, due_review, unseen):
        remaining = count - len(selected)
        if remaining <= 0:
            break
        selected.extend(bucket[:remaining])

    return selected


def _eligible_quiz_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [candidate for candidate in candidates if not candidate.get("review_flag", False)]


def _randomize_quiz_order(rows: list[dict[str, Any]], *, rng: Optional[random.Random] = None) -> list[dict[str, Any]]:
    shuffled = list(rows)
    (rng or random).shuffle(shuffled)
    return shuffled


def create_quiz_session(
    connection: DatabaseConnection,
    *,
    user_id: int,
    module_id: Optional[int],
    count: int,
    rng: Optional[random.Random] = None,
) -> dict[str, Any]:
    ensure_user_exists(connection, user_id)
    scope_module_ids = get_scope_module_ids(connection, module_id)
    placeholders = ",".join("?" for _ in scope_module_ids) or "NULL"
    candidate_rows = connection.execute(
        f"""
        SELECT
            q.id AS question_id,
            q.module_id,
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
    latest_scored_session_id = _latest_scored_session_id(connection, user_id=user_id)
    now = utc_now()
    scheduled_candidates: list[dict[str, Any]] = []
    for row in candidate_rows:
        stats = stats_by_question.get(
            row["question_id"],
            {"attempts_count": 0, "correct_count": 0.0, "incorrect_count": 0.0, "last_asked_at": None},
        )
        schedule = _schedule_snapshot_from_attempts(
            history_by_question.get(row["question_id"], []),
            now=now,
            latest_scored_session_id=latest_scored_session_id,
        )
        scheduled_candidates.append(
            {
                **dict(row),
                **stats,
                **schedule,
                "latest_scored_session_id": latest_scored_session_id,
                "review_flag": review_flags.get(row["question_id"], False),
            }
        )

    eligible_candidates = _eligible_quiz_candidates(scheduled_candidates)
    if scheduled_candidates and not eligible_candidates:
        raise ValidationError("All questions in this scope are currently flagged for review.")

    chosen_rows = _bucketed_question_selection(
        eligible_candidates,
        count=min(count, len(eligible_candidates)),
        now=now,
    )
    chosen_rows = _randomize_quiz_order(chosen_rows, rng=rng)
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
        resolved_prompt, resolved_type_config = _resolved_runtime(
            row["question_type"],
            row["prompt"],
            type_config,
            rng=rng,
        )
        connection.execute(
            """
            INSERT INTO quiz_session_items (
                session_id,
                question_id,
                score_earned,
                score_possible,
                resolved_prompt,
                resolved_type_config_json
            )
            VALUES (?, ?, NULL, ?, ?, ?)
            """,
            (
                session_id,
                row["question_id"],
                score_possible(resolved_type_config),
                resolved_prompt,
                json_dumps(resolved_type_config),
            ),
        )
        items.append(
            {
                "id": row["question_id"],
                "position": index,
                "question_id": row["question_id"],
                "module_id": row["module_id"],
                "module_instruction": row["module_instruction"] or "",
                "review_flag": bool(row["review_flag"]),
                "prompt": resolved_prompt,
                "question_type": row["question_type"],
                "rank": row["rank"],
                "type_config": public_type_config(row["question_type"], resolved_type_config),
                "submitted_answer": None,
                "is_correct": None,
                "score_earned": None,
                "score_possible": score_possible(resolved_type_config),
            }
        )

    return {
        "id": session_id,
        "module_id": module_id,
        "completed_at": None,
        "items": items,
    }


def _unordered_multi_alignment(expected_groups: list[list[str]], normalized_inputs: list[str]) -> list[Optional[int]]:
    normalized_expected_groups = [{normalize_text(answer) for answer in group} for group in expected_groups]
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
    normalized_inputs = [normalize_text(answer) for answer in answers]
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
        expected_normalized = {normalize_text(answer) for answer in expected_group}
        is_correct = submitted in expected_normalized
        slot_results.append({"index": index, "is_correct": is_correct, "expected": " / ".join(expected_group)})
        all_correct = all_correct and is_correct
        if is_correct:
            correct_slots += 1

    earned_score = correct_slots / slot_total
    if question_type in {"single_text", "computed_text"} and len(expected_groups) == 1:
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
            qsi.resolved_type_config_json,
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

    type_config = json.loads(row["resolved_type_config_json"] or row["type_config_json"])
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
    latest_scored_session_id = _latest_scored_session_id(connection, user_id=user_id)
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
        schedule = _schedule_snapshot_from_attempts(
            history_by_question.get(row["question_id"], []),
            now=now,
            latest_scored_session_id=latest_scored_session_id,
        )
        type_config = json.loads(row["type_config_json"])
        denominator = stats["correct_count"] + stats["incorrect_count"]
        questions.append(
            {
                "question_id": row["question_id"],
                "module_id": row["module_id"],
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
                "segments": type_config.get("segments", []),
                "recent_incorrect_answers": recent_incorrect_answers.get(row["question_id"], []),
                "schedule": {
                    "bucket": schedule["bucket"],
                    "logical_bucket": _logical_bucket_label(
                        bucket=schedule["bucket"],
                        interval_step=schedule["interval_step"],
                        bucket_origin_step=schedule.get("bucket_origin_step"),
                        review_flag=review_flag,
                    ),
                    "recovery_streak": schedule["recovery_streak"],
                    "interval_step": schedule["interval_step"],
                    "last_incorrect_at": schedule["last_incorrect_at"],
                    "next_due_at": schedule["next_due_at"],
                    "retry_pending": schedule["retry_pending"],
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


def _existing_prompt_keys(connection: DatabaseConnection, module_id: int) -> set[str]:
    existing_rows = _module_question_rows(connection, module_id)
    return {
        question_prompt_key(row["question_type"], row["prompt"], json.loads(row["type_config_json"]))
        for row in existing_rows
    }


def _report_text(
    unresolved_rows: list[dict[str, Any]],
    *,
    valid_row_count: int,
    skipped_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.extend(
        f"row {row['row_number']} | needs fix | {'; '.join(row['issues'])} | {row['qml_line']}"
        for row in unresolved_rows
    )
    lines.extend(
        f"row {row['row_number']} | skipped duplicate | {row['reason']} | {row['qml_line']}"
        for row in skipped_rows
    )

    if lines:
        return "\n".join(lines)
    if valid_row_count:
        return "All remaining rows are valid. Commit to save them."
    return "No importable rows remain."


def _classify_import_rows(
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
        ordered_rows = sorted(rows, key=lambda row: row["row_number"])
        if key in existing_keys:
            for row in ordered_rows:
                row["skip_reason"] = "Prompt already exists in this leaf module."
            continue
        if len(ordered_rows) > 1:
            for row in ordered_rows[1:]:
                row["skip_reason"] = "Prompt duplicates an earlier row in this upload."
    return parsed_rows


def _normalize_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise ValidationError("Import must include at least one question row.")

    normalized_rows: list[dict[str, Any]] = []
    seen_row_numbers: set[int] = set()
    for row in sorted(rows, key=lambda candidate: candidate["row_number"]):
        row_number = int(row["row_number"])
        qml_line = row["qml_line"]
        if row_number in seen_row_numbers:
            raise ValidationError("Row numbers must be unique.")
        if "\n" in qml_line or "\r" in qml_line:
            raise ValidationError("Each QML row must stay on one line.")
        seen_row_numbers.add(row_number)
        normalized_rows.append({"row_number": row_number, "qml_line": qml_line})
    return normalized_rows


def _validate_question_import_rows(
    connection: DatabaseConnection,
    *,
    module_id: int,
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ensure_leaf_module(connection, module_id)

    parsed_rows: list[dict[str, Any]] = []
    for row in _normalize_import_rows(rows):
        row_number = row["row_number"]
        qml_line = row["qml_line"]
        issues: list[str] = []
        inferred_type: Optional[str] = None
        payload: Optional[dict[str, Any]] = None
        try:
            payload = parse_qml_line(line=qml_line, module_id=module_id, rank=row_number)
            draft = QuestionDraftIn(**payload)
            inferred_type = draft.question_type
            payload = draft.model_dump()
        except (QMLError, ValueError) as error:
            issues.append(str(error))
        parsed_rows.append(
            {
                "row_number": row_number,
                "qml_line": qml_line,
                "inferred_type": inferred_type,
                "payload": payload,
                "issues": issues,
            }
        )

    parsed_rows = _classify_import_rows(connection, module_id=module_id, parsed_rows=parsed_rows)
    unresolved_rows = [
        {
            "row_number": row["row_number"],
            "qml_line": row["qml_line"],
            "issues": row["issues"],
            "inferred_type": row["inferred_type"],
        }
        for row in parsed_rows
        if row["issues"]
    ]
    skipped_rows = [
        {
            "row_number": row["row_number"],
            "qml_line": row["qml_line"],
            "reason": row["skip_reason"],
            "inferred_type": row["inferred_type"],
        }
        for row in parsed_rows
        if row.get("skip_reason")
    ]
    valid_rows = [row for row in parsed_rows if not row["issues"] and not row.get("skip_reason") and row["payload"]]
    result = {
        "ready_to_commit": bool(not unresolved_rows and valid_rows),
        "valid_row_count": len(valid_rows),
        "skipped_duplicate_count": len(skipped_rows),
        "skipped_rows": skipped_rows,
        "unresolved_rows": unresolved_rows,
        "report_text": _report_text(
            unresolved_rows,
            valid_row_count=len(valid_rows),
            skipped_rows=skipped_rows,
        ),
        "committed": False,
        "committed_count": 0,
    }
    return result, valid_rows


def validate_question_import(
    connection: DatabaseConnection,
    *,
    module_id: int,
    qml_text: Optional[str] = None,
    rows: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    try:
        normalized_rows = qml_lines_from_text(qml_text) if qml_text is not None else _normalize_import_rows(rows or [])
    except QMLError as error:
        raise ValidationError(str(error)) from error
    result, _ = _validate_question_import_rows(connection, module_id=module_id, rows=normalized_rows)
    return result


def commit_question_import(
    connection: DatabaseConnection,
    *,
    module_id: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    result, valid_rows = _validate_question_import_rows(connection, module_id=module_id, rows=rows)
    if result["unresolved_rows"]:
        return result

    committed_count = 0
    for row in valid_rows:
        payload = QuestionDraftIn(**row["payload"])
        create_question(connection, payload)
        committed_count += 1

    return {
        **result,
        "committed": True,
        "committed_count": committed_count,
    }


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
        """
        SELECT q.id, m.full_slug, q.prompt, q.question_type, q.type_config_json
        FROM questions AS q
        JOIN modules AS m ON m.id = q.module_id
        """
    ).fetchall()
    for row in rows:
        type_config = json.loads(row["type_config_json"])
        changed = False
        question_type = row["question_type"]

        if question_type == "multi_text" and type_config.get("answer_order_matters") is True:
            question_type = "ordered_multi"
            changed = True
        if (
            row["question_type"] != "inline_cloze"
            and (row["full_slug"], normalize_text(row["prompt"])) in FORCED_UNORDERED_PROMPTS
            and question_type != "multi_text"
        ):
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


def _read_seed_module_instruction(module_file: Path) -> str:
    lines = module_file.read_text().splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("instruction:"):
            continue

        raw_value = line.partition(":")[2].strip()
        if not raw_value:
            return ""
        if raw_value in {"|", ">"}:
            block_lines: list[str] = []
            for block_line in lines[index + 1 :]:
                if not block_line.startswith(("  ", "\t")):
                    break
                block_lines.append(block_line.strip())
            return "\n".join(block_lines).strip()
        return raw_value.strip().strip("\"'")
    return ""


def sync_seed_content(connection: DatabaseConnection, content_root: Path) -> dict[str, int]:
    content_root = Path(content_root)
    imported_modules = 0
    imported_questions = 0
    module_files = sorted(content_root.rglob("module.yaml"), key=lambda path: (len(path.relative_to(content_root).parts), str(path)))

    module_lookup = {
        row["full_slug"]: row["id"]
        for row in connection.execute("SELECT id, full_slug FROM modules").fetchall()
    }
    for module_file in module_files:
        relative_parts = module_file.parent.relative_to(content_root).parts
        slug = relative_parts[-1]
        full_slug = "/".join(relative_parts)
        if full_slug in module_lookup:
            continue

        parent_full_slug = "/".join(relative_parts[:-1]) if len(relative_parts) > 1 else None
        parent_id = None
        if parent_full_slug:
            parent_id = module_lookup.get(parent_full_slug)
            if parent_id is None:
                raise ValidationError(f"Parent module {parent_full_slug} must be imported before child {full_slug}.")
            ensure_module_can_accept_children(connection, parent_id)
        ensure_unique_module_slug(connection, slug, parent_id)
        module_id = execute_insert_returning_id(
            connection,
            """
            INSERT INTO modules (parent_id, slug, full_slug, instruction, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (parent_id, slug, full_slug, _read_seed_module_instruction(module_file), utc_now()),
        )
        module_lookup[full_slug] = module_id
        imported_modules += 1

    question_files = sorted(content_root.rglob("questions.dsl"))
    for question_file in question_files:
        module_full_slug = str(question_file.parent.relative_to(content_root)).replace("\\", "/")
        module_id = module_lookup[module_full_slug]
        existing_prompt_keys = _existing_prompt_keys(connection, module_id)
        for row in qml_lines_from_text(question_file.read_text()):
            payload = QuestionDraftIn(**parse_qml_line(line=row["qml_line"], module_id=module_id, rank=row["row_number"]))
            type_config = serialize_type_config(payload)
            prompt_key = question_prompt_key(payload.question_type, payload.prompt, type_config)
            if prompt_key in existing_prompt_keys:
                continue
            create_question(connection, payload)
            existing_prompt_keys.add(prompt_key)
            imported_questions += 1

    backfill_question_type_defaults(connection)
    backfill_session_scores(connection)
    return {"modules": imported_modules, "questions": imported_questions}
