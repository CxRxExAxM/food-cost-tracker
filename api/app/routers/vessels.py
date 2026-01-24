"""Vessels API Router

CRUD operations for vessels and their product-specific capacities.
Vessels are organization-wide containers (e.g., Chafing Dish, Small Bowl)
that can have default capacities and product-specific capacities.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import get_current_user

router = APIRouter(prefix="/vessels", tags=["vessels"])


# ============================================
# Pydantic Models
# ============================================

class VesselCreate(BaseModel):
    """Create a new vessel."""
    name: str
    default_capacity: Optional[float] = None
    default_unit_id: Optional[int] = None


class VesselUpdate(BaseModel):
    """Update an existing vessel."""
    name: Optional[str] = None
    default_capacity: Optional[float] = None
    default_unit_id: Optional[int] = None


class VesselCapacityCreate(BaseModel):
    """Create a product-specific capacity for a vessel."""
    common_product_id: int
    capacity: float
    unit_id: Optional[int] = None
    notes: Optional[str] = None


class VesselCapacityUpdate(BaseModel):
    """Update a product capacity."""
    capacity: Optional[float] = None
    unit_id: Optional[int] = None
    notes: Optional[str] = None


# ============================================
# Vessel Endpoints
# ============================================

@router.get("")
def list_vessels(
    include_inactive: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    List all vessels for the organization.
    Includes default capacity info and count of product-specific capacities.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        where_clause = "v.organization_id = %s"
        params = [org_id]

        if not include_inactive:
            where_clause += " AND v.is_active = 1"

        cursor.execute(f"""
            SELECT
                v.*,
                u.abbreviation as default_unit_abbr,
                u.name as default_unit_name,
                (SELECT COUNT(*) FROM vessel_product_capacities WHERE vessel_id = v.id) as capacity_count
            FROM vessels v
            LEFT JOIN units u ON u.id = v.default_unit_id
            WHERE {where_clause}
            ORDER BY v.name
        """, params)

        vessels = dicts_from_rows(cursor.fetchall())
        return {"vessels": vessels, "total": len(vessels)}


@router.get("/{vessel_id}")
def get_vessel(vessel_id: int, current_user: dict = Depends(get_current_user)):
    """
    Get a single vessel with all its product-specific capacities.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        cursor.execute("""
            SELECT
                v.*,
                u.abbreviation as default_unit_abbr,
                u.name as default_unit_name
            FROM vessels v
            LEFT JOIN units u ON u.id = v.default_unit_id
            WHERE v.id = %s AND v.organization_id = %s
        """, (vessel_id, org_id))

        vessel = dict_from_row(cursor.fetchone())
        if not vessel:
            raise HTTPException(status_code=404, detail="Vessel not found")

        # Get product-specific capacities
        cursor.execute("""
            SELECT
                vpc.*,
                cp.common_name as product_name,
                cp.category as product_category,
                u.abbreviation as unit_abbr,
                u.name as unit_name
            FROM vessel_product_capacities vpc
            JOIN common_products cp ON cp.id = vpc.common_product_id
            LEFT JOIN units u ON u.id = vpc.unit_id
            WHERE vpc.vessel_id = %s
            ORDER BY cp.common_name
        """, (vessel_id,))

        vessel["capacities"] = dicts_from_rows(cursor.fetchall())
        return vessel


@router.post("")
def create_vessel(vessel: VesselCreate, current_user: dict = Depends(get_current_user)):
    """Create a new vessel for the organization."""
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        try:
            cursor.execute("""
                INSERT INTO vessels (organization_id, name, default_capacity, default_unit_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (org_id, vessel.name, vessel.default_capacity, vessel.default_unit_id))

            vessel_id = cursor.fetchone()["id"]
            conn.commit()

            return {"message": "Vessel created successfully", "vessel_id": vessel_id}

        except Exception as e:
            if "unique_vessel_per_org" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail=f"A vessel named '{vessel.name}' already exists"
                )
            raise


@router.patch("/{vessel_id}")
def update_vessel(
    vessel_id: int,
    updates: VesselUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing vessel."""
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        # Check vessel exists and belongs to org
        cursor.execute("""
            SELECT id FROM vessels
            WHERE id = %s AND organization_id = %s
        """, (vessel_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Vessel not found")

        # Build update query
        update_fields = []
        params = []

        update_dict = updates.dict(exclude_unset=True)
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = NOW()")
        params.append(vessel_id)

        try:
            cursor.execute(f"""
                UPDATE vessels
                SET {', '.join(update_fields)}
                WHERE id = %s
            """, params)

            conn.commit()
            return {"message": "Vessel updated successfully", "vessel_id": vessel_id}

        except Exception as e:
            if "unique_vessel_per_org" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="A vessel with this name already exists"
                )
            raise


@router.delete("/{vessel_id}")
def delete_vessel(vessel_id: int, current_user: dict = Depends(get_current_user)):
    """
    Delete a vessel (soft delete by setting is_active = 0).
    Product capacities remain but vessel won't appear in lists.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        cursor.execute("""
            UPDATE vessels
            SET is_active = 0, updated_at = NOW()
            WHERE id = %s AND organization_id = %s
        """, (vessel_id, org_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Vessel not found")

        conn.commit()
        return {"message": "Vessel deleted successfully", "vessel_id": vessel_id}


# ============================================
# Vessel Capacity Endpoints
# ============================================

@router.post("/{vessel_id}/capacities")
def create_vessel_capacity(
    vessel_id: int,
    capacity: VesselCapacityCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add a product-specific capacity to a vessel."""
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        # Verify vessel belongs to org
        cursor.execute("""
            SELECT id FROM vessels
            WHERE id = %s AND organization_id = %s
        """, (vessel_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Vessel not found")

        try:
            cursor.execute("""
                INSERT INTO vessel_product_capacities
                    (vessel_id, common_product_id, capacity, unit_id, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                vessel_id,
                capacity.common_product_id,
                capacity.capacity,
                capacity.unit_id,
                capacity.notes
            ))

            capacity_id = cursor.fetchone()["id"]
            conn.commit()

            return {"message": "Capacity added successfully", "capacity_id": capacity_id}

        except Exception as e:
            if "unique_vessel_product_capacity" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="A capacity for this product already exists on this vessel"
                )
            if "fk_vessel_capacities_common_product" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="Common product not found"
                )
            raise


@router.patch("/{vessel_id}/capacities/{capacity_id}")
def update_vessel_capacity(
    vessel_id: int,
    capacity_id: int,
    updates: VesselCapacityUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a product-specific capacity."""
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        # Verify capacity belongs to a vessel in this org
        cursor.execute("""
            SELECT vpc.id FROM vessel_product_capacities vpc
            JOIN vessels v ON v.id = vpc.vessel_id
            WHERE vpc.id = %s AND vpc.vessel_id = %s AND v.organization_id = %s
        """, (capacity_id, vessel_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Capacity not found")

        # Build update query
        update_fields = []
        params = []

        update_dict = updates.dict(exclude_unset=True)
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = NOW()")
        params.append(capacity_id)

        cursor.execute(f"""
            UPDATE vessel_product_capacities
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"message": "Capacity updated successfully", "capacity_id": capacity_id}


@router.delete("/{vessel_id}/capacities/{capacity_id}")
def delete_vessel_capacity(
    vessel_id: int,
    capacity_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove a product-specific capacity from a vessel."""
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        # Verify capacity belongs to a vessel in this org
        cursor.execute("""
            DELETE FROM vessel_product_capacities vpc
            USING vessels v
            WHERE vpc.id = %s
              AND vpc.vessel_id = %s
              AND vpc.vessel_id = v.id
              AND v.organization_id = %s
        """, (capacity_id, vessel_id, org_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Capacity not found")

        conn.commit()
        return {"message": "Capacity deleted successfully", "capacity_id": capacity_id}


@router.get("/{vessel_id}/capacity-for-product/{common_product_id}")
def get_capacity_for_product(
    vessel_id: int,
    common_product_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the capacity for a specific product in a vessel.
    Returns product-specific capacity if set, otherwise the vessel's default.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        # Get vessel with its default capacity
        cursor.execute("""
            SELECT
                v.id,
                v.name,
                v.default_capacity,
                v.default_unit_id,
                du.abbreviation as default_unit_abbr
            FROM vessels v
            LEFT JOIN units u ON u.id = v.default_unit_id
            LEFT JOIN units du ON du.id = v.default_unit_id
            WHERE v.id = %s AND v.organization_id = %s AND v.is_active = 1
        """, (vessel_id, org_id))

        vessel = dict_from_row(cursor.fetchone())
        if not vessel:
            raise HTTPException(status_code=404, detail="Vessel not found")

        # Check for product-specific capacity
        cursor.execute("""
            SELECT
                vpc.capacity,
                vpc.unit_id,
                u.abbreviation as unit_abbr,
                cp.common_name as product_name
            FROM vessel_product_capacities vpc
            JOIN common_products cp ON cp.id = vpc.common_product_id
            LEFT JOIN units u ON u.id = vpc.unit_id
            WHERE vpc.vessel_id = %s AND vpc.common_product_id = %s
        """, (vessel_id, common_product_id))

        product_capacity = dict_from_row(cursor.fetchone())

        if product_capacity:
            return {
                "vessel_id": vessel_id,
                "vessel_name": vessel["name"],
                "common_product_id": common_product_id,
                "product_name": product_capacity["product_name"],
                "capacity": float(product_capacity["capacity"]),
                "unit_id": product_capacity["unit_id"],
                "unit_abbr": product_capacity["unit_abbr"],
                "is_product_specific": True
            }
        else:
            return {
                "vessel_id": vessel_id,
                "vessel_name": vessel["name"],
                "common_product_id": common_product_id,
                "capacity": float(vessel["default_capacity"]) if vessel["default_capacity"] else None,
                "unit_id": vessel["default_unit_id"],
                "unit_abbr": vessel["default_unit_abbr"],
                "is_product_specific": False
            }
