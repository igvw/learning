import json
from dataclasses import dataclass
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from ..database import DatabaseConnection, execute_insert_returning_id, utc_now
from .auth import Actor, create_user_account
from .errors import NotFoundError, ValidationError
from .questions import qml_text_from_storage
from .text import slugify_title, title_from_slug


def _module_visible_to_actor(row: Any, actor: Actor | None) -> bool:
    if actor is None or actor.role == "admin":
        return True
    if bool(row["admin_verified"]):
        return True
    return (
        actor.user_id is not None
        and row["created_by_user_id"] == actor.user_id
        and row["moderation_status"] == "pending"
    )


def _active_module_rows(connection: DatabaseConnection) -> list[Any]:
    return connection.execute(
        """
        SELECT
            modules.id,
            modules.parent_id,
            modules.slug,
            modules.full_slug,
            modules.instruction,
            modules.created_by_user_id,
            modules.admin_verified,
            modules.moderation_status,
            users.display_name AS creator_display_name
        FROM modules
        LEFT JOIN users ON users.id = modules.created_by_user_id
        WHERE modules.moderation_status <> 'rejected'
        ORDER BY modules.full_slug ASC
        """
    ).fetchall()


@dataclass(slots=True)
class ContentExportPayload:
    filename: str
    media_type: str
    content: bytes


def ensure_module_exists(connection: DatabaseConnection, module_id: int | None, *, actor: Actor | None = None) -> Any | None:
    if module_id is None:
        return None
    row = connection.execute(
        """
        SELECT
            id,
            parent_id,
            slug,
            full_slug,
            instruction,
            created_by_user_id,
            admin_verified,
            moderation_status
        FROM modules
        WHERE id = ?
        """,
        (module_id,),
    ).fetchone()
    if row is None or not _module_visible_to_actor(row, actor):
        raise NotFoundError(f"Module {module_id} was not found.")
    return row


def ensure_leaf_module(connection: DatabaseConnection, module_id: int, *, actor: Actor | None = None) -> Any:
    module = ensure_module_exists(connection, module_id, actor=actor)
    child_count = connection.execute(
        "SELECT COUNT(*) AS child_count FROM modules WHERE parent_id = ? AND moderation_status <> 'rejected'",
        (module_id,),
    ).fetchone()["child_count"]
    if child_count:
        raise ValidationError("Questions can only be added to leaf modules.")
    return module


def ensure_module_can_accept_children(connection: DatabaseConnection, module_id: int, *, actor: Actor | None = None) -> Any:
    module = ensure_module_exists(connection, module_id, actor=actor)
    question_count = connection.execute(
        "SELECT COUNT(*) AS question_count FROM questions WHERE module_id = ? AND enabled = 1 AND moderation_status <> 'rejected'",
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
    actor: Actor | None = None,
    exclude_module_id: int | None = None,
) -> None:
    full_slug = build_full_slug(connection, slug, parent_id)
    verified_conflict = connection.execute(
        """
        SELECT id
        FROM modules
        WHERE lower(full_slug) = lower(?)
          AND admin_verified = 1
          AND moderation_status <> 'rejected'
        """,
        (full_slug,),
    ).fetchone()
    if verified_conflict is not None and verified_conflict["id"] != exclude_module_id:
        raise ValidationError("A module with this path already exists.")

    if actor is None or actor.role == "admin" or actor.user_id is None:
        return

    own_pending_conflict = connection.execute(
        """
        SELECT id
        FROM modules
        WHERE lower(full_slug) = lower(?)
          AND admin_verified = 0
          AND created_by_user_id = ?
          AND moderation_status = 'pending'
        """,
        (full_slug, actor.user_id),
    ).fetchone()
    if own_pending_conflict is not None and own_pending_conflict["id"] != exclude_module_id:
        raise ValidationError("You already have a pending module at this path.")


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
    actor: Actor | None = None,
) -> dict[str, Any]:
    if parent_id is not None:
        ensure_module_can_accept_children(connection, parent_id, actor=actor)
    slug = slugify_title(title)
    ensure_unique_module_slug(connection, slug, parent_id, actor=actor)
    full_slug = build_full_slug(connection, slug, parent_id)
    is_verified = actor is None or actor.role == "admin"
    moderation_status = "verified" if is_verified else "pending"
    module_id = execute_insert_returning_id(
        connection,
        """
        INSERT INTO modules (
            parent_id,
            slug,
            full_slug,
            instruction,
            created_at,
            created_by_user_id,
            admin_verified,
            moderation_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            parent_id,
            slug,
            full_slug,
            instruction.strip(),
            utc_now(),
            actor.user_id if actor and actor.user_id is not None else None,
            1 if is_verified else 0,
            moderation_status,
        ),
    )
    return {
        "id": module_id,
        "title": title_from_slug(slug),
        "slug": slug,
        "full_slug": full_slug,
        "instruction": instruction.strip(),
        "admin_verified": is_verified,
        "moderation_status": moderation_status,
        "created_by_user_id": actor.user_id if actor and actor.user_id is not None else None,
        "creator_display_name": actor.display_name if actor and actor.user_id is not None else None,
    }


def update_module(
    connection: DatabaseConnection,
    *,
    module_id: int,
    title: str,
    instruction: str,
    actor: Actor | None = None,
) -> dict[str, Any]:
    module = ensure_module_exists(connection, module_id, actor=actor)
    if actor is not None and actor.role != "admin":
        if bool(module["admin_verified"]):
            raise ValidationError("Only admins can edit verified modules.")
        if actor.user_id is None or module["created_by_user_id"] != actor.user_id:
            raise ValidationError("You can only edit your own pending modules.")
    child_count = connection.execute(
        "SELECT COUNT(*) AS child_count FROM modules WHERE parent_id = ? AND moderation_status <> 'rejected'",
        (module_id,),
    ).fetchone()["child_count"]
    if child_count:
        raise ValidationError("Only leaf modules can be renamed.")

    slug = slugify_title(title)
    parent_row = connection.execute(
        "SELECT parent_id FROM modules WHERE id = ?",
        (module_id,),
    ).fetchone()
    parent_id = parent_row["parent_id"]
    ensure_unique_module_slug(connection, slug, parent_id, actor=actor, exclude_module_id=module_id)
    full_slug = build_full_slug(connection, slug, parent_id)
    cleaned_instruction = instruction.strip()
    connection.execute(
        """
        UPDATE modules
        SET
            slug = ?,
            full_slug = ?,
            instruction = ?,
            moderation_status = CASE WHEN admin_verified = 1 THEN moderation_status ELSE 'pending' END
        WHERE id = ?
        """,
        (slug, full_slug, cleaned_instruction, module_id),
    )
    return {
        "id": module_id,
        "title": title_from_slug(slug),
        "slug": slug,
        "full_slug": full_slug,
        "instruction": cleaned_instruction,
        "admin_verified": bool(module["admin_verified"]),
        "moderation_status": "verified" if bool(module["admin_verified"]) else "pending",
        "created_by_user_id": module["created_by_user_id"],
        "creator_display_name": actor.display_name if actor and actor.user_id == module["created_by_user_id"] else None,
    }


def _module_subtree_rows(connection: DatabaseConnection, module_id: int) -> list[Any]:
    return connection.execute(
        """
        WITH RECURSIVE module_tree AS (
            SELECT id, parent_id, full_slug
            FROM modules
            WHERE id = ?
            UNION ALL
            SELECT child.id, child.parent_id, child.full_slug
            FROM modules AS child
            JOIN module_tree AS parent ON child.parent_id = parent.id
        )
        SELECT id, full_slug
        FROM module_tree
        ORDER BY full_slug ASC
        """,
        (module_id,),
    ).fetchall()


def _delete_module_subtree(
    connection: DatabaseConnection,
    *,
    module_id: int,
    safety_message: str,
) -> None:
    subtree_rows = _module_subtree_rows(connection, module_id)
    if not subtree_rows:
        raise NotFoundError(f"Module {module_id} was not found.")

    module_ids = [int(row["id"]) for row in subtree_rows]
    placeholders = ", ".join("?" for _ in module_ids)
    question_rows = connection.execute(
        f"""
        SELECT id
        FROM questions
        WHERE module_id IN ({placeholders})
        """,
        tuple(module_ids),
    ).fetchall()
    question_ids = [int(row["id"]) for row in question_rows]
    if question_ids:
        question_placeholders = ", ".join("?" for _ in question_ids)
        attempt_count = connection.execute(
            f"""
            SELECT COUNT(*) AS attempt_count
            FROM attempts
            WHERE question_id IN ({question_placeholders})
            """,
            tuple(question_ids),
        ).fetchone()["attempt_count"]
        if attempt_count:
            raise ValidationError(safety_message)

        active_item_count = connection.execute(
            f"""
            SELECT COUNT(*) AS active_item_count
            FROM quiz_session_items AS items
            JOIN quiz_sessions AS sessions ON sessions.id = items.session_id
            WHERE items.question_id IN ({question_placeholders})
              AND sessions.completed_at IS NULL
            """,
            tuple(question_ids),
        ).fetchone()["active_item_count"]
        if active_item_count:
            raise ValidationError(safety_message)

    connection.execute(
        f"DELETE FROM modules WHERE id IN ({placeholders})",
        tuple(module_ids),
    )


def delete_module(connection: DatabaseConnection, *, module_id: int) -> None:
    ensure_module_exists(connection, module_id)
    _delete_module_subtree(
        connection,
        module_id=module_id,
        safety_message="Modules with attempted questions or active quiz sessions cannot be deleted.",
    )


def get_module_tree(connection: DatabaseConnection, actor: Actor | None = None) -> list[dict[str, Any]]:
    rows = [row for row in _active_module_rows(connection) if _module_visible_to_actor(row, actor)]

    nodes: dict[int, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []
    for row in rows:
        nodes[row["id"]] = {
            "id": row["id"],
            "title": title_from_slug(row["slug"]),
            "slug": row["slug"],
            "full_slug": row["full_slug"],
            "instruction": row["instruction"] or "",
            "admin_verified": bool(row["admin_verified"]),
            "moderation_status": row["moderation_status"],
            "created_by_user_id": row["created_by_user_id"],
            "creator_display_name": row["creator_display_name"],
            "children": [],
            "_parent_id": row["parent_id"],
        }

    for node in nodes.values():
        parent_id = node.pop("_parent_id")
        if parent_id is None or parent_id not in nodes:
            roots.append(node)
        else:
            nodes[parent_id]["children"].append(node)
    return roots


def get_scope_module_ids(connection: DatabaseConnection, module_id: int | None, *, actor: Actor | None = None) -> list[int]:
    visible_rows = [row for row in _active_module_rows(connection) if _module_visible_to_actor(row, actor)]
    children_by_parent: dict[int | None, list[int]] = {}
    for row in visible_rows:
        children_by_parent.setdefault(row["parent_id"], []).append(int(row["id"]))

    if module_id is None:
        return [int(row["id"]) for row in visible_rows]

    ensure_module_exists(connection, module_id, actor=actor)
    scope_ids: list[int] = []
    stack = [module_id]
    while stack:
        current_id = stack.pop()
        scope_ids.append(current_id)
        stack.extend(children_by_parent.get(current_id, []))
    return sorted(scope_ids)


def _verified_module_rows(connection: DatabaseConnection) -> list[Any]:
    return [row for row in _active_module_rows(connection) if bool(row["admin_verified"]) and row["moderation_status"] == "verified"]


def _module_yaml_text(instruction: str) -> str:
    cleaned_instruction = instruction.strip()
    if not cleaned_instruction:
        return 'instruction: ""\n'
    if "\n" not in cleaned_instruction:
        return f"instruction: {json.dumps(cleaned_instruction, ensure_ascii=False)}\n"

    indented_lines = "\n".join(f"  {line}" if line else "  " for line in cleaned_instruction.splitlines())
    return f"instruction: |\n{indented_lines}\n"


def _questions_qml_text(lines: list[str]) -> bytes:
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def export_verified_content_archive(connection: DatabaseConnection) -> ContentExportPayload:
    verified_rows = _verified_module_rows(connection)
    children_by_parent: dict[int | None, list[int]] = {}
    rows_by_id: dict[int, Any] = {}
    for row in verified_rows:
        module_id = int(row["id"])
        rows_by_id[module_id] = row
        children_by_parent.setdefault(row["parent_id"], []).append(module_id)

    leaf_ids = [module_id for module_id in rows_by_id if not children_by_parent.get(module_id)]
    questions_by_module = {module_id: [] for module_id in leaf_ids}
    if leaf_ids:
        placeholders = ",".join("?" for _ in leaf_ids)
        question_rows = connection.execute(
            f"""
            SELECT module_id, question_type, prompt, type_config_json, bundles.variants_json
            FROM questions
            LEFT JOIN question_bundle_summaries AS bundles ON bundles.question_id = questions.id
            WHERE module_id IN ({placeholders})
              AND admin_verified = 1
              AND enabled = 1
              AND moderation_status = 'verified'
            ORDER BY module_id ASC, rank ASC, id ASC
            """,
            tuple(leaf_ids),
        ).fetchall()
        for row in question_rows:
            type_config = json.loads(row["type_config_json"])
            questions_by_module[int(row["module_id"])].append(
                qml_text_from_storage(str(row["question_type"]), str(row["prompt"]), type_config, row["variants_json"])
            )

    archive_buffer = BytesIO()
    with ZipFile(archive_buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for row in verified_rows:
            full_slug = str(row["full_slug"])
            archive.writestr(
                f"modules-export/content/modules/{full_slug}/module.yaml",
                _module_yaml_text(str(row["instruction"] or "")),
            )

        for module_id in leaf_ids:
            full_slug = str(rows_by_id[module_id]["full_slug"])
            archive.writestr(
                f"modules-export/content/modules/{full_slug}/questions.qml",
                _questions_qml_text(questions_by_module.get(module_id, [])),
            )

    return ContentExportPayload(
        filename="modules-export.zip",
        media_type="application/zip",
        content=archive_buffer.getvalue(),
    )


def list_users(connection: DatabaseConnection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, handle, display_name, role, created_at
        FROM users
        ORDER BY lower(display_name) ASC, id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_user(
    connection: DatabaseConnection,
    *,
    handle: str,
    display_name: str,
    role: str,
    password: str,
) -> dict[str, Any]:
    return create_user_account(
        connection,
        handle=handle,
        display_name=display_name,
        role=role,
        password=password,
    )


def ensure_user_exists(connection: DatabaseConnection, user_id: int) -> Any:
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
    return row
