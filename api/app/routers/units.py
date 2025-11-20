from fastapi import APIRouter
from ..database import get_db, dicts_from_rows
from ..schemas import Unit

router = APIRouter(prefix="/units", tags=["units"])


@router.get("", response_model=list[Unit])
def list_units():
    """List all units of measure."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM units ORDER BY name")
        units = dicts_from_rows(cursor.fetchall())
        return units
