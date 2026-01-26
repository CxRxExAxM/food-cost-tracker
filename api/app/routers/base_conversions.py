"""Base Conversions API Router

CRUD operations for base unit conversions.
Base conversions are standard unit-to-unit conversions (e.g., OZ → LB, GAL → QT)
that apply organization-wide or outlet-specific.

System defaults (organization_id = NULL) are seeded automatically and apply
to all organizations. Organizations can override with their own conversions,
and outlets can further customize.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import get_current_user, check_outlet_access

router = APIRouter(prefix="/base-conversions", tags=["base-conversions"])


# ============================================
# Pydantic Models
# ============================================

class BaseConversionCreate(BaseModel):
    """Create a new base conversion."""
    from_unit_id: int
    to_unit_id: int
    conversion_factor: float
    outlet_id: Optional[int] = None  # NULL = org-wide
    notes: Optional[str] = None


class BaseConversionUpdate(BaseModel):
    """Update an existing base conversion."""
    conversion_factor: Optional[float] = None
    notes: Optional[str] = None


# ============================================
# Endpoints
# ============================================

@router.get("")
def list_base_conversions(
    outlet_id: Optional[int] = None,
    from_unit_id: Optional[int] = None,
    to_unit_id: Optional[int] = None,
    include_system: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    List base conversions with optional filtering.

    Returns conversions in priority order:
    1. Outlet-specific (if outlet_id provided)
    2. Organization-wide
    3. System defaults (if include_system=True)

    - **outlet_id**: Filter by specific outlet
    - **from_unit_id**: Filter by source unit
    - **to_unit_id**: Filter by target unit
    - **include_system**: Include system defaults (default: True)
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        # Build WHERE clause
        where_clauses = ["bc.is_active = 1"]
        params = []

        # Include: system defaults + org-wide + outlet-specific
        org_filter_parts = []
        if include_system:
            org_filter_parts.append("bc.organization_id IS NULL")

        org_filter_parts.append("bc.organization_id = %s")
        params.append(org_id)

        where_clauses.append(f"({' OR '.join(org_filter_parts)})")

        if outlet_id:
            if not check_outlet_access(current_user, outlet_id):
                raise HTTPException(status_code=403, detail="You don't have access to this outlet")
            where_clauses.append("(bc.outlet_id IS NULL OR bc.outlet_id = %s)")
            params.append(outlet_id)
        else:
            where_clauses.append("bc.outlet_id IS NULL")

        if from_unit_id:
            where_clauses.append("bc.from_unit_id = %s")
            params.append(from_unit_id)

        if to_unit_id:
            where_clauses.append("bc.to_unit_id = %s")
            params.append(to_unit_id)

        where_clause = " AND ".join(where_clauses)

        cursor.execute(f"""
            SELECT
                bc.*,
                fu.name as from_unit_name,
                fu.abbreviation as from_unit_abbr,
                fu.unit_type as from_unit_type,
                tu.name as to_unit_name,
                tu.abbreviation as to_unit_abbr,
                tu.unit_type as to_unit_type,
                o.name as outlet_name,
                CASE
                    WHEN bc.organization_id IS NULL THEN 'system'
                    WHEN bc.outlet_id IS NOT NULL THEN 'outlet'
                    ELSE 'organization'
                END as scope
            FROM base_conversions bc
            JOIN units fu ON fu.id = bc.from_unit_id
            JOIN units tu ON tu.id = bc.to_unit_id
            LEFT JOIN outlets o ON o.id = bc.outlet_id
            WHERE {where_clause}
            ORDER BY
                CASE WHEN bc.outlet_id IS NOT NULL THEN 0
                     WHEN bc.organization_id IS NOT NULL THEN 1
                     ELSE 2 END,
                fu.abbreviation,
                tu.abbreviation
        """, params)

        conversions = dicts_from_rows(cursor.fetchall())
        return {"conversions": conversions, "total": len(conversions)}


@router.get("/effective")
def get_effective_conversions(
    outlet_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the effective conversion for each unit pair.

    Returns only the highest-priority conversion for each from/to unit pair:
    1. Outlet-specific overrides first
    2. Organization-wide overrides second
    3. System defaults last

    This is useful for displaying what conversions are actually in effect.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        if outlet_id and not check_outlet_access(current_user, outlet_id):
            raise HTTPException(status_code=403, detail="You don't have access to this outlet")

        # Use DISTINCT ON to get highest priority conversion per unit pair
        cursor.execute("""
            SELECT DISTINCT ON (from_unit_id, to_unit_id)
                bc.*,
                fu.name as from_unit_name,
                fu.abbreviation as from_unit_abbr,
                fu.unit_type as from_unit_type,
                tu.name as to_unit_name,
                tu.abbreviation as to_unit_abbr,
                tu.unit_type as to_unit_type,
                o.name as outlet_name,
                CASE
                    WHEN bc.organization_id IS NULL THEN 'system'
                    WHEN bc.outlet_id IS NOT NULL THEN 'outlet'
                    ELSE 'organization'
                END as scope
            FROM base_conversions bc
            JOIN units fu ON fu.id = bc.from_unit_id
            JOIN units tu ON tu.id = bc.to_unit_id
            LEFT JOIN outlets o ON o.id = bc.outlet_id
            WHERE bc.is_active = 1
              AND (bc.organization_id IS NULL OR bc.organization_id = %s)
              AND (bc.outlet_id IS NULL OR bc.outlet_id = %s)
            ORDER BY
                from_unit_id,
                to_unit_id,
                CASE WHEN bc.outlet_id = %s THEN 0
                     WHEN bc.organization_id = %s THEN 1
                     ELSE 2 END
        """, (org_id, outlet_id or 0, outlet_id or 0, org_id))

        conversions = dicts_from_rows(cursor.fetchall())
        return {"conversions": conversions, "total": len(conversions)}


@router.get("/lookup")
def lookup_conversion(
    from_unit_id: int,
    to_unit_id: int,
    outlet_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Look up the effective conversion factor between two units.

    Returns the highest-priority conversion:
    1. Outlet-specific if exists
    2. Organization-wide if exists
    3. System default if exists
    """
    if from_unit_id == to_unit_id:
        return {
            "from_unit_id": from_unit_id,
            "to_unit_id": to_unit_id,
            "conversion_factor": 1.0,
            "scope": "same_unit"
        }

    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        if outlet_id and not check_outlet_access(current_user, outlet_id):
            raise HTTPException(status_code=403, detail="You don't have access to this outlet")

        cursor.execute("""
            SELECT
                bc.conversion_factor,
                fu.abbreviation as from_unit_abbr,
                tu.abbreviation as to_unit_abbr,
                CASE
                    WHEN bc.organization_id IS NULL THEN 'system'
                    WHEN bc.outlet_id IS NOT NULL THEN 'outlet'
                    ELSE 'organization'
                END as scope
            FROM base_conversions bc
            JOIN units fu ON fu.id = bc.from_unit_id
            JOIN units tu ON tu.id = bc.to_unit_id
            WHERE bc.from_unit_id = %s
              AND bc.to_unit_id = %s
              AND bc.is_active = 1
              AND (bc.organization_id IS NULL OR bc.organization_id = %s)
              AND (bc.outlet_id IS NULL OR bc.outlet_id = %s)
            ORDER BY
                CASE WHEN bc.outlet_id = %s THEN 0
                     WHEN bc.organization_id = %s THEN 1
                     ELSE 2 END
            LIMIT 1
        """, (from_unit_id, to_unit_id, org_id, outlet_id or 0, outlet_id or 0, org_id))

        result = dict_from_row(cursor.fetchone())
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No conversion found from unit {from_unit_id} to unit {to_unit_id}"
            )

        return {
            "from_unit_id": from_unit_id,
            "to_unit_id": to_unit_id,
            "from_unit_abbr": result["from_unit_abbr"],
            "to_unit_abbr": result["to_unit_abbr"],
            "conversion_factor": float(result["conversion_factor"]),
            "scope": result["scope"]
        }


@router.post("")
def create_base_conversion(
    conversion: BaseConversionCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new base conversion for the organization or outlet.

    This creates an override for the system default or adds a new conversion.
    """
    if conversion.from_unit_id == conversion.to_unit_id:
        raise HTTPException(status_code=400, detail="From and to units must be different")

    if conversion.conversion_factor <= 0:
        raise HTTPException(status_code=400, detail="Conversion factor must be positive")

    if conversion.outlet_id and not check_outlet_access(current_user, conversion.outlet_id):
        raise HTTPException(status_code=403, detail="You don't have access to this outlet")

    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]
        user_id = current_user["user_id"]

        try:
            cursor.execute("""
                INSERT INTO base_conversions
                    (organization_id, outlet_id, from_unit_id, to_unit_id, conversion_factor, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                org_id,
                conversion.outlet_id,
                conversion.from_unit_id,
                conversion.to_unit_id,
                conversion.conversion_factor,
                conversion.notes,
                user_id
            ))

            conversion_id = cursor.fetchone()["id"]
            conn.commit()

            return {"message": "Conversion created successfully", "conversion_id": conversion_id}

        except Exception as e:
            if "idx_base_conversions_lookup" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="A conversion between these units already exists at this scope"
                )
            raise


@router.patch("/{conversion_id}")
def update_base_conversion(
    conversion_id: int,
    updates: BaseConversionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing base conversion.

    Note: System defaults (organization_id = NULL) cannot be modified.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        # Check conversion exists and belongs to org (not system default)
        cursor.execute("""
            SELECT id, organization_id, outlet_id
            FROM base_conversions
            WHERE id = %s
        """, (conversion_id,))

        existing = dict_from_row(cursor.fetchone())
        if not existing:
            raise HTTPException(status_code=404, detail="Conversion not found")

        if existing["organization_id"] is None:
            raise HTTPException(
                status_code=403,
                detail="System default conversions cannot be modified. Create an organization override instead."
            )

        if existing["organization_id"] != org_id:
            raise HTTPException(status_code=404, detail="Conversion not found")

        if existing["outlet_id"] and not check_outlet_access(current_user, existing["outlet_id"]):
            raise HTTPException(status_code=403, detail="You don't have access to this outlet")

        # Build update query
        update_fields = []
        params = []

        update_dict = updates.dict(exclude_unset=True)

        if "conversion_factor" in update_dict:
            if update_dict["conversion_factor"] <= 0:
                raise HTTPException(status_code=400, detail="Conversion factor must be positive")
            update_fields.append("conversion_factor = %s")
            params.append(update_dict["conversion_factor"])

        if "notes" in update_dict:
            update_fields.append("notes = %s")
            params.append(update_dict["notes"])

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = NOW()")
        params.append(conversion_id)

        cursor.execute(f"""
            UPDATE base_conversions
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"message": "Conversion updated successfully", "conversion_id": conversion_id}


@router.delete("/{conversion_id}")
def delete_base_conversion(
    conversion_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a base conversion.

    Note: System defaults (organization_id = NULL) cannot be deleted.
    Deleting an org/outlet override will cause the system default to take effect again.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        # Check conversion exists and belongs to org
        cursor.execute("""
            SELECT id, organization_id, outlet_id
            FROM base_conversions
            WHERE id = %s
        """, (conversion_id,))

        existing = dict_from_row(cursor.fetchone())
        if not existing:
            raise HTTPException(status_code=404, detail="Conversion not found")

        if existing["organization_id"] is None:
            raise HTTPException(
                status_code=403,
                detail="System default conversions cannot be deleted"
            )

        if existing["organization_id"] != org_id:
            raise HTTPException(status_code=404, detail="Conversion not found")

        if existing["outlet_id"] and not check_outlet_access(current_user, existing["outlet_id"]):
            raise HTTPException(status_code=403, detail="You don't have access to this outlet")

        cursor.execute("""
            DELETE FROM base_conversions
            WHERE id = %s AND organization_id = %s
        """, (conversion_id, org_id))

        conn.commit()
        return {"message": "Conversion deleted successfully", "conversion_id": conversion_id}


@router.post("/create-reverse")
def create_reverse_conversion(
    from_unit_id: int,
    to_unit_id: int,
    outlet_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Automatically create the reverse conversion based on an existing one.

    For example, if OZ → LB = 0.0625 exists, this creates LB → OZ = 16.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]
        user_id = current_user["user_id"]

        if outlet_id and not check_outlet_access(current_user, outlet_id):
            raise HTTPException(status_code=403, detail="You don't have access to this outlet")

        # Find the existing conversion
        cursor.execute("""
            SELECT conversion_factor, notes
            FROM base_conversions
            WHERE from_unit_id = %s
              AND to_unit_id = %s
              AND is_active = 1
              AND (organization_id IS NULL OR organization_id = %s)
              AND (outlet_id IS NULL OR outlet_id = %s)
            ORDER BY
                CASE WHEN outlet_id = %s THEN 0
                     WHEN organization_id = %s THEN 1
                     ELSE 2 END
            LIMIT 1
        """, (from_unit_id, to_unit_id, org_id, outlet_id or 0, outlet_id or 0, org_id))

        existing = dict_from_row(cursor.fetchone())
        if not existing:
            raise HTTPException(
                status_code=404,
                detail="No conversion found to create reverse from"
            )

        reverse_factor = 1.0 / float(existing["conversion_factor"])

        try:
            cursor.execute("""
                INSERT INTO base_conversions
                    (organization_id, outlet_id, from_unit_id, to_unit_id, conversion_factor, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                org_id,
                outlet_id,
                to_unit_id,  # Reverse direction
                from_unit_id,
                reverse_factor,
                f"Auto-generated reverse of conversion",
                user_id
            ))

            conversion_id = cursor.fetchone()["id"]
            conn.commit()

            return {
                "message": "Reverse conversion created successfully",
                "conversion_id": conversion_id,
                "conversion_factor": reverse_factor
            }

        except Exception as e:
            if "idx_base_conversions_lookup" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="A reverse conversion already exists at this scope"
                )
            raise
