from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from ..database import DatabaseConnection, get_connection
from ..services import Actor, ServiceError, get_actor_from_token
from ..settings import auth_cookie_name, auth_cookie_secure, resolve_database_url


def database_connection(request: Request) -> Iterator[DatabaseConnection]:
    database_url = request.app.state.database_url
    if database_url is None:
        database_url = resolve_database_url(request.app.state.database_url_input)
        request.app.state.database_url = database_url
    with get_connection(database_url) as connection:
        yield connection


def service_error_response(_: Request, error: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": str(error)})


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=auth_cookie_name(),
        value=token,
        httponly=True,
        secure=auth_cookie_secure(),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=auth_cookie_name(),
        path="/",
        secure=auth_cookie_secure(),
        samesite="lax",
    )


def optional_actor(
    request: Request,
    connection: DatabaseConnection = Depends(database_connection),
) -> Actor | None:
    return get_actor_from_token(connection, request.cookies.get(auth_cookie_name()))


def require_actor(actor: Actor | None = Depends(optional_actor)) -> Actor:
    if actor is None:
        raise HTTPException(status_code=401, detail="Authentication is required.")
    return actor


def require_admin_actor(actor: Actor = Depends(require_actor)) -> Actor:
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access is required.")
    return actor
