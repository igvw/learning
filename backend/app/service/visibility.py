import json
from typing import Any

from ..database import DatabaseConnection
from .auth import Actor
from .questions import bundle_qml_from_storage


def question_visible_to_actor(row: Any, actor: Actor | None) -> bool:
    if actor is None or actor.role == "admin":
        return row["moderation_status"] != "rejected"
    if bool(row["admin_verified"]):
        return row["moderation_status"] != "rejected"
    return (
        actor.user_id is not None
        and row["created_by_user_id"] == actor.user_id
        and row["moderation_status"] == "pending"
    )


def module_visible_to_actor(row: Any, actor: Actor | None) -> bool:
    if actor is None or actor.role == "admin":
        return row["moderation_status"] != "rejected"
    if bool(row["admin_verified"]):
        return row["moderation_status"] != "rejected"
    return (
        actor.user_id is not None
        and row["created_by_user_id"] == actor.user_id
        and row["moderation_status"] == "pending"
    )


def active_viewer_proposal_question_ids(
    connection: DatabaseConnection,
    *,
    actor: Actor | None,
    question_ids: list[int],
) -> set[int]:
    if actor is None or actor.role == "admin" or actor.user_id is None or not question_ids:
        return set()
    placeholders = ",".join("?" for _ in question_ids)
    rows = connection.execute(
        f"""
        SELECT question_id
        FROM question_revision_proposals
        WHERE proposer_user_id = ?
          AND status = 'pending'
          AND question_id IN ({placeholders})
        """,
        (actor.user_id, *question_ids),
    ).fetchall()
    return {int(row["question_id"]) for row in rows}


def list_effective_question_rows(
    connection: DatabaseConnection,
    *,
    actor: Actor | None,
    scope_module_ids: list[int],
) -> list[dict[str, Any]]:
    if not scope_module_ids:
        return []

    placeholders = ",".join("?" for _ in scope_module_ids)
    rows = connection.execute(
        f"""
        SELECT
            q.id AS question_id,
            q.module_id,
            q.question_type,
            q.prompt,
            q.rank,
            q.type_config_json,
            bundles.variants_json,
            q.created_by_user_id,
            q.admin_verified,
            q.moderation_status,
            q.admin_review_note,
            m.full_slug AS module_full_slug,
            m.instruction AS module_instruction,
            creators.display_name AS creator_display_name
        FROM questions AS q
        JOIN modules AS m ON m.id = q.module_id
        LEFT JOIN question_bundles AS bundles ON bundles.question_id = q.id
        LEFT JOIN users AS creators ON creators.id = q.created_by_user_id
        WHERE q.module_id IN ({placeholders})
          AND q.moderation_status <> 'rejected'
        ORDER BY q.id ASC
        """,
        tuple(scope_module_ids),
    ).fetchall()

    question_ids = [int(row["question_id"]) for row in rows]
    active_proposal_question_ids = active_viewer_proposal_question_ids(
        connection,
        actor=actor,
        question_ids=question_ids,
    )
    effective_rows: list[dict[str, Any]] = []
    for row in rows:
        if not question_visible_to_actor(row, actor):
            continue
        if int(row["question_id"]) in active_proposal_question_ids and bool(row["admin_verified"]):
            continue

        question_type = row["question_type"]
        prompt = row["prompt"]
        type_config = json.loads(row["type_config_json"])
        bundle_qml = bundle_qml_from_storage(question_type, prompt, row["variants_json"])

        effective_rows.append(
            {
                "question_id": int(row["question_id"]),
                "module_id": int(row["module_id"]),
                "module_full_slug": row["module_full_slug"],
                "module_instruction": row["module_instruction"] or "",
                "question_type": question_type,
                "prompt": prompt,
                "rank": int(row["rank"]),
                "type_config": type_config,
                "bundle_qml": bundle_qml,
                "bundle_variants_json": row["variants_json"],
                "created_by_user_id": row["created_by_user_id"],
                "admin_verified": bool(row["admin_verified"]),
                "moderation_status": row["moderation_status"],
                "creator_display_name": row["creator_display_name"],
            }
        )
    return effective_rows


def get_effective_question_row(
    connection: DatabaseConnection,
    *,
    actor: Actor | None,
    question_id: int,
) -> dict[str, Any] | None:
    direct = connection.execute(
        """
        SELECT module_id
        FROM questions
        WHERE id = ?
        """,
        (question_id,),
    ).fetchone()
    if direct is None:
        return None
    scoped_rows = list_effective_question_rows(connection, actor=actor, scope_module_ids=[int(direct["module_id"])])
    for row in scoped_rows:
        if row["question_id"] == question_id:
            return row
    return None
