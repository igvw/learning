from fastapi import APIRouter, Depends

from ...database import DatabaseConnection
from ...schemas import HealthOut
from ...services import admin_exists
from ...settings import instance_key
from ..dependencies import database_connection


router = APIRouter()


@router.get("/api/health", response_model=HealthOut)
def health(connection: DatabaseConnection = Depends(database_connection)) -> dict[str, str | bool]:
    return {
        "status": "ok",
        "instance_key": instance_key(),
        "bootstrap_required": not admin_exists(connection),
    }
