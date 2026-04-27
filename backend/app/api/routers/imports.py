from fastapi import APIRouter, Depends

from ...database import DatabaseConnection
from ...schemas import CommitQuestionImportIn, QuestionImportResultOut, ValidateQuestionImportIn
from ...services import Actor, commit_question_import, validate_question_import
from ..dependencies import database_connection, require_admin_actor


router = APIRouter()


@router.post("/api/question-imports/validate", response_model=QuestionImportResultOut)
def question_imports_validate(
    payload: ValidateQuestionImportIn,
    actor: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return validate_question_import(
        connection,
        module_id=payload.module_id,
        qml_text=payload.qml_text,
        rows=[row.model_dump() for row in payload.rows] if payload.rows else None,
        actor=actor,
    )


@router.post("/api/question-imports/commit", response_model=QuestionImportResultOut)
def question_imports_commit(
    payload: CommitQuestionImportIn,
    actor: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return commit_question_import(
        connection,
        module_id=payload.module_id,
        rows=[row.model_dump() for row in payload.rows],
        actor=actor,
    )
