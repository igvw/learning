from fastapi import APIRouter, Depends, Response, status

from ...database import DatabaseConnection
from ...schemas import ModerationActionIn, ModerationQueueOut, ModerationRevisionActionIn, MyContributionsOut
from ...services import (
    Actor,
    delete_rejected_module_submission,
    list_moderation_queue,
    list_my_contributions,
    review_module_submission,
    review_question_revision,
    review_question_submission,
)
from ..dependencies import database_connection, require_actor, require_admin_actor


router = APIRouter()


@router.get("/api/contributions/me", response_model=MyContributionsOut)
def contributions_me(
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return list_my_contributions(connection, actor=actor)


@router.get("/api/moderation/queue", response_model=ModerationQueueOut)
def moderation_queue(
    _: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return list_moderation_queue(connection)


@router.post("/api/moderation/modules/{module_id}", response_model=dict)
def moderation_module_review(
    module_id: int,
    payload: ModerationActionIn,
    actor: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return review_module_submission(
        connection,
        module_id=module_id,
        action=payload.action,
        note=payload.note,
        actor=actor,
    )


@router.delete("/api/moderation/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def moderation_module_delete(
    module_id: int,
    _: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> Response:
    delete_rejected_module_submission(connection, module_id=module_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/moderation/questions/{question_id}", response_model=dict)
def moderation_question_review(
    question_id: int,
    payload: ModerationActionIn,
    actor: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return review_question_submission(
        connection,
        question_id=question_id,
        action=payload.action,
        note=payload.note,
        actor=actor,
    )


@router.post("/api/moderation/question-revisions/{proposal_id}", response_model=dict)
def moderation_question_revision_review(
    proposal_id: int,
    payload: ModerationRevisionActionIn,
    actor: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return review_question_revision(
        connection,
        proposal_id=proposal_id,
        action=payload.action,
        note=payload.note,
        reset_stats=payload.reset_stats,
        edited_revision=payload.edited_revision,
        actor=actor,
    )
