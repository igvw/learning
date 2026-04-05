from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import get_connection, initialize_database
from .schemas import (
    CreateModuleIn,
    CreateQuestionImportSessionIn,
    ModuleNodeOut,
    QuestionDraftIn,
    QuestionImportSessionOut,
    QuestionMutationOut,
    QuestionReviewFlagIn,
    QuestionReviewFlagOut,
    QuestionRevisionIn,
    QuizSessionCreateIn,
    QuizSessionOut,
    RevalidateQuestionImportSessionIn,
    StatsResponseOut,
    SubmitAnswerIn,
    SubmitAnswerOut,
    UserCreateIn,
    UserOut,
)
from .services import (
    ServiceError,
    commit_question_import_session,
    create_module,
    create_question,
    create_question_import_session,
    create_quiz_session,
    create_user,
    discard_question_import_session_row,
    get_module_tree,
    get_stats,
    list_users,
    revalidate_question_import_session,
    revise_question,
    set_question_review_flag,
    submit_answer,
    sync_seed_content,
)
from .settings import CONTENT_DIR, FRONTEND_DIST_DIR, cors_origins, resolve_database_url, seed_on_boot


def _handle_service_error(error: ServiceError) -> None:
    raise HTTPException(status_code=error.status_code, detail=str(error)) from error


def _require_user_id(x_user_id: Optional[int]) -> int:
    if x_user_id is None:
        raise HTTPException(status_code=400, detail="X-User-Id header is required.")
    return x_user_id


def create_app(
    database_url: Optional[Union[str, Path]] = None,
    content_root: Optional[Union[str, Path]] = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize_database(app.state.database_url)
        if seed_on_boot():
            with get_connection(app.state.database_url) as connection:
                sync_seed_content(connection, app.state.content_root)
        yield

    app = FastAPI(title="Learning App API", lifespan=lifespan)
    app.state.database_url = resolve_database_url(database_url)
    app.state.content_root = Path(content_root).resolve() if content_root else CONTENT_DIR

    allowed_origins = cors_origins()
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/modules/tree", response_model=list[ModuleNodeOut])
    def modules_tree() -> list[dict]:
        with get_connection(app.state.database_url) as connection:
            return get_module_tree(connection)

    @app.get("/api/users", response_model=list[UserOut])
    def users_list() -> list[dict]:
        with get_connection(app.state.database_url) as connection:
            try:
                return list_users(connection)
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/users", response_model=UserOut)
    def users_create(payload: UserCreateIn) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return create_user(connection, handle=payload.handle, display_name=payload.display_name)
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/modules", response_model=ModuleNodeOut)
    def modules_create(payload: CreateModuleIn) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                module = create_module(
                    connection,
                    title=payload.title,
                    parent_id=payload.parent_id,
                    instruction=payload.instruction,
                    ui_copy=payload.ui_copy.model_dump(),
                )
            except ServiceError as error:
                _handle_service_error(error)
            tree = get_module_tree(connection)
            stack = list(tree)
            while stack:
                node = stack.pop()
                if node["id"] == module["id"]:
                    return node
                stack.extend(node["children"])
        raise HTTPException(status_code=500, detail="Module creation did not return a created node.")

    @app.post("/api/quiz-sessions", response_model=QuizSessionOut)
    def quiz_sessions_create(
        payload: QuizSessionCreateIn,
        x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    ) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return create_quiz_session(
                    connection,
                    user_id=_require_user_id(x_user_id),
                    module_id=payload.module_id,
                    count=payload.count,
                )
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/quiz-sessions/{session_id}/items/{item_id}/submit", response_model=SubmitAnswerOut)
    def quiz_sessions_submit(
        session_id: int,
        item_id: int,
        payload: SubmitAnswerIn,
        x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    ) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return submit_answer(
                    connection,
                    user_id=_require_user_id(x_user_id),
                    session_id=session_id,
                    item_id=item_id,
                    answers=payload.answers,
                )
            except ServiceError as error:
                _handle_service_error(error)

    @app.get("/api/stats", response_model=StatsResponseOut)
    def stats(
        module_id: Optional[int] = None,
        review_only: bool = Query(default=False),
        x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    ) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return get_stats(
                    connection,
                    user_id=_require_user_id(x_user_id),
                    module_id=module_id,
                    review_only=review_only,
                )
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/questions", response_model=QuestionMutationOut)
    def questions_create(payload: QuestionDraftIn) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return create_question(connection, payload)
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/questions/{question_id}/revisions", response_model=QuestionMutationOut)
    def questions_revise(question_id: int, payload: QuestionRevisionIn) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                draft = QuestionDraftIn(**payload.model_dump(exclude={"reset_stats"}))
                return revise_question(connection, question_id, draft, reset_stats=payload.reset_stats)
            except ServiceError as error:
                _handle_service_error(error)

    @app.patch("/api/questions/{question_id}/review-flag", response_model=QuestionReviewFlagOut)
    def questions_review_flag(
        question_id: int,
        payload: QuestionReviewFlagIn,
        x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    ) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return set_question_review_flag(
                    connection,
                    user_id=_require_user_id(x_user_id),
                    question_id=question_id,
                    review_flag=payload.review_flag,
                )
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/question-import-sessions", response_model=QuestionImportSessionOut)
    def question_import_sessions_create(payload: CreateQuestionImportSessionIn) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return create_question_import_session(connection, module_id=payload.module_id, csv_text=payload.csv_text)
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/question-import-sessions/{session_id}/revalidate", response_model=QuestionImportSessionOut)
    def question_import_sessions_revalidate(session_id: int, payload: RevalidateQuestionImportSessionIn) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return revalidate_question_import_session(
                    connection,
                    session_id=session_id,
                    rows=[row.model_dump() for row in payload.rows],
                )
            except ServiceError as error:
                _handle_service_error(error)

    @app.delete("/api/question-import-sessions/{session_id}/rows/{row_number}", response_model=QuestionImportSessionOut)
    def question_import_sessions_discard_row(session_id: int, row_number: int) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return discard_question_import_session_row(connection, session_id=session_id, row_number=row_number)
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/question-import-sessions/{session_id}/commit", response_model=QuestionImportSessionOut)
    def question_import_sessions_commit(session_id: int) -> dict:
        with get_connection(app.state.database_url) as connection:
            try:
                return commit_question_import_session(connection, session_id=session_id)
            except ServiceError as error:
                _handle_service_error(error)

    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        def frontend_app(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            return FileResponse(FRONTEND_DIST_DIR / "index.html")

    return app


app = create_app()
