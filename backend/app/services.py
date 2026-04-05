from __future__ import annotations

import csv
import json
import random
import re
import sqlite3
from pathlib import Path
from typing import Any, Optional

import yaml

from .database import utc_now
from .schemas import ModuleUiCopy, QuestionDraftIn


class ServiceError(Exception):
    status_code = 400


class NotFoundError(ServiceError):
    status_code = 404


class ValidationError(ServiceError):
    status_code = 400


DEFAULT_UI_COPY = ModuleUiCopy().model_dump()
FORCED_UNORDERED_SOURCE_IDS = {"geography-rivers-002", "geography-rivers-005"}


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return slug or "module"


def normalize_answer(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


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
        rendered = "[_]".join(type_config.get("segments", []))
        return rendered if len(rendered) <= 120 else f"{rendered[:117]}..."
    return prompt if len(prompt) <= 120 else f"{prompt[:117]}..."


def ensure_module_exists(connection: sqlite3.Connection, module_id: Optional[int]) -> Optional[sqlite3.Row]:
    if module_id is None:
        return None
    row = connection.execute(
        "SELECT id, title, full_slug FROM modules WHERE id = ?",
        (module_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Module {module_id} was not found.")
    return row


def next_unique_slug(connection: sqlite3.Connection, title: str, parent_id: Optional[int]) -> tuple[str, str]:
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


def create_module(
    connection: sqlite3.Connection,
    *,
    title: str,
    parent_id: Optional[int],
    ui_copy: dict[str, Any],
) -> dict[str, Any]:
    if parent_id is not None:
        ensure_module_exists(connection, parent_id)
    slug, full_slug = next_unique_slug(connection, title, parent_id)
    cursor = connection.execute(
        """
        INSERT INTO modules (source_id, parent_id, title, slug, full_slug, ui_copy_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (None, parent_id, title.strip(), slug, full_slug, json_dumps(merge_ui_copy(ui_copy)), utc_now()),
    )
    return {
        "id": cursor.lastrowid,
        "title": title.strip(),
        "slug": slug,
        "full_slug": full_slug,
        "ui_copy": merge_ui_copy(ui_copy),
    }


def get_module_tree(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, source_id, parent_id, title, slug, full_slug, ui_copy_json
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


def get_scope_module_ids(connection: sqlite3.Connection, module_id: Optional[int]) -> list[int]:
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


def _candidate_weight(row: sqlite3.Row | dict[str, Any]) -> float:
    ranking = max(float(row["ranking"]), 1.0)
    attempts = row["attempts_count"]
    correct = row["correct_count"]
    incorrect = row["incorrect_count"]
    if attempts == 0:
        return ranking * 2
    return ranking * ((1 + incorrect) / (1 + correct))


def weighted_sample_without_replacement(
    candidates: list[sqlite3.Row | dict[str, Any]],
    count: int,
    *,
    rng: Optional[random.Random] = None,
) -> list[sqlite3.Row | dict[str, Any]]:
    if count <= 0 or not candidates:
        return []

    generator = rng or random.Random()
    pool = list(candidates)
    chosen: list[sqlite3.Row | dict[str, Any]] = []
    while pool and len(chosen) < count:
        total_weight = sum(_candidate_weight(row) for row in pool)
        needle = generator.random() * total_weight
        running_weight = 0.0
        chosen_index = 0
        for index, row in enumerate(pool):
            running_weight += _candidate_weight(row)
            if running_weight >= needle:
                chosen_index = index
                break
        chosen.append(pool.pop(chosen_index))
    return chosen


def create_question(connection: sqlite3.Connection, payload: QuestionDraftIn) -> dict[str, int]:
    ensure_module_exists(connection, payload.module_id)
    cursor = connection.execute(
        """
        INSERT INTO questions (source_id, module_id, review_flag, question_type, prompt, ranking, type_config_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            None,
            payload.module_id,
            int(payload.review_flag),
            payload.question_type,
            payload.prompt.strip(),
            float(payload.ranking),
            json_dumps(serialize_type_config(payload)),
        ),
    )
    return {"question_id": cursor.lastrowid}


def revise_question(connection: sqlite3.Connection, question_id: int, payload: QuestionDraftIn, *, reset_stats: bool) -> dict[str, int]:
    current = connection.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone()
    if current is None:
        raise NotFoundError(f"Question {question_id} was not found.")

    ensure_module_exists(connection, payload.module_id)
    if reset_stats:
        connection.execute("DELETE FROM quiz_session_items WHERE question_id = ?", (question_id,))

    connection.execute(
        """
        UPDATE questions
        SET
            module_id = ?,
            review_flag = ?,
            question_type = ?,
            prompt = ?,
            ranking = ?,
            type_config_json = ?
        WHERE id = ?
        """,
        (
            payload.module_id,
            int(payload.review_flag),
            payload.question_type,
            payload.prompt.strip(),
            float(payload.ranking),
            json_dumps(serialize_type_config(payload)),
            question_id,
        ),
    )
    return {"question_id": question_id}


def set_question_review_flag(connection: sqlite3.Connection, question_id: int, review_flag: bool) -> dict[str, Any]:
    row = connection.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Question {question_id} was not found.")
    connection.execute(
        "UPDATE questions SET review_flag = ? WHERE id = ?",
        (int(review_flag), question_id),
    )
    return {"question_id": question_id, "review_flag": review_flag}


def _question_stats_by_question(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            qsi.question_id,
            COUNT(*) AS attempts_count,
            COALESCE(SUM(qsi.score_earned), 0) AS correct_count,
            COALESCE(SUM(qsi.score_possible - qsi.score_earned), 0) AS incorrect_count,
            MAX(COALESCE(qs.completed_at, qs.created_at)) AS last_asked_at
        FROM quiz_session_items AS qsi
        JOIN quiz_sessions AS qs ON qs.id = qsi.session_id
        WHERE qsi.score_earned IS NOT NULL
        GROUP BY qsi.question_id
        """
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


def create_quiz_session(
    connection: sqlite3.Connection,
    *,
    module_id: Optional[int],
    count: int,
    rng: Optional[random.Random] = None,
) -> dict[str, Any]:
    scope_module_ids = get_scope_module_ids(connection, module_id)
    placeholders = ",".join("?" for _ in scope_module_ids) or "NULL"
    stats_by_question = _question_stats_by_question(connection)
    candidate_rows = connection.execute(
        f"""
        SELECT
            q.id AS question_id,
            q.review_flag,
            q.prompt,
            q.question_type,
            q.ranking,
            q.type_config_json
        FROM questions AS q
        WHERE q.module_id IN ({placeholders})
        ORDER BY q.id
        """,
        tuple(scope_module_ids),
    ).fetchall()

    weighted_candidates: list[dict[str, Any]] = []
    for row in candidate_rows:
        stats = stats_by_question.get(
            row["question_id"],
            {"attempts_count": 0, "correct_count": 0.0, "incorrect_count": 0.0, "last_asked_at": None},
        )
        weighted_candidates.append(
            {
                **dict(row),
                **stats,
            }
        )

    chosen_rows = weighted_sample_without_replacement(weighted_candidates, min(count, len(weighted_candidates)), rng=rng)
    cursor = connection.execute(
        """
        INSERT INTO quiz_sessions (module_id, created_at)
        VALUES (?, ?)
        """,
        (module_id, utc_now()),
    )
    session_id = cursor.lastrowid

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
                "review_flag": bool(row["review_flag"]),
                "prompt": row["prompt"],
                "question_type": row["question_type"],
                "ranking": row["ranking"],
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
    connection: sqlite3.Connection,
    *,
    session_id: int,
    item_id: int,
    answers: list[str],
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            qsi.question_id,
            qsi.score_earned,
            qsi.score_possible,
            q.question_type,
            q.type_config_json
        FROM quiz_session_items AS qsi
        JOIN questions AS q ON q.id = qsi.question_id
        WHERE qsi.session_id = ? AND qsi.question_id = ?
        """,
        (session_id, item_id),
    ).fetchone()
    if row is None:
        raise NotFoundError("Quiz session item was not found.")
    if row["score_earned"] is not None:
        raise ValidationError("Quiz session item has already been answered.")

    type_config = json.loads(row["type_config_json"])
    is_correct, earned_score, possible_score, slot_results = evaluate_answers(row["question_type"], type_config, answers)
    connection.execute(
        """
        UPDATE quiz_session_items
        SET score_earned = ?, score_possible = ?
        WHERE session_id = ? AND question_id = ?
        """,
        (earned_score, possible_score, session_id, item_id),
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
            (utc_now(), session_id),
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
    connection: sqlite3.Connection,
    *,
    module_id: Optional[int],
    review_only: bool,
) -> dict[str, Any]:
    scope_ids = get_scope_module_ids(connection, module_id)
    placeholders = ",".join("?" for _ in scope_ids) or "NULL"
    stats_filter_sql = "AND q.review_flag = 1" if review_only else ""

    summary_row = connection.execute(
        f"""
        WITH question_stats AS (
            SELECT
                qsi.question_id,
                COUNT(*) AS attempts_count,
                COALESCE(SUM(qsi.score_earned), 0) AS correct_count,
                COALESCE(SUM(qsi.score_possible - qsi.score_earned), 0) AS incorrect_count
            FROM quiz_session_items AS qsi
            WHERE qsi.score_earned IS NOT NULL
            GROUP BY qsi.question_id
        )
        SELECT
            COUNT(*) AS total_questions,
            SUM(CASE WHEN q.review_flag = 1 THEN 1 ELSE 0 END) AS reviewed_questions,
            COALESCE(SUM(COALESCE(qs.attempts_count, 0)), 0) AS total_attempts,
            COALESCE(SUM(COALESCE(qs.correct_count, 0)), 0) AS total_correct,
            COALESCE(SUM(COALESCE(qs.correct_count, 0) + COALESCE(qs.incorrect_count, 0)), 0) AS total_possible
        FROM questions AS q
        LEFT JOIN question_stats AS qs ON qs.question_id = q.id
        WHERE q.module_id IN ({placeholders})
        """,
        tuple(scope_ids),
    ).fetchone()

    question_rows = connection.execute(
        f"""
        WITH question_stats AS (
            SELECT
                qsi.question_id,
                COUNT(*) AS attempts_count,
                COALESCE(SUM(qsi.score_earned), 0) AS correct_count,
                COALESCE(SUM(qsi.score_possible - qsi.score_earned), 0) AS incorrect_count,
                MAX(COALESCE(qs.completed_at, qs.created_at)) AS last_asked_at
            FROM quiz_session_items AS qsi
            JOIN quiz_sessions AS qs ON qs.id = qsi.session_id
            WHERE qsi.score_earned IS NOT NULL
            GROUP BY qsi.question_id
        )
        SELECT
            q.id AS question_id,
            q.module_id,
            m.title AS module_title,
            q.review_flag,
            q.prompt,
            q.question_type,
            q.ranking,
            q.type_config_json,
            COALESCE(s.attempts_count, 0) AS attempts_count,
            COALESCE(s.correct_count, 0) AS correct_count,
            COALESCE(s.incorrect_count, 0) AS incorrect_count,
            s.last_asked_at
        FROM questions AS q
        JOIN modules AS m ON m.id = q.module_id
        LEFT JOIN question_stats AS s ON s.question_id = q.id
        WHERE q.module_id IN ({placeholders}) {stats_filter_sql}
        ORDER BY q.review_flag DESC, s.last_asked_at IS NULL, s.last_asked_at DESC, q.ranking DESC, q.id DESC
        """,
        tuple(scope_ids),
    ).fetchall()

    questions = []
    for row in question_rows:
        type_config = json.loads(row["type_config_json"])
        denominator = row["correct_count"] + row["incorrect_count"]
        questions.append(
            {
                "question_id": row["question_id"],
                "module_id": row["module_id"],
                "module_title": row["module_title"],
                "prompt": row["prompt"],
                "prompt_preview": preview_prompt(row["prompt"], row["question_type"], type_config),
                "question_type": row["question_type"],
                "ranking": row["ranking"],
                "attempts": row["attempts_count"],
                "correct_percentage": (row["correct_count"] / denominator) if denominator else 0.0,
                "last_asked_at": row["last_asked_at"],
                "review_flag": bool(row["review_flag"]),
                "accepted_answers": type_config["accepted_answers"],
                "slot_prompts": type_config.get("slot_prompts", []),
                "segments": type_config.get("segments", []),
            }
        )

    session_scope_filter = "qs.module_id IS NULL" if module_id is None else "qs.module_id = ?"
    session_scope_params: tuple[Any, ...] = () if module_id is None else (module_id,)
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

    total_possible = summary_row["total_possible"]
    return {
        "summary": {
            "total_questions": summary_row["total_questions"],
            "reviewed_questions": summary_row["reviewed_questions"] or 0,
            "total_attempts": summary_row["total_attempts"],
            "total_correct": summary_row["total_correct"],
            "total_possible": total_possible,
            "accuracy": (summary_row["total_correct"] / total_possible) if total_possible else 0.0,
        },
        "recent_sessions": recent_sessions,
        "questions": questions,
    }


def backfill_session_scores(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE quiz_session_items
        SET score_possible = 1
        WHERE score_possible IS NULL OR score_possible = 0
        """
    )


def backfill_question_type_defaults(connection: sqlite3.Connection) -> None:
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


def sync_seed_content(connection: sqlite3.Connection, content_root: Path) -> dict[str, int]:
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
        title = data["title"]
        ui_copy = merge_ui_copy(data.get("ui_copy"))
        slug, full_slug = next_unique_slug(connection, title, parent_id)
        cursor = connection.execute(
            """
            INSERT INTO modules (source_id, parent_id, title, slug, full_slug, ui_copy_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, parent_id, title, slug, full_slug, json_dumps(ui_copy), utc_now()),
        )
        module_lookup[source_id] = cursor.lastrowid
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
                    ranking=float(raw_row["ranking"]),
                    review_flag=False,
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
