from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import get_connection, initialize_database
from .schemas import (
    CreateModuleIn,
    ModuleNodeOut,
    QuestionDraftIn,
    QuestionMutationOut,
    QuestionReviewFlagIn,
    QuestionReviewFlagOut,
    QuestionRevisionIn,
    QuizSessionCreateIn,
    QuizSessionOut,
    StatsResponseOut,
    SubmitAnswerIn,
    SubmitAnswerOut,
)
from .services import (
    NotFoundError,
    ServiceError,
    ValidationError,
    create_module,
    create_question,
    create_quiz_session,
    get_module_tree,
    get_stats,
    revise_question,
    set_question_review_flag,
    submit_answer,
    sync_seed_content,
)
from .settings import CONTENT_DIR, DEV_FRONTEND_ORIGIN, FRONTEND_DIST_DIR, resolve_db_path


def _handle_service_error(error: ServiceError) -> None:
    raise HTTPException(status_code=error.status_code, detail=str(error)) from error


def create_app(
    db_path: Optional[Union[str, Path]] = None,
    content_root: Optional[Union[str, Path]] = None,
) -> FastAPI:
    app = FastAPI(title="Learning App API")
    app.state.db_path = resolve_db_path(db_path)
    app.state.content_root = Path(content_root).resolve() if content_root else CONTENT_DIR

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[DEV_FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup() -> None:
        initialize_database(app.state.db_path)
        with get_connection(app.state.db_path) as connection:
            sync_seed_content(connection, app.state.content_root)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/modules/tree", response_model=list[ModuleNodeOut])
    def modules_tree() -> list[dict]:
        with get_connection(app.state.db_path) as connection:
            return get_module_tree(connection)

    @app.post("/api/modules", response_model=ModuleNodeOut)
    def modules_create(payload: CreateModuleIn) -> dict:
        with get_connection(app.state.db_path) as connection:
            try:
                module = create_module(
                    connection,
                    title=payload.title,
                    parent_id=payload.parent_id,
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
    def quiz_sessions_create(payload: QuizSessionCreateIn) -> dict:
        with get_connection(app.state.db_path) as connection:
            try:
                return create_quiz_session(connection, module_id=payload.module_id, count=payload.count)
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/quiz-sessions/{session_id}/items/{item_id}/submit", response_model=SubmitAnswerOut)
    def quiz_sessions_submit(session_id: int, item_id: int, payload: SubmitAnswerIn) -> dict:
        with get_connection(app.state.db_path) as connection:
            try:
                return submit_answer(connection, session_id=session_id, item_id=item_id, answers=payload.answers)
            except ServiceError as error:
                _handle_service_error(error)

    @app.get("/api/stats", response_model=StatsResponseOut)
    def stats(module_id: Optional[int] = None, review_only: bool = Query(default=False)) -> dict:
        with get_connection(app.state.db_path) as connection:
            try:
                return get_stats(connection, module_id=module_id, review_only=review_only)
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/questions", response_model=QuestionMutationOut)
    def questions_create(payload: QuestionDraftIn) -> dict:
        with get_connection(app.state.db_path) as connection:
            try:
                return create_question(connection, payload)
            except ServiceError as error:
                _handle_service_error(error)

    @app.post("/api/questions/{question_id}/revisions", response_model=QuestionMutationOut)
    def questions_revise(question_id: int, payload: QuestionRevisionIn) -> dict:
        with get_connection(app.state.db_path) as connection:
            try:
                draft = QuestionDraftIn(**payload.model_dump(exclude={"reset_stats"}))
                return revise_question(connection, question_id, draft, reset_stats=payload.reset_stats)
            except ServiceError as error:
                _handle_service_error(error)

    @app.patch("/api/questions/{question_id}/review-flag", response_model=QuestionReviewFlagOut)
    def questions_review_flag(question_id: int, payload: QuestionReviewFlagIn) -> dict:
        with get_connection(app.state.db_path) as connection:
            try:
                return set_question_review_flag(connection, question_id, payload.review_flag)
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
