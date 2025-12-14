"""
Outlets router - Endpoints for managing outlets within organizations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ..database import get_db, dict_from_row, dicts_from_rows
from ..schemas import OutletCreate, OutletUpdate, OutletResponse
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/outlets", tags=["outlets"])


@router.get("", response_model=List[OutletResponse])
def list_outlets(current_user: dict = Depends(get_current_user)):
    """List all outlets in user's organization."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM outlets
            WHERE organization_id = %s AND is_active = 1
            ORDER BY name
        """, (current_user["organization_id"],))

        outlets = dicts_from_rows(cursor.fetchall())
        return outlets


@router.get("/{outlet_id}", response_model=OutletResponse)
def get_outlet(outlet_id: int, current_user: dict = Depends(get_current_user)):
    """Get outlet details."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, current_user["organization_id"]))

        outlet = dict_from_row(cursor.fetchone())

        if not outlet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outlet not found"
            )

        return outlet


@router.post("", response_model=OutletResponse, status_code=status.HTTP_201_CREATED)
def create_outlet(
    outlet_data: OutletCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new outlet (admin only)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if outlet name already exists in this organization
        cursor.execute("""
            SELECT id FROM outlets
            WHERE organization_id = %s AND name = %s
        """, (org_id, outlet_data.name))

        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Outlet with this name already exists in your organization"
            )

        # Create outlet
        cursor.execute("""
            INSERT INTO outlets (organization_id, name, location, description, is_active)
            VALUES (%s, %s, %s, %s, 1)
            RETURNING id
        """, (
            org_id,
            outlet_data.name,
            outlet_data.location,
            outlet_data.description
        ))

        outlet_id = cursor.fetchone()["id"]
        conn.commit()

        # Fetch and return the created outlet
        cursor.execute("SELECT * FROM outlets WHERE id = %s", (outlet_id,))
        outlet = dict_from_row(cursor.fetchone())
        return outlet


@router.patch("/{outlet_id}", response_model=OutletResponse)
def update_outlet(
    outlet_id: int,
    outlet_data: OutletUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update an outlet (admin only)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check outlet exists and belongs to user's organization
        cursor.execute("""
            SELECT * FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        outlet = dict_from_row(cursor.fetchone())

        if not outlet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outlet not found"
            )

        # Build update query
        update_fields = []
        params = []

        if outlet_data.name is not None:
            # Check for duplicate name
            cursor.execute("""
                SELECT id FROM outlets
                WHERE organization_id = %s AND name = %s AND id != %s
            """, (org_id, outlet_data.name, outlet_id))

            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Outlet with this name already exists in your organization"
                )

            update_fields.append("name = %s")
            params.append(outlet_data.name)

        if outlet_data.location is not None:
            update_fields.append("location = %s")
            params.append(outlet_data.location)

        if outlet_data.description is not None:
            update_fields.append("description = %s")
            params.append(outlet_data.description)

        if outlet_data.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(outlet_data.is_active)

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(outlet_id)

        query = f"UPDATE outlets SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()

        # Return updated outlet
        cursor.execute("SELECT * FROM outlets WHERE id = %s", (outlet_id,))
        updated_outlet = dict_from_row(cursor.fetchone())
        return updated_outlet


@router.delete("/{outlet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_outlet(
    outlet_id: int,
    current_user: dict = Depends(require_admin)
):
    """Soft delete an outlet (admin only)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check outlet exists and belongs to user's organization
        cursor.execute("""
            SELECT * FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        outlet = dict_from_row(cursor.fetchone())

        if not outlet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outlet not found"
            )

        # Check if outlet has products or recipes
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM products WHERE outlet_id = %s AND is_active = 1) as products,
                (SELECT COUNT(*) FROM recipes WHERE outlet_id = %s AND is_active = 1) as recipes
        """, (outlet_id, outlet_id))

        counts = cursor.fetchone()

        if counts["products"] > 0 or counts["recipes"] > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete outlet with {counts['products']} products and {counts['recipes']} recipes. Deactivate instead or move data first."
            )

        # Soft delete (set is_active = 0)
        cursor.execute("""
            UPDATE outlets
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (outlet_id,))

        conn.commit()
        return None


@router.get("/{outlet_id}/stats")
def get_outlet_stats(
    outlet_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get usage statistics for an outlet."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check outlet exists and belongs to user's organization
        cursor.execute("""
            SELECT * FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        outlet = dict_from_row(cursor.fetchone())

        if not outlet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outlet not found"
            )

        # Get counts (based on which outlet has imported/used the products)
        # Uses price_history.outlet_id which was added in migration 002
        cursor.execute("""
            SELECT COUNT(DISTINCT p.id) as count
            FROM products p
            WHERE p.is_active = 1
            AND EXISTS (
                SELECT 1 FROM price_history ph
                JOIN distributor_products dp ON dp.id = ph.distributor_product_id
                WHERE dp.product_id = p.id AND ph.outlet_id = %s
            )
        """, (outlet_id,))
        product_count = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count FROM recipes
            WHERE outlet_id = %s AND is_active = 1
        """, (outlet_id,))
        recipe_count = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) FROM user_outlets
            WHERE outlet_id = %s
        """, (outlet_id,))
        user_count = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count FROM import_batches
            WHERE outlet_id = %s
        """, (outlet_id,))
        import_count = cursor.fetchone()["count"]

        return {
            "outlet_id": outlet_id,
            "outlet_name": outlet["name"],
            "organization_id": org_id,
            "products": product_count,
            "recipes": recipe_count,
            "users": user_count,
            "imports": import_count
        }


@router.get("/{outlet_id}/users")
def get_outlet_users(
    outlet_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get list of users assigned to this outlet."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check outlet exists and belongs to user's organization
        cursor.execute("""
            SELECT * FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outlet not found"
            )

        # Get users assigned to this outlet
        cursor.execute("""
            SELECT u.id, u.email, u.username, u.full_name, u.role
            FROM users u
            JOIN user_outlets uo ON u.id = uo.user_id
            WHERE uo.outlet_id = %s AND u.is_active = 1
            ORDER BY u.full_name, u.username
        """, (outlet_id,))

        users = dicts_from_rows(cursor.fetchall())
        return users


@router.post("/{outlet_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def assign_user_to_outlet(
    outlet_id: int,
    user_id: int,
    current_user: dict = Depends(require_admin)
):
    """Assign a user to an outlet (admin only)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check outlet exists and belongs to user's organization
        cursor.execute("""
            SELECT * FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outlet not found"
            )

        # Check user exists and belongs to same organization
        cursor.execute("""
            SELECT * FROM users
            WHERE id = %s AND organization_id = %s
        """, (user_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if already assigned
        cursor.execute("""
            SELECT * FROM user_outlets
            WHERE user_id = %s AND outlet_id = %s
        """, (user_id, outlet_id))

        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already assigned to this outlet"
            )

        # Assign user to outlet
        cursor.execute("""
            INSERT INTO user_outlets (user_id, outlet_id)
            VALUES (%s, %s)
        """, (user_id, outlet_id))

        conn.commit()
        return None


@router.delete("/{outlet_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_outlet(
    outlet_id: int,
    user_id: int,
    current_user: dict = Depends(require_admin)
):
    """Remove a user from an outlet (admin only)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check outlet exists and belongs to user's organization
        cursor.execute("""
            SELECT * FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outlet not found"
            )

        # Check user exists and belongs to same organization
        cursor.execute("""
            SELECT * FROM users
            WHERE id = %s AND organization_id = %s
        """, (user_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Remove assignment
        cursor.execute("""
            DELETE FROM user_outlets
            WHERE user_id = %s AND outlet_id = %s
        """, (user_id, outlet_id))

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not assigned to this outlet"
            )

        conn.commit()
        return None
