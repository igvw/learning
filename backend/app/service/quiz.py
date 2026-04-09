from __future__ import annotations

import json
import random
from typing import Any, Optional

from ..database import DatabaseConnection, execute_insert_returning_id, utc_now
from .catalog import ensure_user_exists, get_scope_module_ids
from .common import (
    NotFoundError,
    ValidationError,
    canonical_answers,
    json_dumps,
    normalize_text,
    public_type_config,
    resolved_runtime,
    score_possible,
)
from .schedule import (
    _bucketed_question_selection,
    _eligible_quiz_candidates,
    _latest_scored_session_id,
    _question_attempt_history,
    _question_stats_by_question,
    _randomize_quiz_order,
    _review_flags_by_question,
    _schedule_snapshot_from_attempts,
)


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
        resolved_prompt, resolved_type_config = resolved_runtime(
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
    is_correct, earned_score, possible_score_value, slot_results = evaluate_answers(row["question_type"], type_config, answers)
    answered_at = utc_now()
    connection.execute(
        """
        UPDATE quiz_session_items
        SET score_earned = ?, score_possible = ?, submitted_answer_json = ?
        WHERE session_id = ? AND question_id = ?
        """,
        (earned_score, possible_score_value, json_dumps(answers), session_id, item_id),
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
        "score_possible": possible_score_value,
        "slot_results": slot_results,
        "canonical_answers": canonical_answers(type_config),
        "session_completed": session_completed,
        "submitted_answer": answers,
    }
