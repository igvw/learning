from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.dependencies import service_error_response
from .api.routers import ALL_ROUTERS
from .database import get_connection, initialize_database
from .services import ServiceError, bootstrap_admin_from_environment, sync_seed_content
from .settings import CONTENT_DIR, FRONTEND_DIST_DIR, cors_origins, resolve_database_url, seed_on_boot


def create_app(
    database_url: str | Path | None = None,
    content_root: str | Path | None = None,
) -> FastAPI:
    explicit_database_url = None
    if database_url is not None:
        cleaned_database_url = str(database_url).strip()
        if cleaned_database_url:
            explicit_database_url = cleaned_database_url

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_database_url = resolve_database_url(app.state.database_url_input)
        app.state.database_url = resolved_database_url
        initialize_database(resolved_database_url)
        with get_connection(resolved_database_url) as connection:
            bootstrap_admin_from_environment(connection)
            if seed_on_boot():
                sync_seed_content(connection, app.state.content_root)
        yield

    app = FastAPI(title="Learning App API", lifespan=lifespan)
    app.state.database_url_input = explicit_database_url
    app.state.database_url = explicit_database_url
    app.state.content_root = Path(content_root).resolve() if content_root else CONTENT_DIR
    app.add_exception_handler(ServiceError, service_error_response)

    allowed_origins = cors_origins()
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    for router in ALL_ROUTERS:
        app.include_router(router)

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
