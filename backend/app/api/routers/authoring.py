from fastapi import APIRouter, Depends

from ...database import DatabaseConnection
from ...schemas import QuestionDraftIn, QuestionMutationOut, QuestionReviewFlagIn, QuestionReviewFlagOut, QuestionRevisionIn
from ...services import Actor, create_question, delete_question, revise_question, set_question_review_flag
from ..dependencies import actor_key, database_connection, require_actor, require_real_actor


router = APIRouter()


@router.post("/api/questions", response_model=QuestionMutationOut)
def questions_create(
    payload: QuestionDraftIn,
    actor: Actor = Depends(require_real_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return create_question(connection, payload, actor=actor)


@router.post("/api/questions/{question_id}/revisions", response_model=QuestionMutationOut)
def questions_revise(
    question_id: int,
    payload: QuestionRevisionIn,
    actor: Actor = Depends(require_real_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    draft = QuestionDraftIn(**payload.model_dump(exclude={"reset_stats"}))
    return revise_question(connection, question_id, draft, reset_stats=payload.reset_stats, actor=actor)


@router.delete("/api/questions/{question_id}", response_model=QuestionMutationOut)
def questions_delete(
    question_id: int,
    actor: Actor = Depends(require_real_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return delete_question(connection, question_id, actor=actor)


@router.patch("/api/questions/{question_id}/review-flag", response_model=QuestionReviewFlagOut)
def questions_review_flag(
    question_id: int,
    payload: QuestionReviewFlagIn,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    from ...services import set_demo_review_flag

    if actor.is_demo:
        return set_demo_review_flag(
            actor_key=actor_key(actor),
            question_id=question_id,
            review_flag=payload.review_flag,
        )
    return set_question_review_flag(
        connection,
        user_id=int(actor.user_id),
        question_id=question_id,
        review_flag=payload.review_flag,
    )
