import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ..database import DatabaseConnection, execute_insert_returning_id, utc_now
from ..settings import auth_session_ttl_seconds, bootstrap_admin_credentials, demo_session_ttl_seconds
from .errors import NotFoundError, ValidationError
from .passwords import hash_password, verify_password_and_update
_DEMO_SESSIONS: dict[str, dict[str, Any]] = {}


@dataclass(slots=True)
class Actor:
    user_id: int | None
    handle: str
    display_name: str
    role: str
    is_demo: bool = False
    created_at: str | None = None


def actor_to_dict(actor: Actor) -> dict[str, Any]:
    return {
        "id": actor.user_id,
        "handle": actor.handle,
        "display_name": actor.display_name,
        "role": actor.role,
        "is_demo": actor.is_demo,
        "created_at": actor.created_at,
    }


def admin_exists(connection: DatabaseConnection) -> bool:
    row = connection.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    return row is not None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _future_timestamp(seconds: int) -> str:
    return (datetime.fromisoformat(utc_now()) + timedelta(seconds=seconds)).isoformat()


def create_user_account(
    connection: DatabaseConnection,
    *,
    handle: str,
    display_name: str,
    role: str,
    password: str,
) -> dict[str, Any]:
    cleaned_handle = handle.strip()
    cleaned_display_name = display_name.strip()
    cleaned_role = role.strip().lower()
    if cleaned_role not in {"admin", "user"}:
        raise ValidationError("User role must be admin or user.")
    if not cleaned_handle:
        raise ValidationError("User handle is required.")
    if not cleaned_display_name:
        raise ValidationError("Display name is required.")

    existing = connection.execute(
        "SELECT id FROM users WHERE lower(handle) = lower(?)",
        (cleaned_handle,),
    ).fetchone()
    if existing is not None:
        raise ValidationError("User handle already exists.")

    created_at = utc_now()
    user_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO users (handle, display_name, role, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cleaned_handle, cleaned_display_name, cleaned_role, hash_password(password), created_at),
    )
    return {
        "id": user_id,
        "handle": cleaned_handle,
        "display_name": cleaned_display_name,
        "role": cleaned_role,
        "created_at": created_at,
    }


def bootstrap_admin(
    connection: DatabaseConnection,
    *,
    handle: str,
    display_name: str,
    password: str,
) -> dict[str, Any]:
    if admin_exists(connection):
        raise ValidationError("Admin bootstrap is no longer available.")
    return create_user_account(
        connection,
        handle=handle,
        display_name=display_name,
        role="admin",
        password=password,
    )


def bootstrap_admin_from_environment(connection: DatabaseConnection) -> dict[str, Any] | None:
    if admin_exists(connection):
        return None
    credentials = bootstrap_admin_credentials()
    if credentials is None:
        return None
    handle, display_name, password = credentials
    return bootstrap_admin(
        connection,
        handle=handle,
        display_name=display_name,
        password=password,
    )


def update_user_password(connection: DatabaseConnection, *, user_id: int, password: str) -> dict[str, Any]:
    row = connection.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"User {user_id} was not found.")
    password_hash = hash_password(password)
    connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    return {"user_id": user_id}


def update_user_role(connection: DatabaseConnection, *, user_id: int, role: str) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT id, handle, display_name, role, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"User {user_id} was not found.")

    cleaned_role = role.strip().lower()
    if cleaned_role not in {"admin", "user"}:
        raise ValidationError("User role must be admin or user.")

    current_role = row["role"]
    if current_role == cleaned_role:
        return {
            "id": int(row["id"]),
            "handle": row["handle"],
            "display_name": row["display_name"],
            "role": current_role,
            "created_at": row["created_at"],
        }

    if current_role == "admin" and cleaned_role != "admin":
        admin_count = connection.execute("SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin'").fetchone()
        if int(admin_count["admin_count"]) <= 1:
            raise ValidationError("At least one admin account must remain.")

    connection.execute("UPDATE users SET role = ? WHERE id = ?", (cleaned_role, user_id))
    return {
        "id": int(row["id"]),
        "handle": row["handle"],
        "display_name": row["display_name"],
        "role": cleaned_role,
        "created_at": row["created_at"],
    }


def _actor_from_user_row(row: Any) -> Actor:
    return Actor(
        user_id=int(row["id"]),
        handle=row["handle"],
        display_name=row["display_name"],
        role=row["role"],
        is_demo=False,
        created_at=row["created_at"],
    )


def _delete_expired_sessions(connection: DatabaseConnection) -> None:
    connection.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (utc_now(),))


def create_session(connection: DatabaseConnection, *, user_id: int) -> str:
    _delete_expired_sessions(connection)
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    created_at = utc_now()
    expires_at = _future_timestamp(auth_session_ttl_seconds())
    connection.execute(
        """
        INSERT INTO auth_sessions (user_id, token_hash, created_at, expires_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, token_hash, created_at, expires_at, created_at),
    )
    return token


def login_user(connection: DatabaseConnection, *, handle: str, password: str) -> tuple[dict[str, Any], str]:
    row = connection.execute(
        """
        SELECT id, handle, display_name, role, password_hash, created_at
        FROM users
        WHERE lower(handle) = lower(?)
        """,
        (handle.strip(),),
    ).fetchone()
    if row is None:
        raise ValidationError("Invalid handle or password.")
    valid_password, updated_hash = verify_password_and_update(password, row["password_hash"])
    if not valid_password:
        raise ValidationError("Invalid handle or password.")
    if updated_hash is not None:
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (updated_hash, int(row["id"])),
        )
    actor = _actor_from_user_row(row)
    token = create_session(connection, user_id=int(row["id"]))
    return actor_to_dict(actor), token


def _cleanup_demo_sessions() -> None:
    now = utc_now()
    expired = [token_hash for token_hash, session in _DEMO_SESSIONS.items() if session["expires_at"] <= now]
    for token_hash in expired:
        _DEMO_SESSIONS.pop(token_hash, None)


def create_demo_session() -> tuple[dict[str, Any], str]:
    _cleanup_demo_sessions()
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    created_at = utc_now()
    expires_at = _future_timestamp(demo_session_ttl_seconds())
    actor = Actor(
        user_id=None,
        handle="demo",
        display_name="Demo",
        role="demo",
        is_demo=True,
        created_at=created_at,
    )
    _DEMO_SESSIONS[token_hash] = {
        "actor": actor_to_dict(actor),
        "created_at": created_at,
        "expires_at": expires_at,
    }
    return actor_to_dict(actor), token


def get_actor_from_token(connection: DatabaseConnection, token: str | None) -> Actor | None:
    if not token:
        return None

    token_hash = _hash_token(token)
    _cleanup_demo_sessions()
    demo_session = _DEMO_SESSIONS.get(token_hash)
    if demo_session is not None:
        actor_payload = demo_session["actor"]
        return Actor(
            user_id=actor_payload["id"],
            handle=actor_payload["handle"],
            display_name=actor_payload["display_name"],
            role=actor_payload["role"],
            is_demo=True,
            created_at=actor_payload.get("created_at"),
        )

    _delete_expired_sessions(connection)
    row = connection.execute(
        """
        SELECT
            users.id,
            users.handle,
            users.display_name,
            users.role,
            users.created_at
        FROM auth_sessions
        JOIN users ON users.id = auth_sessions.user_id
        WHERE auth_sessions.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()
    if row is None:
        return None
    connection.execute(
        "UPDATE auth_sessions SET last_seen_at = ? WHERE token_hash = ?",
        (utc_now(), token_hash),
    )
    return _actor_from_user_row(row)


def logout_session(connection: DatabaseConnection, token: str | None) -> None:
    if not token:
        return
    token_hash = _hash_token(token)
    _DEMO_SESSIONS.pop(token_hash, None)
    connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
