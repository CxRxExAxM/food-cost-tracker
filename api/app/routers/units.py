from fastapi import APIRouter, Query
from typing import Optional
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


@router.get("/grouped")
def list_units_grouped():
    """
    List all units grouped by unit_type.

    Returns units organized by type (weight, volume, count, etc.)
    for use in dropdown selectors.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM units ORDER BY unit_type, name")
        units = dicts_from_rows(cursor.fetchall())

        # Group by unit_type
        grouped = {}
        for unit in units:
            unit_type = unit.get("unit_type", "other")
            if unit_type not in grouped:
                grouped[unit_type] = []
            grouped[unit_type].append(unit)

        return {"groups": grouped, "all": units}
