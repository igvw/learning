from typing import Any

from ..database import DatabaseConnection, execute_insert_returning_id, utc_now
from .common import NotFoundError, ValidationError, slugify_title, title_from_slug


def ensure_module_exists(connection: DatabaseConnection, module_id: int | None) -> Any | None:
    if module_id is None:
        return None
    row = connection.execute(
        "SELECT id, slug, full_slug, instruction FROM modules WHERE id = ?",
        (module_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Module {module_id} was not found.")
    return row


def ensure_leaf_module(connection: DatabaseConnection, module_id: int) -> Any:
    module = ensure_module_exists(connection, module_id)
    child_count = connection.execute(
        "SELECT COUNT(*) AS child_count FROM modules WHERE parent_id = ?",
        (module_id,),
    ).fetchone()["child_count"]
    if child_count:
        raise ValidationError("Questions can only be added to leaf modules.")
    return module


def ensure_module_can_accept_children(connection: DatabaseConnection, module_id: int) -> Any:
    module = ensure_module_exists(connection, module_id)
    question_count = connection.execute(
        "SELECT COUNT(*) AS question_count FROM questions WHERE module_id = ?",
        (module_id,),
    ).fetchone()["question_count"]
    if question_count:
        raise ValidationError("Cannot add child modules under a module that already contains questions.")
    return module


def ensure_unique_module_slug(
    connection: DatabaseConnection,
    slug: str,
    parent_id: int | None,
    *,
    exclude_module_id: int | None = None,
) -> None:
    sibling_rows = connection.execute(
        "SELECT id, slug FROM modules WHERE parent_id IS ?",
        (parent_id,),
    ).fetchall()
    for row in sibling_rows:
        if exclude_module_id is not None and row["id"] == exclude_module_id:
            continue
        if row["slug"] == slug:
            raise ValidationError("A sibling module with this title already exists.")


def build_full_slug(connection: DatabaseConnection, slug: str, parent_id: int | None) -> str:
    if parent_id is None:
        return slug

    parent_row = ensure_module_exists(connection, parent_id)
    return f"{parent_row['full_slug']}/{slug}"


def create_module(
    connection: DatabaseConnection,
    *,
    title: str,
    parent_id: int | None,
    instruction: str,
) -> dict[str, Any]:
    if parent_id is not None:
        ensure_module_can_accept_children(connection, parent_id)
    slug = slugify_title(title)
    ensure_unique_module_slug(connection, slug, parent_id)
    full_slug = build_full_slug(connection, slug, parent_id)
    module_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO modules (parent_id, slug, full_slug, instruction, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (parent_id, slug, full_slug, instruction.strip(), utc_now()),
    )
    return {
        "id": module_id,
        "title": title_from_slug(slug),
        "slug": slug,
        "full_slug": full_slug,
        "instruction": instruction.strip(),
    }


def get_module_tree(connection: DatabaseConnection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, parent_id, slug, full_slug, instruction
        FROM modules
        ORDER BY full_slug
        """
    ).fetchall()

    nodes: dict[int, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []
    for row in rows:
        nodes[row["id"]] = {
            "id": row["id"],
            "title": title_from_slug(row["slug"]),
            "slug": row["slug"],
            "full_slug": row["full_slug"],
            "instruction": row["instruction"] or "",
            "children": [],
            "_parent_id": row["parent_id"],
        }

    for node in nodes.values():
        parent_id = node.pop("_parent_id")
        if parent_id is None:
            roots.append(node)
        else:
            nodes[parent_id]["children"].append(node)
    return roots


def get_scope_module_ids(connection: DatabaseConnection, module_id: int | None) -> list[int]:
    if module_id is None:
        rows = connection.execute("SELECT id FROM modules ORDER BY id").fetchall()
        return [row["id"] for row in rows]

    ensure_module_exists(connection, module_id)
    rows = connection.execute(
        """
        WITH RECURSIVE scope(id) AS (
            SELECT id FROM modules WHERE id = ?
            UNION ALL
            SELECT modules.id
            FROM modules
            JOIN scope ON modules.parent_id = scope.id
        )
        SELECT id FROM scope ORDER BY id
        """,
        (module_id,),
    ).fetchall()
    return [row["id"] for row in rows]


def list_users(connection: DatabaseConnection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, handle, display_name, created_at
        FROM users
        ORDER BY lower(display_name) ASC, id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_user(connection: DatabaseConnection, *, handle: str, display_name: str) -> dict[str, Any]:
    cleaned_handle = handle.strip()
    cleaned_display_name = display_name.strip()
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
        INSERT INTO users (handle, display_name, created_at)
        VALUES (?, ?, ?)
        """,
        (cleaned_handle, cleaned_display_name, created_at),
    )
    return {
        "id": user_id,
        "handle": cleaned_handle,
        "display_name": cleaned_display_name,
        "created_at": created_at,
    }


def ensure_user_exists(connection: DatabaseConnection, user_id: int) -> Any:
    row = connection.execute(
        """
        SELECT id, handle, display_name, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"User {user_id} was not found.")
    return row
