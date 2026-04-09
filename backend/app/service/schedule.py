from __future__ import annotations

import json
import random
from typing import Any, Optional

from ..config import FULL_CREDIT_TOLERANCE, SCHEDULE_INTERVALS
from ..database import DatabaseConnection
from .common import add_interval_to_timestamp, is_full_credit, normalize_text, parse_iso_timestamp


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
