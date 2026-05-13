from fastapi import APIRouter, Depends

from ...database import DatabaseConnection
from ...schemas import (
    QuestionDraftIn,
    QuestionMutationOut,
    QuestionRevisionIn,
    QuestionRowOut,
)
from ...services import (
    Actor,
    create_question,
    delete_question,
    get_question,
    revise_question,
    withdraw_question_revision,
)
from ..dependencies import database_connection, require_actor


router = APIRouter()


@router.get("/api/questions/{question_id}", response_model=QuestionRowOut)
def questions_get(
    question_id: int,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return get_question(connection, user_id=int(actor.user_id), question_id=question_id, actor=actor)


@router.post("/api/questions", response_model=QuestionMutationOut)
def questions_create(
    payload: QuestionDraftIn,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return create_question(connection, payload, actor=actor)


@router.post("/api/questions/{question_id}/revisions", response_model=QuestionMutationOut)
def questions_revise(
    question_id: int,
    payload: QuestionRevisionIn,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    draft = QuestionDraftIn(**payload.model_dump(exclude={"reset_stats"}))
    return revise_question(connection, question_id, draft, reset_stats=payload.reset_stats, actor=actor)


@router.delete("/api/questions/{question_id}", response_model=QuestionMutationOut)
def questions_delete(
    question_id: int,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return delete_question(connection, question_id, actor=actor)


@router.delete("/api/questions/{question_id}/revisions/mine", status_code=204)
def questions_revision_withdraw(
    question_id: int,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> None:
    withdraw_question_revision(connection, actor=actor, question_id=question_id)
    return None
