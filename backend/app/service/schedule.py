import json
import random
from typing import Any

from ..config import FULL_CREDIT_TOLERANCE, SCHEDULE_INTERVALS
from ..database import DatabaseConnection
from ..settings import schedule_timezone
from .time_utils import is_full_credit, parse_iso_timestamp, schedule_due_at


def _review_flags_by_question(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_ids: list[int] | None = None,
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
    question_ids: list[int] | None = None,
) -> dict[int, list[dict[str, Any]]]:
    if question_ids is not None and not question_ids:
        return {}

    where_sql = "WHERE attempts.user_id = ?"
    params: list[Any] = [user_id]
    if question_ids is not None:
        placeholders = ",".join("?" for _ in question_ids)
        where_sql += f" AND attempts.legacy_question_id IN ({placeholders})"
        params.extend(question_ids)

    rows = connection.execute(
        f"""
        SELECT
            attempts.legacy_question_id AS question_id,
            attempts.score_earned,
            attempts.score_possible,
            attempts.answered_at,
            attempts.session_id
        FROM attempts
        {where_sql}
        ORDER BY attempts.legacy_question_id ASC, attempts.answered_at ASC, attempts.session_id ASC
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


def _latest_scored_session_id(connection: DatabaseConnection, *, user_id: int) -> int | None:
    row = connection.execute(
        """
        SELECT session_id AS id
        FROM attempts
        WHERE user_id = ?
        GROUP BY session_id, answered_at
        ORDER BY answered_at DESC, session_id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return int(row["id"]) if row is not None else None


def _bucket_step_after_hot_recovery(origin_step: int | None, failures_after_bucket_retry: int) -> int:
    if origin_step is None:
        return 0
    if failures_after_bucket_retry > 1:
        return max(origin_step - 1, 0)
    return origin_step


def _derive_schedule_state_from_attempts(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    app_schedule_timezone = schedule_timezone()
    state: dict[str, Any] = {
        "bucket": "unseen",
        "recovery_streak": None,
        "recovery_origin": None,
        "interval_step": None,
        "last_incorrect_at": None,
        "next_due_at": None,
        "last_answered_at": None,
        "last_session_id": None,
        "bucket_origin_step": None,
        "recovery_wrong_count": 0,
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
                        "recovery_origin": None,
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
                        "recovery_origin": "unseen",
                        "interval_step": None,
                        "last_incorrect_at": answered_at,
                        "next_due_at": None,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "bucket_origin_step": None,
                        "recovery_wrong_count": 0,
                    }
                )
            continue

        if bucket == "mastery":
            if is_correct:
                state.update({"last_answered_at": answered_at, "last_session_id": session_id, "recovery_origin": None})
            else:
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "recovery_origin": "mastery",
                        "interval_step": None,
                        "last_incorrect_at": answered_at,
                        "next_due_at": None,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "bucket_origin_step": None,
                        "recovery_wrong_count": 0,
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
                            "recovery_origin": None,
                            "interval_step": None,
                            "last_answered_at": answered_at,
                            "last_session_id": session_id,
                            "next_due_at": None,
                            "bucket_origin_step": None,
                            "recovery_wrong_count": 0,
                        }
                    )
                else:
                    next_step = current_step + 1
                    state.update(
                        {
                            "bucket": "cooling",
                            "recovery_streak": None,
                            "recovery_origin": None,
                            "interval_step": next_step,
                            "last_answered_at": answered_at,
                            "last_session_id": session_id,
                            "next_due_at": schedule_due_at(
                                answered_at,
                                SCHEDULE_INTERVALS[next_step][1],
                                timezone=app_schedule_timezone,
                            ),
                            "bucket_origin_step": None,
                            "recovery_wrong_count": 0,
                        }
                    )
            else:
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "recovery_origin": "bucket",
                        "interval_step": None,
                        "last_incorrect_at": answered_at,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "next_due_at": None,
                        "bucket_origin_step": current_step,
                        "recovery_wrong_count": 1,
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
                wrong_count = state["recovery_wrong_count"]
                if state["bucket_origin_step"] is not None and state["recovery_origin"] == "bucket":
                    wrong_count += 1
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "last_incorrect_at": answered_at,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "recovery_wrong_count": wrong_count,
                    }
                )
            continue

        if bucket == "hot1":
            if is_correct:
                resolved_step = _bucket_step_after_hot_recovery(
                    state["bucket_origin_step"],
                    int(state["recovery_wrong_count"] or 0),
                )
                state.update(
                    {
                        "bucket": "cooling",
                        "recovery_streak": 2,
                        "recovery_origin": None,
                        "interval_step": resolved_step,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "next_due_at": schedule_due_at(
                            answered_at,
                            SCHEDULE_INTERVALS[resolved_step][1],
                            timezone=app_schedule_timezone,
                        ),
                        "bucket_origin_step": None,
                        "recovery_wrong_count": 0,
                    }
                )
            else:
                wrong_count = state["recovery_wrong_count"]
                if state["bucket_origin_step"] is not None and state["recovery_origin"] == "bucket":
                    wrong_count += 1
                state.update(
                    {
                        "bucket": "hot0",
                        "recovery_streak": 0,
                        "last_incorrect_at": answered_at,
                        "last_answered_at": answered_at,
                        "last_session_id": session_id,
                        "next_due_at": None,
                        "recovery_wrong_count": wrong_count,
                    }
                )
            continue

    return state


def _schedule_snapshot_from_attempts(
    attempts: list[dict[str, Any]],
    *,
    now: str,
    latest_scored_session_id: int | None = None,
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
    bucket = state["bucket"]
    if bucket == "hot1" and latest_scored_session_id is not None and state.get("last_session_id") == latest_scored_session_id:
        bucket = "hot1_sit_out"
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
        "last_session_id": state.get("last_session_id"),
    }


def _question_stats_by_question(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_ids: list[int] | None = None,
) -> dict[int, dict[str, Any]]:
    if question_ids is not None and not question_ids:
        return {}

    where_sql = "WHERE attempts.user_id = ?"
    params: list[Any] = [user_id]
    if question_ids is not None:
        placeholders = ",".join("?" for _ in question_ids)
        where_sql += f" AND attempts.legacy_question_id IN ({placeholders})"
        params.extend(question_ids)

    rows = connection.execute(
        f"""
        SELECT
            attempts.legacy_question_id AS question_id,
            COUNT(*) AS attempts_count,
            COALESCE(SUM(attempts.score_earned), 0) AS correct_count,
            COALESCE(SUM(attempts.score_possible - attempts.score_earned), 0) AS incorrect_count,
            MIN(attempts.answered_at) AS first_asked_at,
            MAX(attempts.answered_at) AS last_asked_at
        FROM attempts
        {where_sql}
        GROUP BY attempts.legacy_question_id
        """,
        tuple(params),
    ).fetchall()
    return {
        row["question_id"]: {
            "attempts_count": row["attempts_count"],
            "correct_count": row["correct_count"],
            "incorrect_count": row["incorrect_count"],
            "first_asked_at": row["first_asked_at"],
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
            attempts.legacy_question_id AS question_id,
            attempts.submitted_answer_json,
            attempts.answered_at
        FROM attempts
        WHERE attempts.user_id = ?
          AND attempts.legacy_question_id IN ({placeholders})
          AND attempts.score_earned + ? < attempts.score_possible
          AND attempts.submitted_answer_json IS NOT NULL
        ORDER BY attempts.answered_at DESC, attempts.session_id DESC
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
    interval_step: int | None,
    bucket_origin_step: int | None,
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


def _iso_timestamp_sort_value(value: str | None, *, descending: bool = False) -> float:
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


def _randomize_quiz_order(rows: list[dict[str, Any]], *, rng: random.Random | None = None) -> list[dict[str, Any]]:
    shuffled = list(rows)
    (rng or random).shuffle(shuffled)
    return shuffled
