from fastapi import APIRouter
from ..database import get_db, dicts_from_rows
from ..schemas import Distributor

router = APIRouter(prefix="/distributors", tags=["distributors"])


@router.get("", response_model=list[Distributor])
def list_distributors():
    """List all distributors."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM distributors WHERE is_active = 1 ORDER BY name")
        distributors = dicts_from_rows(cursor.fetchall())
        return distributors
