from typing import Any

from ..database import DatabaseConnection, utc_now
from ..settings import schedule_timezone_name
from .auth import Actor
from .catalog import ensure_user_exists, get_scope_module_ids
from .errors import NotFoundError
from .questions import preview_prompt
from .schedule import (
    _iso_timestamp_sort_value,
    _latest_scored_session_id,
    _logical_bucket_label,
    _question_attempt_history,
    _question_stats_by_question,
    _recent_incorrect_answers_by_question,
    _schedule_snapshot_from_attempts,
)
from .visibility import get_effective_question_row, list_effective_question_rows
from .moderation import list_pending_revision_proposals


def _default_question_stats() -> dict[str, Any]:
    return {
        "attempts_count": 0,
        "correct_count": 0.0,
        "incorrect_count": 0.0,
        "first_asked_at": None,
        "last_asked_at": None,
    }


def _question_payload(
    row: dict[str, Any],
    *,
    stats: dict[str, Any],
    history: list[dict[str, Any]],
    latest_scored_session_id: int | None,
    recent_incorrect_answers: list[dict[str, Any]],
    now: str,
) -> dict[str, Any]:
    type_config = row["type_config"]
    denominator = stats["correct_count"] + stats["incorrect_count"]
    schedule = _schedule_snapshot_from_attempts(
        history,
        now=now,
        latest_scored_session_id=latest_scored_session_id,
    )
    return {
        "question_id": row["question_id"],
        "module_id": row["module_id"],
        "module_full_slug": row["module_full_slug"],
        "prompt": row["prompt"],
        "prompt_preview": preview_prompt(row["prompt"], row["question_type"], type_config),
        "question_type": row["question_type"],
        "rank": row["rank"],
        "attempts": stats["attempts_count"],
        "correct_percentage": (stats["correct_count"] / denominator) if denominator else 0.0,
        "first_asked_at": stats["first_asked_at"],
        "last_asked_at": stats["last_asked_at"],
        "admin_verified": bool(row["admin_verified"]),
        "moderation_status": row["moderation_status"],
        "created_by_user_id": row["created_by_user_id"],
        "creator_display_name": row["creator_display_name"],
        "accepted_answers": type_config.get("accepted_answers", []),
        "segments": type_config.get("segments", []),
        "bundle_qml": row.get("bundle_qml"),
        "recent_incorrect_answers": recent_incorrect_answers,
        "schedule": {
            "bucket": schedule["bucket"],
            "logical_bucket": _logical_bucket_label(
                bucket=schedule["bucket"],
                interval_step=schedule["interval_step"],
                bucket_origin_step=schedule.get("bucket_origin_step"),
            ),
            "recovery_streak": schedule["recovery_streak"],
            "interval_step": schedule["interval_step"],
            "last_incorrect_at": schedule["last_incorrect_at"],
            "next_due_at": schedule["next_due_at"],
        },
    }


def get_question(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_id: int,
    actor: Actor | None = None,
) -> dict[str, Any]:
    ensure_user_exists(connection, user_id)
    row = get_effective_question_row(connection, actor=actor, question_id=question_id)
    if row is None:
        raise NotFoundError(f"Question {question_id} was not found.")

    question_ids = [question_id]
    stats_by_question = _question_stats_by_question(connection, user_id=user_id, question_ids=question_ids)
    history_by_question = _question_attempt_history(connection, user_id=user_id, question_ids=question_ids)
    recent_incorrect_answers = _recent_incorrect_answers_by_question(
        connection,
        user_id=user_id,
        question_ids=question_ids,
    )
    return _question_payload(
        row,
        stats=stats_by_question.get(question_id, _default_question_stats()),
        history=history_by_question.get(question_id, []),
        latest_scored_session_id=_latest_scored_session_id(connection, user_id=user_id),
        recent_incorrect_answers=recent_incorrect_answers.get(question_id, []),
        now=utc_now(),
    )


def get_stats(
    connection: DatabaseConnection,
    *,
    user_id: int,
    module_id: int | None,
    review_only: bool,
    actor: Actor | None = None,
) -> dict[str, Any]:
    ensure_user_exists(connection, user_id)
    scope_ids = get_scope_module_ids(connection, module_id, actor=actor)
    question_rows = list_effective_question_rows(connection, actor=actor, scope_module_ids=scope_ids)

    question_ids = [row["question_id"] for row in question_rows]
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
        if review_only:
            continue

        questions.append(
            _question_payload(
                row,
                stats=stats_by_question.get(row["question_id"], _default_question_stats()),
                history=history_by_question.get(row["question_id"], []),
                latest_scored_session_id=latest_scored_session_id,
                recent_incorrect_answers=recent_incorrect_answers.get(row["question_id"], []),
                now=now,
            )
        )

    questions.sort(
        key=lambda row: (
            row["last_asked_at"] is None,
            _iso_timestamp_sort_value(row["last_asked_at"], descending=True),
            row["rank"],
            row["question_id"],
        )
    )

    total_questions = len(question_rows)
    revision_proposals = list_pending_revision_proposals(connection, actor=actor, scope_module_ids=scope_ids)
    reviewed_questions = len(revision_proposals)
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
                COUNT(attempts.id) AS answered_count,
                COALESCE(SUM(attempts.score_earned), 0) AS correct_count,
                COALESCE(SUM(attempts.score_possible), 0) AS score_possible
            FROM quiz_sessions AS qs
            JOIN attempts ON attempts.session_id = qs.id
            WHERE {session_scope_filter}
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
        "schedule_timezone": schedule_timezone_name(),
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
        "revision_proposals": revision_proposals,
    }
