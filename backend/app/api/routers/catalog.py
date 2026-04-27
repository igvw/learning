from fastapi import APIRouter, Depends, HTTPException, Response

from ...database import DatabaseConnection
from ...schemas import CreateModuleIn, ModuleNodeOut, UpdateModuleIn
from ...services import Actor, create_module, export_verified_content_archive, get_module_tree, update_module
from ..dependencies import database_connection, require_actor, require_admin_actor


router = APIRouter()


def _find_module_node(module_tree: list[dict], module_id: int) -> dict | None:
    stack = list(module_tree)
    while stack:
        node = stack.pop()
        if node["id"] == module_id:
            return node
        stack.extend(node["children"])
    return None


@router.get("/api/modules/tree", response_model=list[ModuleNodeOut])
def modules_tree(
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> list[dict]:
    return get_module_tree(connection, actor=actor)


@router.post("/api/modules", response_model=ModuleNodeOut)
def modules_create(
    payload: CreateModuleIn,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    module = create_module(
        connection,
        title=payload.title,
        parent_id=payload.parent_id,
        instruction=payload.instruction,
        actor=actor,
    )
    created_node = _find_module_node(get_module_tree(connection, actor=actor), module["id"])
    if created_node is not None:
        return created_node
    raise HTTPException(status_code=500, detail="Module creation did not return a created node.")


@router.patch("/api/modules/{module_id}", response_model=ModuleNodeOut)
def modules_update(
    module_id: int,
    payload: UpdateModuleIn,
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    module = update_module(
        connection,
        module_id=module_id,
        title=payload.title,
        instruction=payload.instruction,
        actor=actor,
    )
    updated_node = _find_module_node(get_module_tree(connection, actor=actor), module["id"])
    if updated_node is not None:
        return updated_node
    raise HTTPException(status_code=500, detail="Module update did not return an updated node.")


@router.get("/api/modules/export")
def modules_export(
    _: Actor = Depends(require_admin_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> Response:
    payload = export_verified_content_archive(connection)
    return Response(
        content=payload.content,
        media_type=payload.media_type,
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )
