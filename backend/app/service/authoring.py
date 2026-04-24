import json
from pathlib import Path
from typing import Any

from ..config import FORCED_UNORDERED_PROMPTS
from ..database import DatabaseConnection, execute_insert_returning_id, utc_now
from ..qml import parse_qml_line, qml_lines_from_text
from ..schemas import QuestionDraftIn
from .auth import Actor
from .bundles import (
    bundle_snapshot_type_config,
    bundle_summary,
    delete_question_bundle,
    normalize_bundle_payload,
    upsert_question_bundle,
)
from .catalog import (
    ensure_leaf_module,
    ensure_module_can_accept_children,
    ensure_unique_module_slug,
    ensure_user_exists,
)
from .errors import NotFoundError, ValidationError
from .questions import draft_kwargs_from_storage, serialize_type_config, stored_prompt_key
from .text import json_dumps, normalize_text
from .visibility import question_visible_to_actor


def _append_rank(connection: DatabaseConnection, module_id: int) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(rank), 0) AS max_rank FROM questions WHERE module_id = ?",
        (module_id,),
    ).fetchone()
    return int(row["max_rank"]) + 1


def _normalized_question_storage(payload: QuestionDraftIn) -> tuple[str, dict[str, Any], list[dict[str, Any]] | None]:
    if payload.question_type == "bundle":
        prompt, variants, _ = normalize_bundle_payload(payload)
        return prompt, bundle_summary(prompt, variants), variants
    return payload.prompt.strip(), serialize_type_config(payload), None


def _proposal_type_config(payload: QuestionDraftIn) -> tuple[str, dict[str, Any], list[dict[str, Any]] | None]:
    if payload.question_type == "bundle":
        prompt, variants, _ = normalize_bundle_payload(payload)
        return prompt, bundle_snapshot_type_config(prompt, variants), variants
    return payload.prompt.strip(), serialize_type_config(payload), None


def _store_bundle_definition(
    connection: DatabaseConnection,
    *,
    question_id: int,
    question_type: str,
    bundle_variants: list[dict[str, Any]] | None,
) -> None:
    if question_type == "bundle":
        upsert_question_bundle(connection, question_id=question_id, variants=bundle_variants or [])
        return
    delete_question_bundle(connection, question_id=question_id)


def ensure_unique_question_prompt(
    connection: DatabaseConnection,
    *,
    module_id: int,
    question_type: str,
    prompt: str,
    type_config: dict[str, Any],
    actor: Actor | None = None,
    exclude_question_id: int | None = None,
) -> None:
    candidate_key = stored_prompt_key(question_type, prompt, type_config)
    rows = connection.execute(
        """
        SELECT id, created_by_user_id, admin_verified, moderation_status
        FROM questions
        WHERE module_id = ?
          AND prompt_key = ?
        """,
        (module_id, candidate_key),
    ).fetchall()
    for row in rows:
        if exclude_question_id is not None and row["id"] == exclude_question_id:
            continue
        if question_visible_to_actor(row, actor):
            raise ValidationError("Prompt already exists in this leaf module.")


def _insert_question_record(
    connection: DatabaseConnection,
    *,
    payload: QuestionDraftIn,
    rank: int,
    actor: Actor | None,
) -> dict[str, Any]:
    user_id = actor.user_id if actor and actor.user_id is not None else None
    is_verified = actor is None or actor.role == "admin"
    moderation_status = "verified" if is_verified else "pending"
    prompt, type_config, bundle_variants = _normalized_question_storage(payload)
    question_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO questions (
            module_id,
            question_type,
            prompt,
            prompt_key,
            rank,
            type_config_json,
            created_by_user_id,
            admin_verified,
            moderation_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.module_id,
            payload.question_type,
            prompt,
            stored_prompt_key(payload.question_type, prompt, type_config),
            rank,
            json_dumps(type_config),
            user_id,
            1 if is_verified else 0,
            moderation_status,
        ),
    )
    _store_bundle_definition(
        connection,
        question_id=question_id,
        question_type=payload.question_type,
        bundle_variants=bundle_variants,
    )
    return {
        "question_id": question_id,
        "admin_verified": is_verified,
        "moderation_status": moderation_status,
        "delete_requested": False,
        "proposal_id": None,
    }


def create_question_append_only(
    connection: DatabaseConnection,
    payload: QuestionDraftIn,
    *,
    actor: Actor | None = None,
) -> dict[str, Any]:
    ensure_leaf_module(connection, payload.module_id, actor=actor)
    prompt, type_config, _ = _normalized_question_storage(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=prompt,
        type_config=type_config,
        actor=actor,
    )
    return _insert_question_record(connection, payload=payload, rank=_append_rank(connection, payload.module_id), actor=actor)


def create_question(connection: DatabaseConnection, payload: QuestionDraftIn, *, actor: Actor | None = None) -> dict[str, Any]:
    ensure_leaf_module(connection, payload.module_id, actor=actor)
    prompt, type_config, _ = _normalized_question_storage(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=prompt,
        type_config=type_config,
        actor=actor,
    )
    return _insert_question_record(connection, payload=payload, rank=_append_rank(connection, payload.module_id), actor=actor)


def _question_row(connection: DatabaseConnection, question_id: int) -> Any:
    return connection.execute(
        """
        SELECT
            id,
            module_id,
            rank,
            question_type,
            prompt,
            type_config_json,
            bundles.variants_json,
            created_by_user_id,
            admin_verified,
            moderation_status
        FROM questions
        LEFT JOIN question_bundles AS bundles ON bundles.question_id = questions.id
        WHERE id = ?
        """,
        (question_id,),
    ).fetchone()


def _require_question_row(connection: DatabaseConnection, question_id: int) -> Any:
    row = _question_row(connection, question_id)
    if row is None:
        raise NotFoundError(f"Question {question_id} was not found.")
    return row


def _apply_verified_question_revision(
    connection: DatabaseConnection,
    *,
    question_id: int,
    payload: QuestionDraftIn,
    reset_stats: bool,
) -> None:
    current = _require_question_row(connection, question_id)
    ensure_leaf_module(connection, payload.module_id)
    prompt, type_config, bundle_variants = _normalized_question_storage(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=prompt,
        type_config=type_config,
        exclude_question_id=question_id,
    )
    if reset_stats:
        connection.execute("DELETE FROM quiz_session_items WHERE question_id = ?", (question_id,))
        connection.execute("DELETE FROM attempts WHERE legacy_question_id = ?", (question_id,))
        connection.execute("DELETE FROM user_review_flags WHERE question_id = ?", (question_id,))

    target_rank = int(current["rank"]) if int(current["module_id"]) == payload.module_id else _append_rank(connection, payload.module_id)

    connection.execute(
        """
        UPDATE questions
        SET
            module_id = ?,
            question_type = ?,
            prompt = ?,
            prompt_key = ?,
            rank = ?,
            type_config_json = ?,
            admin_review_note = '',
            reviewed_by_user_id = NULL,
            reviewed_at = NULL
        WHERE id = ?
        """,
        (
            payload.module_id,
            payload.question_type,
            prompt,
            stored_prompt_key(payload.question_type, prompt, type_config),
            target_rank,
            json_dumps(type_config),
            question_id,
        ),
    )
    _store_bundle_definition(
        connection,
        question_id=question_id,
        question_type=payload.question_type,
        bundle_variants=bundle_variants,
    )
    connection.execute("DELETE FROM user_review_flags WHERE question_id = ?", (question_id,))


def apply_import_revision(connection: DatabaseConnection, *, question_id: int, payload: QuestionDraftIn) -> None:
    _require_question_row(connection, question_id)
    ensure_leaf_module(connection, payload.module_id)
    prompt, type_config, bundle_variants = _normalized_question_storage(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=prompt,
        type_config=type_config,
        exclude_question_id=question_id,
    )
    connection.execute(
        """
        UPDATE questions
        SET
            question_type = ?,
            prompt = ?,
            prompt_key = ?,
            type_config_json = ?,
            admin_review_note = '',
            reviewed_by_user_id = NULL,
            reviewed_at = NULL
        WHERE id = ?
        """,
        (
            payload.question_type,
            prompt,
            stored_prompt_key(payload.question_type, prompt, type_config),
            json_dumps(type_config),
            question_id,
        ),
    )
    _store_bundle_definition(
        connection,
        question_id=question_id,
        question_type=payload.question_type,
        bundle_variants=bundle_variants,
    )
    connection.execute("DELETE FROM user_review_flags WHERE question_id = ?", (question_id,))


def relocate_question_for_import(
    connection: DatabaseConnection,
    *,
    question_id: int,
    payload: QuestionDraftIn,
) -> int:
    current = _require_question_row(connection, question_id)
    ensure_leaf_module(connection, payload.module_id)
    prompt, type_config, bundle_variants = _normalized_question_storage(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=prompt,
        type_config=type_config,
        exclude_question_id=question_id,
    )
    target_rank = _append_rank(connection, payload.module_id)
    connection.execute(
        """
        UPDATE questions
        SET
            module_id = ?,
            question_type = ?,
            prompt = ?,
            prompt_key = ?,
            rank = ?,
            type_config_json = ?,
            admin_review_note = '',
            reviewed_by_user_id = NULL,
            reviewed_at = NULL
        WHERE id = ?
        """,
        (
            payload.module_id,
            payload.question_type,
            prompt,
            stored_prompt_key(payload.question_type, prompt, type_config),
            target_rank,
            json_dumps(type_config),
            question_id,
        ),
    )
    _store_bundle_definition(
        connection,
        question_id=question_id,
        question_type=payload.question_type,
        bundle_variants=bundle_variants,
    )
    connection.execute("DELETE FROM user_review_flags WHERE question_id = ?", (question_id,))
    return int(current["module_id"])


def _proposal_payload(
    *,
    question_id: int,
    proposer_user_id: int,
    payload: QuestionDraftIn,
    delete_requested: bool,
) -> tuple[Any, ...]:
    prompt, type_config, _ = _proposal_type_config(payload)
    now = utc_now()
    return (
        question_id,
        proposer_user_id,
        prompt,
        payload.question_type,
        json_dumps(type_config),
        1 if delete_requested else 0,
        "pending",
        "",
        now,
        now,
    )


def _upsert_question_revision_proposal(
    connection: DatabaseConnection,
    *,
    question_id: int,
    actor: Actor,
    payload: QuestionDraftIn,
    delete_requested: bool,
) -> dict[str, Any]:
    existing = connection.execute(
        """
        SELECT id
        FROM question_revision_proposals
        WHERE question_id = ? AND proposer_user_id = ?
        """,
        (question_id, actor.user_id),
    ).fetchone()
    if existing is None:
        proposal_id = execute_insert_returning_id(
            connection,
            """
            INSERT INTO question_revision_proposals (
                question_id,
                proposer_user_id,
                prompt,
                question_type,
                type_config_json,
                delete_requested,
                status,
                admin_review_note,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _proposal_payload(
                question_id=question_id,
                proposer_user_id=int(actor.user_id),
                payload=payload,
                delete_requested=delete_requested,
            ),
        )
    else:
        proposal_id = int(existing["id"])
        prompt, type_config, _ = _proposal_type_config(payload)
        connection.execute(
            """
            UPDATE question_revision_proposals
            SET
                prompt = ?,
                question_type = ?,
                type_config_json = ?,
                delete_requested = ?,
                status = 'pending',
                admin_review_note = '',
                reviewed_by_user_id = NULL,
                reviewed_at = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (
                prompt,
                payload.question_type,
                json_dumps(type_config),
                1 if delete_requested else 0,
                utc_now(),
                proposal_id,
            ),
        )
    return {"proposal_id": proposal_id, "question_id": question_id}


def revise_question(
    connection: DatabaseConnection,
    question_id: int,
    payload: QuestionDraftIn,
    *,
    reset_stats: bool,
    actor: Actor | None = None,
) -> dict[str, Any]:
    current = _require_question_row(connection, question_id)
    if actor is None or actor.role == "admin":
        _apply_verified_question_revision(connection, question_id=question_id, payload=payload, reset_stats=reset_stats)
        return {
            "question_id": question_id,
            "proposal_id": None,
            "admin_verified": True,
            "moderation_status": "verified",
            "delete_requested": False,
        }

    if bool(current["admin_verified"]):
        if payload.module_id != int(current["module_id"]):
            raise ValidationError("Regular-user revisions cannot move a verified question to another module.")
        if int(payload.rank) != int(current["rank"]):
            raise ValidationError("Regular-user revisions cannot change rank for a verified question.")
        proposal = _upsert_question_revision_proposal(
            connection,
            question_id=question_id,
            actor=actor,
            payload=payload,
            delete_requested=False,
        )
        return {
            "question_id": question_id,
            "proposal_id": proposal["proposal_id"],
            "admin_verified": True,
            "moderation_status": "verified",
            "delete_requested": False,
        }

    if actor.user_id is None or current["created_by_user_id"] != actor.user_id:
        raise ValidationError("You can only revise your own pending questions.")

    ensure_leaf_module(connection, payload.module_id, actor=actor)
    prompt, type_config, bundle_variants = _normalized_question_storage(payload)
    ensure_unique_question_prompt(
        connection,
        module_id=payload.module_id,
        question_type=payload.question_type,
        prompt=prompt,
        type_config=type_config,
        actor=actor,
        exclude_question_id=question_id,
    )
    target_rank = int(current["rank"]) if int(current["module_id"]) == payload.module_id else _append_rank(connection, payload.module_id)
    connection.execute(
        """
        UPDATE questions
        SET
            module_id = ?,
            question_type = ?,
            prompt = ?,
            prompt_key = ?,
            rank = ?,
            type_config_json = ?,
            moderation_status = 'pending',
            admin_review_note = '',
            reviewed_by_user_id = NULL,
            reviewed_at = NULL
        WHERE id = ?
        """,
        (
            payload.module_id,
            payload.question_type,
            prompt,
            stored_prompt_key(payload.question_type, prompt, type_config),
            target_rank,
            json_dumps(type_config),
            question_id,
        ),
    )
    _store_bundle_definition(
        connection,
        question_id=question_id,
        question_type=payload.question_type,
        bundle_variants=bundle_variants,
    )
    return {
        "question_id": question_id,
        "proposal_id": None,
        "admin_verified": False,
        "moderation_status": "pending",
        "delete_requested": False,
    }


def delete_question(connection: DatabaseConnection, question_id: int, *, actor: Actor | None = None) -> dict[str, Any]:
    current = _require_question_row(connection, question_id)
    if actor is None or actor.role == "admin":
        delete_question_record(connection, question_id)
        return {
            "question_id": question_id,
            "proposal_id": None,
            "admin_verified": bool(current["admin_verified"]),
            "moderation_status": current["moderation_status"],
            "delete_requested": False,
        }

    if not bool(current["admin_verified"]):
        if actor.user_id is None or current["created_by_user_id"] != actor.user_id:
            raise ValidationError("You can only delete your own pending questions.")
        delete_question_record(connection, question_id)
        return {
            "question_id": question_id,
            "proposal_id": None,
            "admin_verified": False,
            "moderation_status": "pending",
            "delete_requested": False,
        }

    current_type_config = json.loads(current["type_config_json"])
    proposal_payload = QuestionDraftIn(
        **draft_kwargs_from_storage(
            module_id=int(current["module_id"]),
            prompt=current["prompt"],
            question_type=current["question_type"],
            rank=int(current["rank"]),
            type_config=current_type_config,
            variants_json=current["variants_json"],
        )
    )
    proposal = _upsert_question_revision_proposal(
        connection,
        question_id=question_id,
        actor=actor,
        payload=proposal_payload,
        delete_requested=True,
    )
    return {
        "question_id": question_id,
        "proposal_id": proposal["proposal_id"],
        "admin_verified": True,
        "moderation_status": "verified",
        "delete_requested": True,
    }


def set_question_review_flag(
    connection: DatabaseConnection,
    *,
    user_id: int,
    question_id: int,
    review_flag: bool,
) -> dict[str, Any]:
    ensure_user_exists(connection, user_id)
    _require_question_row(connection, question_id)
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
def _session_item_merge_priority(row: dict[str, Any]) -> tuple[int, float, int]:
    answered = row["score_earned"] is not None and row["score_possible"] is not None
    if answered and row["score_possible"]:
        accuracy = float(row["score_earned"]) / float(row["score_possible"])
    else:
        accuracy = 1.0
    return (
        0 if answered else 1,
        accuracy,
        0 if row.get("submitted_answer_json") else 1,
    )


def _merge_session_item_rows(existing_row: dict[str, Any], incoming_row: dict[str, Any]) -> dict[str, Any]:
    preferred = min((existing_row, incoming_row), key=_session_item_merge_priority)
    merged = dict(preferred)
    for key in ("resolved_prompt", "resolved_type_config_json", "submitted_answer_json"):
        if not merged.get(key):
            merged[key] = existing_row.get(key) or incoming_row.get(key)
    return merged


def merge_question_progress(
    connection: DatabaseConnection,
    *,
    survivor_question_id: int,
    merged_question_ids: list[int],
) -> None:
    survivor = _require_question_row(connection, survivor_question_id)
    survivor_module_id = int(survivor["module_id"])
    for merged_question_id in merged_question_ids:
        session_rows = connection.execute(
            """
            SELECT
                session_id,
                question_id,
                score_earned,
                score_possible,
                resolved_prompt,
                resolved_type_config_json,
                submitted_answer_json
            FROM quiz_session_items
            WHERE question_id = ?
            ORDER BY session_id ASC
            """,
            (merged_question_id,),
        ).fetchall()
        for row in session_rows:
            existing = connection.execute(
                """
                SELECT
                    session_id,
                    question_id,
                    score_earned,
                    score_possible,
                    resolved_prompt,
                    resolved_type_config_json,
                    submitted_answer_json
                FROM quiz_session_items
                WHERE session_id = ? AND question_id = ?
                """,
                (row["session_id"], survivor_question_id),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    UPDATE quiz_session_items
                    SET question_id = ?
                    WHERE session_id = ? AND question_id = ?
                    """,
                    (survivor_question_id, row["session_id"], merged_question_id),
                )
                continue

            merged_item = _merge_session_item_rows(dict(existing), dict(row))
            connection.execute(
                """
                UPDATE quiz_session_items
                SET
                    score_earned = ?,
                    score_possible = ?,
                    resolved_prompt = ?,
                    resolved_type_config_json = ?,
                    submitted_answer_json = ?
                WHERE session_id = ? AND question_id = ?
                """,
                (
                    merged_item["score_earned"],
                    merged_item["score_possible"],
                    merged_item["resolved_prompt"],
                    merged_item["resolved_type_config_json"],
                    merged_item["submitted_answer_json"],
                    row["session_id"],
                    survivor_question_id,
                ),
            )
            connection.execute(
                "DELETE FROM quiz_session_items WHERE session_id = ? AND question_id = ?",
                (row["session_id"], merged_question_id),
            )
        attempt_rows = connection.execute(
            """
            SELECT
                id,
                session_id,
                legacy_question_id,
                question_id,
                module_id,
                score_earned,
                score_possible,
                resolved_prompt,
                resolved_type_config_json,
                submitted_answer_json,
                answered_at
            FROM attempts
            WHERE legacy_question_id = ?
            ORDER BY session_id ASC, id ASC
            """,
            (merged_question_id,),
        ).fetchall()
        for row in attempt_rows:
            existing = connection.execute(
                """
                SELECT
                    id,
                    session_id,
                    legacy_question_id,
                    question_id,
                    module_id,
                    score_earned,
                    score_possible,
                    resolved_prompt,
                    resolved_type_config_json,
                    submitted_answer_json,
                    answered_at
                FROM attempts
                WHERE session_id = ? AND legacy_question_id = ?
                """,
                (row["session_id"], survivor_question_id),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    UPDATE attempts
                    SET legacy_question_id = ?, question_id = ?, module_id = ?
                    WHERE id = ?
                    """,
                    (survivor_question_id, survivor_question_id, survivor_module_id, row["id"]),
                )
                continue

            merged_attempt = _merge_session_item_rows(dict(existing), dict(row))
            connection.execute(
                """
                UPDATE attempts
                SET
                    question_id = ?,
                    module_id = ?,
                    score_earned = ?,
                    score_possible = ?,
                    resolved_prompt = ?,
                    resolved_type_config_json = ?,
                    submitted_answer_json = ?,
                    answered_at = ?
                WHERE id = ?
                """,
                (
                    survivor_question_id,
                    survivor_module_id,
                    merged_attempt["score_earned"],
                    merged_attempt["score_possible"],
                    merged_attempt["resolved_prompt"],
                    merged_attempt["resolved_type_config_json"],
                    merged_attempt["submitted_answer_json"],
                    merged_attempt["answered_at"],
                    existing["id"],
                ),
            )
            connection.execute("DELETE FROM attempts WHERE id = ?", (row["id"],))


def delete_question_record(connection: DatabaseConnection, question_id: int) -> None:
    row = _question_row(connection, question_id)
    if row is None:
        return
    connection.execute("DELETE FROM questions WHERE id = ?", (question_id,))


def _existing_prompt_keys(connection: DatabaseConnection, module_id: int) -> set[str]:
    rows = connection.execute(
        """
        SELECT prompt_key
        FROM questions
        WHERE module_id = ?
          AND moderation_status <> 'rejected'
        """,
        (module_id,),
    ).fetchall()
    return {row["prompt_key"] for row in rows}


def backfill_session_scores(connection: DatabaseConnection) -> None:
    connection.execute(
        """
        UPDATE quiz_session_items
        SET score_possible = 1
        WHERE score_possible IS NULL OR score_possible = 0
        """
    )
    connection.execute(
        """
        UPDATE attempts
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
                SET question_type = ?, type_config_json = ?, prompt_key = ?
                WHERE id = ?
                """,
                (question_type, json_dumps(type_config), stored_prompt_key(question_type, row["prompt"], type_config), row["id"]),
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
            payload = QuestionDraftIn(
                **parse_qml_line(line=row["qml_text"], module_id=module_id, rank=row["start_line"])
            )
            type_config = serialize_type_config(payload)
            prompt_key = stored_prompt_key(payload.question_type, payload.prompt, type_config)
            if prompt_key in existing_prompt_keys:
                continue
            create_question(connection, payload)
            existing_prompt_keys.add(prompt_key)
            imported_questions += 1

    backfill_question_type_defaults(connection)
    backfill_session_scores(connection)
    return {"modules": imported_modules, "questions": imported_questions}
