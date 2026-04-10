import json
from typing import Any

from ..database import DatabaseConnection, utc_now
from .catalog import ensure_user_exists, get_scope_module_ids
from .common import preview_prompt
from .schedule import (
    _iso_timestamp_sort_value,
    _latest_scored_session_id,
    _logical_bucket_label,
    _question_attempt_history,
    _question_stats_by_question,
    _recent_incorrect_answers_by_question,
    _review_flags_by_question,
    _schedule_snapshot_from_attempts,
)


def get_stats(
    connection: DatabaseConnection,
    *,
    user_id: int,
    module_id: int | None,
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
