from fastapi import APIRouter, Depends

from ...database import DatabaseConnection
from ...schemas import QuizSessionCreateIn, QuizSessionOut, SubmitAnswerIn, SubmitAnswerOut
from ...services import Actor, create_quiz_session, submit_answer
from ..dependencies import database_connection, require_actor


router = APIRouter()


@router.post("/api/quiz-sessions", response_model=QuizSessionOut)
def quiz_sessions_create(
    payload: QuizSessionCreateIn,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return create_quiz_session(
        connection,
        user_id=int(actor.user_id),
        module_id=payload.module_id,
        count=payload.count,
        actor=actor,
    )


@router.post("/api/quiz-sessions/{session_id}/items/{item_id}/submit", response_model=SubmitAnswerOut)
def quiz_sessions_submit(
    session_id: int,
    item_id: int,
    payload: SubmitAnswerIn,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return submit_answer(
        connection,
        user_id=int(actor.user_id),
        session_id=session_id,
        item_id=item_id,
        answers=payload.answers,
    )
