import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import Distributor
from ..auth import get_current_user

router = APIRouter(prefix="/distributors", tags=["distributors"])


class DistributorCreate(BaseModel):
    """Create a new vendor/distributor.

    `code` is optional; if omitted it is derived (slugified) from the name.
    Distributors are global reference data shared across organizations.
    """
    name: str
    code: Optional[str] = None


def _slugify(value: str) -> str:
    """Lowercase, strip to alphanumerics. Used to derive a vendor code."""
    slug = re.sub(r'[^a-z0-9]+', '', value.lower())
    return slug or 'vendor'


@router.get("", response_model=list[Distributor])
def list_distributors():
    """List all active distributors."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM distributors WHERE is_active = 1 ORDER BY name")
        distributors = dicts_from_rows(cursor.fetchall())
        return distributors


@router.post("", response_model=Distributor, status_code=201)
def create_distributor(payload: DistributorCreate, current_user: dict = Depends(get_current_user)):
    """Create a new vendor/distributor.

    Lets users add vendors (external or internal/housemade) that weren't part
    of the original seed, so products and prices can be entered before an
    invoice import exists. The `name` carries a UNIQUE constraint (global),
    so duplicate names are rejected; `code` is auto-generated and de-duped.
    """
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Vendor name is required")

    with get_db() as conn:
        cursor = conn.cursor()

        # Distributors are global; reject duplicate names case-insensitively.
        cursor.execute("SELECT id FROM distributors WHERE LOWER(name) = LOWER(%s)", (name,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"A vendor named '{name}' already exists")

        # Derive a unique code from the supplied code (or the name), appending a
        # numeric suffix on collision since `code` is also UNIQUE.
        base_code = _slugify(payload.code or name)
        code = base_code
        suffix = 1
        while True:
            cursor.execute("SELECT id FROM distributors WHERE code = %s", (code,))
            if not cursor.fetchone():
                break
            suffix += 1
            code = f"{base_code}{suffix}"

        cursor.execute("""
            INSERT INTO distributors (name, code, is_active)
            VALUES (%s, %s, 1)
            RETURNING id, name, code, is_active
        """, (name, code))
        distributor = dict_from_row(cursor.fetchone())
        conn.commit()

        return distributor
