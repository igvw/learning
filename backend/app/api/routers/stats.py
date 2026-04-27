from fastapi import APIRouter, Depends, Query

from ...database import DatabaseConnection
from ...schemas import StatsResponseOut
from ...services import Actor, get_stats
from ..dependencies import database_connection, require_actor


router = APIRouter()


@router.get("/api/stats", response_model=StatsResponseOut)
def stats(
    module_id: int | None = None,
    review_only: bool = Query(default=False),
    actor: Actor = Depends(require_actor),
    connection: DatabaseConnection = Depends(database_connection),
) -> dict:
    return get_stats(
        connection,
        user_id=int(actor.user_id),
        module_id=module_id,
        review_only=review_only,
        actor=actor,
    )
