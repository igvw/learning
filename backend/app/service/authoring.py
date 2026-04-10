import json
from pathlib import Path
from typing import Any

from ..config import FORCED_UNORDERED_PROMPTS
from ..database import DatabaseConnection, execute_insert_returning_id, utc_now
from ..qml import parse_qml_line, qml_lines_from_text
from ..schemas import QuestionDraftIn
from .catalog import (
    ensure_leaf_module,
    ensure_module_can_accept_children,
    ensure_unique_module_slug,
    ensure_user_exists,
)
from .common import NotFoundError, ValidationError, json_dumps, normalize_text, question_prompt_key, serialize_type_config
from .schedule import _question_attempt_history


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
    exclude_question_id: int | None = None,
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


def _clamp_insert_rank(
    connection: DatabaseConnection,
    *,
    module_id: int,
    rank: int,
    exclude_question_id: int | None = None,
) -> int:
    rows = [
        row
        for row in _module_question_rank_rows(connection, module_id)
        if exclude_question_id is None or row["id"] != exclude_question_id
    ]
    return max(1, min(int(rank), len(rows) + 1))


def _priority_insert_rank(connection: DatabaseConnection, *, user_id: int | None, module_id: int, priority_mode: str) -> int:
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
    exclude_question_id: int | None = None,
) -> None:
    candidate_key = question_prompt_key(question_type, prompt, type_config)
    for row in _module_question_rows(connection, module_id):
        if exclude_question_id is not None and row["id"] == exclude_question_id:
            continue
        existing_type_config = json.loads(row["type_config_json"])
        if question_prompt_key(row["question_type"], row["prompt"], existing_type_config) == candidate_key:
            raise ValidationError("Prompt already exists in this leaf module.")


def create_question(connection: DatabaseConnection, payload: QuestionDraftIn, *, user_id: int | None = None) -> dict[str, int]:
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


def _existing_prompt_keys(connection: DatabaseConnection, module_id: int) -> set[str]:
    existing_rows = _module_question_rows(connection, module_id)
    return {
        question_prompt_key(row["question_type"], row["prompt"], json.loads(row["type_config_json"]))
        for row in existing_rows
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
