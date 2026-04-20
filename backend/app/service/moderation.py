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
from .catalog import ensure_unique_module_slug
from .errors import NotFoundError, ValidationError
from .text import title_from_slug


def _stored_rejection_status(action: str) -> str:
    return "rejected" if action == "reject" else action


def _pending_module_rows(connection: DatabaseConnection, *, creator_user_id: int | None = None) -> list[Any]:
    where_sql = "WHERE modules.admin_verified = 0"
    params: tuple[Any, ...] = ()
    if creator_user_id is not None:
        where_sql += " AND modules.created_by_user_id = ?"
        params = (creator_user_id,)
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
    where_sql = "WHERE questions.admin_verified = 0"
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
            questions.admin_verified,
            questions.moderation_status,
            questions.created_by_user_id,
            questions.admin_review_note,
            creators.display_name AS creator_display_name
        FROM questions
        JOIN modules ON modules.id = questions.module_id
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
            proposers.display_name AS proposer_display_name
        FROM question_revision_proposals AS proposals
        JOIN questions ON questions.id = proposals.question_id
        JOIN modules ON modules.id = questions.module_id
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
    return {
        "question_id": int(row["question_id"]),
        "module_id": int(row["module_id"]),
        "module_full_slug": row["module_full_slug"],
        "prompt": row["prompt"],
        "question_type": row["question_type"],
        "rank": int(row["rank"]),
        "accepted_answers": type_config.get("accepted_answers", []),
        "segments": type_config.get("segments", []),
        "admin_verified": bool(row["admin_verified"]),
        "moderation_status": row["moderation_status"],
        "created_by_user_id": row["created_by_user_id"],
        "creator_display_name": row["creator_display_name"],
        "admin_review_note": row["admin_review_note"] or "",
    }


def _proposal_payload(row: Any) -> dict[str, Any]:
    current_type_config = json.loads(row["current_type_config_json"])
    proposed_type_config = json.loads(row["proposed_type_config_json"])
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
        "proposed_prompt": row["proposed_prompt"],
        "proposed_question_type": row["proposed_question_type"],
        "proposed_accepted_answers": proposed_type_config.get("accepted_answers", []),
        "proposed_segments": proposed_type_config.get("segments", []),
    }


def list_moderation_queue(connection: DatabaseConnection) -> dict[str, Any]:
    return {
        "pending_modules": [_module_payload(row) for row in _pending_module_rows(connection)],
        "pending_questions": [_question_payload(row) for row in _pending_question_rows(connection)],
        "pending_revisions": [_proposal_payload(row) for row in _proposal_rows(connection) if row["status"] in {"pending", "changes_requested"}],
    }


def list_my_contributions(connection: DatabaseConnection, *, actor: Actor) -> dict[str, Any]:
    return {
        "modules": [_module_payload(row) for row in _pending_module_rows(connection, creator_user_id=int(actor.user_id))],
        "questions": [_question_payload(row) for row in _pending_question_rows(connection, creator_user_id=int(actor.user_id))],
        "revisions": [
            _proposal_payload(row)
            for row in _proposal_rows(connection, proposer_user_id=int(actor.user_id))
            if row["status"] in {"pending", "changes_requested"}
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
                moderation_status = ?,
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (_stored_rejection_status(action), note.strip(), actor.user_id, utc_now(), module_id),
        )
    refreshed = _pending_module_rows(connection)
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
                questions.admin_verified,
                questions.moderation_status,
                questions.created_by_user_id,
                questions.admin_review_note,
                creators.display_name AS creator_display_name
            FROM questions
            JOIN modules ON modules.id = questions.module_id
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
                moderation_status = ?,
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (_stored_rejection_status(action), note.strip(), actor.user_id, utc_now(), question_id),
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
            questions.admin_verified,
            questions.moderation_status,
            questions.created_by_user_id,
            questions.admin_review_note,
            creators.display_name AS creator_display_name
        FROM questions
        JOIN modules ON modules.id = questions.module_id
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
            modules.full_slug AS module_full_slug,
            proposers.display_name AS proposer_display_name,
            proposals.admin_review_note
        FROM question_revision_proposals AS proposals
        JOIN questions ON questions.id = proposals.question_id
        JOIN modules ON modules.id = questions.module_id
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
            payload = QuestionDraftIn(
                module_id=int(row["module_id"]),
                prompt=edited_revision.prompt,
                question_type=edited_revision.question_type,
                rank=int(row["rank"]),
                accepted_answers=edited_revision.accepted_answers,
                segments=edited_revision.segments,
            )
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
            _apply_verified_question_revision(
                connection,
                question_id=int(row["question_id"]),
                payload=QuestionDraftIn(
                    module_id=int(row["module_id"]),
                    prompt=row["proposed_prompt"],
                    question_type=row["proposed_question_type"],
                    rank=int(row["rank"]),
                    accepted_answers=proposed_type_config.get("accepted_answers", []),
                    segments=proposed_type_config.get("segments", []),
                ),
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
                status = ?,
                admin_review_note = ?,
                reviewed_by_user_id = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (_stored_rejection_status(action), note.strip(), actor.user_id, utc_now(), proposal_id),
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
            proposers.display_name AS proposer_display_name
        FROM question_revision_proposals AS proposals
        JOIN questions ON questions.id = proposals.question_id
        JOIN modules ON modules.id = questions.module_id
        LEFT JOIN users AS proposers ON proposers.id = proposals.proposer_user_id
        WHERE proposals.id = ?
        """,
        (proposal_id,),
    ).fetchone()
    if refreshed is None:
        return {"proposal_id": proposal_id, "question_id": int(row["question_id"])}
    return _proposal_payload(refreshed)
