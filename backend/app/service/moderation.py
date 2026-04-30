import json
from typing import Any

from ..database import DatabaseConnection, utc_now
from ..schemas import QuestionDraftIn, QuestionRevisionIn
from .auth import Actor
from .authoring import (
    _apply_verified_question_revision,
    delete_question_record,
    ensure_unique_question_prompt,
)
from .catalog import _delete_module_subtree, _module_subtree_rows, ensure_unique_module_slug
from .errors import NotFoundError, ValidationError
from .questions import bundle_qml_from_snapshot, bundle_qml_from_storage, draft_kwargs_from_snapshot
from .text import title_from_slug


def _module_rows(
    connection: DatabaseConnection,
    *,
    moderation_statuses: tuple[str, ...],
    creator_user_id: int | None = None,
) -> list[Any]:
    status_placeholders = ", ".join("?" for _ in moderation_statuses)
    where_sql = f"""
        WHERE modules.admin_verified = 0
          AND modules.moderation_status IN ({status_placeholders})
    """
    params: tuple[Any, ...] = moderation_statuses
    if creator_user_id is not None:
        where_sql += " AND modules.created_by_user_id = ?"
        params = (*params, creator_user_id)
    return connection.execute(
        f"""
        SELECT
            modules.id,
            modules.parent_id,
            modules.slug,
            modules.full_slug,
            modules.instruction,
            modules.admin_verified,
            modules.moderation_status,
            modules.created_by_user_id,
            modules.admin_review_note,
            users.display_name AS creator_display_name
        FROM modules
        LEFT JOIN users ON users.id = modules.created_by_user_id
        {where_sql}
        ORDER BY modules.full_slug ASC
        """,
        params,
    ).fetchall()


def _pending_question_rows(connection: DatabaseConnection, *, creator_user_id: int | None = None) -> list[Any]:
    where_sql = "WHERE questions.admin_verified = 0 AND questions.enabled = 1"
    params: tuple[Any, ...] = ()
    if creator_user_id is not None:
        where_sql += " AND questions.created_by_user_id = ?"
        params = (creator_user_id,)
    return connection.execute(
        f"""
        SELECT
            questions.id AS question_id,
            questions.module_id,
            modules.full_slug AS module_full_slug,
            questions.prompt,
            questions.question_type,
            questions.rank,
            questions.type_config_json,
            bundles.variants_json,
            questions.admin_verified,
            questions.moderation_status,
            questions.created_by_user_id,
            questions.admin_review_note,
            creators.display_name AS creator_display_name
        FROM questions
        JOIN modules ON modules.id = questions.module_id
        LEFT JOIN question_bundle_summaries AS bundles ON bundles.question_id = questions.id
        LEFT JOIN users AS creators ON creators.id = questions.created_by_user_id
        {where_sql}
        ORDER BY modules.full_slug ASC, questions.rank ASC, questions.id ASC
        """,
        params,
    ).fetchall()


def _proposal_rows(connection: DatabaseConnection, *, proposer_user_id: int | None = None) -> list[Any]:
    where_sql = ""
    params: tuple[Any, ...] = ()
    if proposer_user_id is not None:
        where_sql = "WHERE proposals.proposer_user_id = ?"
        params = (proposer_user_id,)
    return connection.execute(
        f"""
        SELECT
            proposals.id AS proposal_id,
            proposals.question_id,
            proposals.proposer_user_id,
            proposals.status,
            proposals.delete_requested,
            proposals.admin_review_note,
            proposals.prompt AS proposed_prompt,
            proposals.question_type AS proposed_question_type,
            proposals.type_config_json AS proposed_type_config_json,
            questions.module_id,
            modules.full_slug AS module_full_slug,
            questions.prompt AS current_prompt,
            questions.question_type AS current_question_type,
            questions.type_config_json AS current_type_config_json,
            bundles.variants_json AS current_variants_json,
            proposers.display_name AS proposer_display_name
        FROM question_revision_proposals AS proposals
        JOIN questions ON questions.id = proposals.question_id
        JOIN modules ON modules.id = questions.module_id
        LEFT JOIN question_bundle_summaries AS bundles ON bundles.question_id = questions.id
        LEFT JOIN users AS proposers ON proposers.id = proposals.proposer_user_id
        {where_sql}
        ORDER BY proposals.updated_at DESC, proposals.id DESC
        """,
        params,
    ).fetchall()


def _module_payload(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "title": title_from_slug(row["slug"]),
        "full_slug": row["full_slug"],
        "parent_id": row["parent_id"],
        "instruction": row["instruction"] or "",
        "admin_verified": bool(row["admin_verified"]),
        "moderation_status": row["moderation_status"],
        "created_by_user_id": row["created_by_user_id"],
        "creator_display_name": row["creator_display_name"],
        "admin_review_note": row["admin_review_note"] or "",
    }


def _question_payload(row: Any) -> dict[str, Any]:
    type_config = json.loads(row["type_config_json"])
    bundle_qml = bundle_qml_from_storage(row["question_type"], row["prompt"], row["variants_json"])
    return {
        "question_id": int(row["question_id"]),
        "module_id": int(row["module_id"]),
        "module_full_slug": row["module_full_slug"],
        "prompt": row["prompt"],
        "question_type": row["question_type"],
        "rank": int(row["rank"]),
        "accepted_answers": type_config.get("accepted_answers", []),
        "segments": type_config.get("segments", []),
        "bundle_qml": bundle_qml,
        "admin_verified": bool(row["admin_verified"]),
        "moderation_status": row["moderation_status"],
        "created_by_user_id": row["created_by_user_id"],
        "creator_display_name": row["creator_display_name"],
        "admin_review_note": row["admin_review_note"] or "",
    }


def _proposal_payload(row: Any) -> dict[str, Any]:
    current_type_config = json.loads(row["current_type_config_json"])
    proposed_type_config = json.loads(row["proposed_type_config_json"])
    current_bundle_qml = bundle_qml_from_storage(
        row["current_question_type"],
        row["current_prompt"],
        row["current_variants_json"],
    )
    proposed_bundle_qml = bundle_qml_from_snapshot(
        row["proposed_question_type"],
        row["proposed_prompt"],
        proposed_type_config,
    )
    return {
        "proposal_id": int(row["proposal_id"]),
        "question_id": int(row["question_id"]),
        "proposer_user_id": int(row["proposer_user_id"]),
        "proposer_display_name": row["proposer_display_name"],
        "status": row["status"],
        "delete_requested": bool(row["delete_requested"]),
        "admin_review_note": row["admin_review_note"] or "",
        "module_id": int(row["module_id"]),
        "module_full_slug": row["module_full_slug"],
        "current_prompt": row["current_prompt"],
        "current_question_type": row["current_question_type"],
        "current_accepted_answers": current_type_config.get("accepted_answers", []),
        "current_segments": current_type_config.get("segments", []),
        "current_bundle_qml": current_bundle_qml,
        "proposed_prompt": row["proposed_prompt"],
        "proposed_question_type": row["proposed_question_type"],
        "proposed_accepted_answers": proposed_type_config.get("accepted_answers", []),
        "proposed_segments": proposed_type_config.get("segments", []),
        "proposed_bundle_qml": proposed_bundle_qml,
    }


def list_moderation_queue(connection: DatabaseConnection) -> dict[str, Any]:
    return {
        "pending_modules": [
            _module_payload(row) for row in _module_rows(connection, moderation_statuses=("pending",))
        ],
        "rejected_modules": [
            _module_payload(row) for row in _module_rows(connection, moderation_statuses=("rejected",))
        ],
        "pending_questions": [_question_payload(row) for row in _pending_question_rows(connection)],
        "pending_revisions": [_proposal_payload(row) for row in _proposal_rows(connection) if row["status"] == "pending"],
    }


def list_my_contributions(connection: DatabaseConnection, *, actor: Actor) -> dict[str, Any]:
    return {
        "modules": [
            _module_payload(row)
            for row in _module_rows(
                connection,
                moderation_statuses=("pending",),
                creator_user_id=int(actor.user_id),
            )
        ],
        "questions": [_question_payload(row) for row in _pending_question_rows(connection, creator_user_id=int(actor.user_id))],
        "revisions": [
            _proposal_payload(row)
            for row in _proposal_rows(connection, proposer_user_id=int(actor.user_id))
            if row["status"] == "pending"
        ],
    }


def review_module_submission(
    connection: DatabaseConnection,
    *,
    module_id: int,
    action: str,
    note: str,
    actor: Actor,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            modules.id,
            modules.parent_id,
            modules.slug,
            modules.full_slug,
            modules.instruction,
            modules.admin_verified,
            modules.moderation_status,
            modules.created_by_user_id,
            modules.admin_review_note,
            users.display_name AS creator_display_name
        FROM modules
        LEFT JOIN users ON users.id = modules.created_by_user_id
        WHERE modules.id = ?
        """,
        (module_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Module {module_id} was not found.")

    if action == "approve":
        ensure_unique_module_slug(connection, row["slug"], row["parent_id"], exclude_module_id=module_id)
        connection.execute(
            """
            UPDATE modules
            SET
                admin_verified = 1,
                moderation_status = 'verified',
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (note.strip(), actor.user_id, utc_now(), module_id),
        )
    else:
        connection.execute(
            """
            UPDATE modules
            SET
                admin_verified = 0,
                moderation_status = 'rejected',
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (note.strip(), actor.user_id, utc_now(), module_id),
        )
    refreshed = _module_rows(connection, moderation_statuses=("pending",))
    target = next((candidate for candidate in refreshed if int(candidate["id"]) == module_id), None)
    if target is not None:
        return _module_payload(target)
    row = connection.execute(
        """
        SELECT
            modules.id,
            modules.parent_id,
            modules.slug,
            modules.full_slug,
            modules.instruction,
            modules.admin_verified,
            modules.moderation_status,
            modules.created_by_user_id,
            modules.admin_review_note,
            users.display_name AS creator_display_name
        FROM modules
        LEFT JOIN users ON users.id = modules.created_by_user_id
        WHERE modules.id = ?
        """,
        (module_id,),
    ).fetchone()
    return _module_payload(row)


def delete_rejected_module_submission(connection: DatabaseConnection, *, module_id: int) -> None:
    row = connection.execute(
        """
        SELECT id, admin_verified, moderation_status
        FROM modules
        WHERE id = ?
        """,
        (module_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Module {module_id} was not found.")
    if bool(row["admin_verified"]) or row["moderation_status"] != "rejected":
        raise ValidationError("Only rejected unverified modules can be deleted from moderation.")

    subtree_rows = _module_subtree_rows(connection, module_id)
    module_ids = [int(candidate["id"]) for candidate in subtree_rows]
    placeholders = ", ".join("?" for _ in module_ids)
    subtree_status_rows = connection.execute(
        f"""
        SELECT id, admin_verified, moderation_status
        FROM modules
        WHERE id IN ({placeholders})
        """,
        tuple(module_ids),
    ).fetchall()
    verified_descendant = next(
        (
            candidate
            for candidate in subtree_status_rows
            if int(candidate["id"]) != module_id
            and (bool(candidate["admin_verified"]) or candidate["moderation_status"] == "verified")
        ),
        None,
    )
    if verified_descendant is not None:
        raise ValidationError(
            "Cannot delete a rejected module subtree that contains verified descendants."
        )

    _delete_module_subtree(
        connection,
        module_id=module_id,
        safety_message="Rejected module submissions with attempted questions or active quiz sessions cannot be deleted.",
    )


def review_question_submission(
    connection: DatabaseConnection,
    *,
    question_id: int,
    action: str,
    note: str,
    actor: Actor,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT question_id, module_id, module_full_slug, prompt, question_type, rank, type_config_json, admin_verified, moderation_status, created_by_user_id, admin_review_note, creator_display_name
        FROM (
            SELECT
                questions.id AS question_id,
                questions.module_id,
                modules.full_slug AS module_full_slug,
                questions.prompt,
                questions.question_type,
                questions.rank,
                questions.type_config_json,
                bundles.variants_json,
                questions.admin_verified,
                questions.moderation_status,
                questions.created_by_user_id,
                questions.admin_review_note,
                creators.display_name AS creator_display_name
            FROM questions
            JOIN modules ON modules.id = questions.module_id
            LEFT JOIN question_bundle_summaries AS bundles ON bundles.question_id = questions.id
            LEFT JOIN users AS creators ON creators.id = questions.created_by_user_id
        ) AS question_rows
        WHERE question_id = ?
        """,
        (question_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Question {question_id} was not found.")

    if action == "approve":
        ensure_unique_question_prompt(
            connection,
            module_id=int(row["module_id"]),
            question_type=row["question_type"],
            prompt=row["prompt"],
            type_config=json.loads(row["type_config_json"]),
            exclude_question_id=question_id,
        )
        connection.execute(
            """
            UPDATE questions
            SET
                admin_verified = 1,
                moderation_status = 'verified',
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (note.strip(), actor.user_id, utc_now(), question_id),
        )
    else:
        connection.execute(
            """
            UPDATE questions
            SET
                admin_verified = 0,
                moderation_status = 'rejected',
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (note.strip(), actor.user_id, utc_now(), question_id),
        )
    refreshed = _pending_question_rows(connection)
    target = next((candidate for candidate in refreshed if int(candidate["question_id"]) == question_id), None)
    if target is not None:
        return _question_payload(target)
    current = connection.execute(
        """
        SELECT
            questions.id AS question_id,
            questions.module_id,
            modules.full_slug AS module_full_slug,
            questions.prompt,
            questions.question_type,
            questions.rank,
            questions.type_config_json,
            bundles.variants_json,
            questions.admin_verified,
            questions.moderation_status,
            questions.created_by_user_id,
            questions.admin_review_note,
            creators.display_name AS creator_display_name
        FROM questions
        JOIN modules ON modules.id = questions.module_id
        LEFT JOIN question_bundle_summaries AS bundles ON bundles.question_id = questions.id
        LEFT JOIN users AS creators ON creators.id = questions.created_by_user_id
        WHERE questions.id = ?
        """,
        (question_id,),
    ).fetchone()
    return _question_payload(current)


def review_question_revision(
    connection: DatabaseConnection,
    *,
    proposal_id: int,
    action: str,
    note: str,
    reset_stats: bool | None = None,
    edited_revision: QuestionRevisionIn | None = None,
    actor: Actor,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            proposals.id AS proposal_id,
            proposals.question_id,
            proposals.proposer_user_id,
            proposals.status,
            proposals.delete_requested,
            proposals.prompt AS proposed_prompt,
            proposals.question_type AS proposed_question_type,
            proposals.type_config_json AS proposed_type_config_json,
            questions.module_id,
            questions.rank,
            questions.prompt AS current_prompt,
            questions.question_type AS current_question_type,
            questions.type_config_json AS current_type_config_json,
            bundles.variants_json AS current_variants_json,
            modules.full_slug AS module_full_slug,
            proposers.display_name AS proposer_display_name,
            proposals.admin_review_note
        FROM question_revision_proposals AS proposals
        JOIN questions ON questions.id = proposals.question_id
        JOIN modules ON modules.id = questions.module_id
        LEFT JOIN question_bundle_summaries AS bundles ON bundles.question_id = questions.id
        LEFT JOIN users AS proposers ON proposers.id = proposals.proposer_user_id
        WHERE proposals.id = ?
        """,
        (proposal_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Proposal {proposal_id} was not found.")

    if edited_revision is not None and action != "approve":
        raise ValidationError("Edited revisions can only be submitted when approving a proposal.")
    if reset_stats is not None and action != "approve":
        raise ValidationError("Reset stats can only be submitted when approving a proposal.")

    if action == "approve":
        if edited_revision is not None:
            payload_kwargs: dict[str, Any] = {
                "module_id": int(row["module_id"]),
                "prompt": edited_revision.prompt,
                "question_type": edited_revision.question_type,
                "rank": int(row["rank"]),
            }
            if edited_revision.question_type == "bundle":
                payload_kwargs["bundle_qml"] = edited_revision.bundle_qml
                payload_kwargs["bundle_variants"] = edited_revision.bundle_variants
            else:
                payload_kwargs["accepted_answers"] = edited_revision.accepted_answers
                payload_kwargs["segments"] = edited_revision.segments
            payload = QuestionDraftIn(**payload_kwargs)
            _apply_verified_question_revision(
                connection,
                question_id=int(row["question_id"]),
                payload=payload,
                reset_stats=edited_revision.reset_stats,
            )
        elif bool(row["delete_requested"]):
            delete_question_record(connection, int(row["question_id"]))
        else:
            proposed_type_config = json.loads(row["proposed_type_config_json"])
            payload_kwargs = draft_kwargs_from_snapshot(
                module_id=int(row["module_id"]),
                prompt=row["proposed_prompt"],
                question_type=row["proposed_question_type"],
                rank=int(row["rank"]),
                type_config=proposed_type_config,
            )
            _apply_verified_question_revision(
                connection,
                question_id=int(row["question_id"]),
                payload=QuestionDraftIn(**payload_kwargs),
                reset_stats=bool(reset_stats),
            )
        connection.execute(
            """
            UPDATE question_revision_proposals
            SET
                status = 'approved',
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (note.strip(), actor.user_id, utc_now(), proposal_id),
        )
    else:
        connection.execute(
            """
            UPDATE question_revision_proposals
            SET
                status = 'rejected',
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (note.strip(), actor.user_id, utc_now(), proposal_id),
        )

    refreshed = connection.execute(
        """
        SELECT
            proposals.id AS proposal_id,
            proposals.question_id,
            proposals.proposer_user_id,
            proposals.status,
            proposals.delete_requested,
            proposals.admin_review_note,
            proposals.prompt AS proposed_prompt,
            proposals.question_type AS proposed_question_type,
            proposals.type_config_json AS proposed_type_config_json,
            questions.module_id,
            modules.full_slug AS module_full_slug,
            questions.prompt AS current_prompt,
            questions.question_type AS current_question_type,
            questions.type_config_json AS current_type_config_json,
            bundles.variants_json AS current_variants_json,
            proposers.display_name AS proposer_display_name
        FROM question_revision_proposals AS proposals
        JOIN questions ON questions.id = proposals.question_id
        JOIN modules ON modules.id = questions.module_id
        LEFT JOIN question_bundle_summaries AS bundles ON bundles.question_id = questions.id
        LEFT JOIN users AS proposers ON proposers.id = proposals.proposer_user_id
        WHERE proposals.id = ?
        """,
        (proposal_id,),
    ).fetchone()
    if refreshed is None:
        return {"proposal_id": proposal_id, "question_id": int(row["question_id"])}
    return _proposal_payload(refreshed)
