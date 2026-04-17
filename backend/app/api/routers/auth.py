from fastapi import APIRouter, Depends, Request, Response

from ...database import DatabaseConnection
from ...settings import auth_cookie_name
from ...schemas import AuthActorOut, AuthBootstrapAdminIn, AuthLoginIn, UserCreateIn, UserOut, UserPasswordUpdateIn, UserRoleUpdateIn
from ...services import (
    Actor,
    bootstrap_admin,
    create_demo_session,
    create_user,
    list_users,
    login_user,
    logout_session,
    update_user_password,
    update_user_role,
)
from ..dependencies import (
    clear_session_cookie,
    database_connection,
    require_actor,
    require_admin_actor,
    set_session_cookie,
)


router = APIRouter()


@router.post("/api/auth/bootstrap-admin", response_model=AuthActorOut)
def auth_bootstrap_admin(
    payload: AuthBootstrapAdminIn,
    response: Response,
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    created = bootstrap_admin(
        connection,
        handle=payload.handle,
        display_name=payload.display_name,
        password=payload.password,
    )
    actor, token = login_user(connection, handle=created["handle"], password=payload.password)
    set_session_cookie(response, token)
    return actor


@router.post("/api/auth/login", response_model=AuthActorOut)
def auth_login(
    payload: AuthLoginIn,
    response: Response,
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    actor, token = login_user(connection, handle=payload.handle, password=payload.password)
    set_session_cookie(response, token)
    return actor


@router.post("/api/auth/demo-session", response_model=AuthActorOut)
def auth_demo_session(response: Response) -> dict:
    actor, token = create_demo_session()
    set_session_cookie(response, token)
    return actor


@router.post("/api/auth/logout", response_model=AuthActorOut | None)
def auth_logout(
    request: Request,
    response: Response,
    connection: DatabaseConnection = Depends(database_connection),
) -> None:
    logout_session(connection, request.cookies.get(auth_cookie_name()))
    clear_session_cookie(response)
    return None


@router.get("/api/auth/me", response_model=AuthActorOut)
def auth_me(actor: Actor = Depends(require_actor)) -> dict:
    return {
        "id": actor.user_id,
        "handle": actor.handle,
        "display_name": actor.display_name,
        "role": actor.role,
        "is_demo": actor.is_demo,
        "created_at": actor.created_at,
    }


@router.get("/api/users", response_model=list[UserOut])
def users_list(
    _: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> list[dict]:
    return list_users(connection)


@router.post("/api/users", response_model=UserOut)
def users_create(
    payload: UserCreateIn,
    _: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return create_user(
        connection,
        handle=payload.handle,
        display_name=payload.display_name,
        role=payload.role,
        password=payload.password,
    )


@router.post("/api/users/{user_id}/password")
def users_password_update(
    user_id: int,
    payload: UserPasswordUpdateIn,
    _: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return update_user_password(connection, user_id=user_id, password=payload.password)


@router.patch("/api/users/{user_id}", response_model=UserOut)
def users_update(
    user_id: int,
    payload: UserRoleUpdateIn,
    _: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return update_user_role(connection, user_id=user_id, role=payload.role)
