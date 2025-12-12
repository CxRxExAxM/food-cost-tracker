"""
Organizations router - Admin endpoints for managing organizations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime

from ..database import get_db, dict_from_row, dicts_from_rows
from ..schemas import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(current_user: dict = Depends(get_current_user)):
    """Get current user's organization."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (current_user["organization_id"],))
        org = dict_from_row(cursor.fetchone())

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        return org


@router.get("/me/stats")
def get_my_organization_stats(current_user: dict = Depends(get_current_user)):
    """Get current user's organization usage statistics."""
    org_id = current_user["organization_id"]
    with get_db() as conn:
        cursor = conn.cursor()

        # Get organization
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        org = dict_from_row(cursor.fetchone())

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Get counts
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE organization_id = %s", (org_id,))
        user_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM recipes WHERE organization_id = %s AND is_active = 1", (org_id,))
        recipe_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM products WHERE organization_id = %s AND is_active = 1", (org_id,))
        product_count = cursor.fetchone()["count"]

        return {
            "organization_id": org_id,
            "organization_name": org['name'],
            "subscription_tier": org['subscription_tier'],
            "subscription_status": org['subscription_status'],
            "users": {
                "current": user_count,
                "max": org['max_users'],
                "available": org['max_users'] - user_count if org['max_users'] > 0 else -1
            },
            "recipes": {
                "current": recipe_count,
                "max": org['max_recipes'],
                "available": org['max_recipes'] - recipe_count if org['max_recipes'] > 0 else -1
            },
            "products": {
                "current": product_count
            }
        }


@router.patch("/me", response_model=OrganizationResponse)
def update_my_organization(
    org_data: OrganizationUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update current user's organization (admin only)."""
    org_id = current_user["organization_id"]
    with get_db() as conn:
        cursor = conn.cursor()

        # Check organization exists
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        org = dict_from_row(cursor.fetchone())

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Build update query
        update_fields = []
        params = []

        if org_data.name is not None:
            update_fields.append("name = %s")
            params.append(org_data.name)

        if org_data.contact_email is not None:
            update_fields.append("contact_email = %s")
            params.append(org_data.contact_email)

        if org_data.contact_phone is not None:
            update_fields.append("contact_phone = %s")
            params.append(org_data.contact_phone)

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(org_id)

        query = f"UPDATE organizations SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()

        # Return updated organization
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        updated_org = dict_from_row(cursor.fetchone())
        return updated_org


@router.get("", response_model=List[OrganizationResponse])
def list_organizations(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(require_admin)
):
    """List all organizations (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM organizations
            ORDER BY name
            LIMIT %s OFFSET %s
        """, (limit, skip))
        orgs = dicts_from_rows(cursor.fetchall())
        return orgs


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: int,
    current_user: dict = Depends(require_admin)
):
    """Get organization by ID (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        org = dict_from_row(cursor.fetchone())

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        return org


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_data: OrganizationCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new organization (admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if slug already exists
        cursor.execute("SELECT id FROM organizations WHERE slug = %s", (org_data.slug,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this slug already exists"
            )

        # Set tier-based limits
        tier_limits = {
            'free': {'max_users': 2, 'max_recipes': 5, 'max_distributors': 1, 'max_ai_parses_per_month': 10},
            'basic': {'max_users': 5, 'max_recipes': 50, 'max_distributors': 3, 'max_ai_parses_per_month': 100},
            'pro': {'max_users': 15, 'max_recipes': -1, 'max_distributors': -1, 'max_ai_parses_per_month': 500},
            'enterprise': {'max_users': -1, 'max_recipes': -1, 'max_distributors': -1, 'max_ai_parses_per_month': -1},
        }

        limits = tier_limits.get(org_data.subscription_tier, tier_limits['free'])

        # Create organization
        cursor.execute("""
            INSERT INTO organizations (
                name, slug, subscription_tier, subscription_status,
                max_users, max_recipes, max_distributors, max_ai_parses_per_month,
                contact_email, contact_phone, ai_parses_reset_date,
                ai_parses_used_this_month, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            org_data.name,
            org_data.slug,
            org_data.subscription_tier,
            org_data.subscription_status or 'active',
            limits['max_users'],
            limits['max_recipes'],
            limits['max_distributors'],
            limits['max_ai_parses_per_month'],
            org_data.contact_email,
            org_data.contact_phone,
            datetime.utcnow().isoformat(),
            0,  # ai_parses_used_this_month
            1   # is_active
        ))

        conn.commit()
        org_id = cursor.lastrowid

        # Fetch and return the created organization
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        org = dict_from_row(cursor.fetchone())
        return org


@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    org_data: OrganizationUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update an organization (admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check organization exists
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        org = dict_from_row(cursor.fetchone())

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Build update query
        update_fields = []
        params = []

        if org_data.name is not None:
            update_fields.append("name = %s")
            params.append(org_data.name)

        if org_data.subscription_status is not None:
            update_fields.append("subscription_status = %s")
            params.append(org_data.subscription_status)

        if org_data.contact_email is not None:
            update_fields.append("contact_email = %s")
            params.append(org_data.contact_email)

        if org_data.contact_phone is not None:
            update_fields.append("contact_phone = %s")
            params.append(org_data.contact_phone)

        if org_data.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(1 if org_data.is_active else 0)

        # Update tier limits if tier is changing
        if org_data.subscription_tier and org_data.subscription_tier != org['subscription_tier']:
            tier_limits = {
                'free': {'max_users': 2, 'max_recipes': 5, 'max_distributors': 1, 'max_ai_parses_per_month': 10},
                'basic': {'max_users': 5, 'max_recipes': 50, 'max_distributors': 3, 'max_ai_parses_per_month': 100},
                'pro': {'max_users': 15, 'max_recipes': -1, 'max_distributors': -1, 'max_ai_parses_per_month': 500},
                'enterprise': {'max_users': -1, 'max_recipes': -1, 'max_distributors': -1, 'max_ai_parses_per_month': -1},
            }
            limits = tier_limits.get(org_data.subscription_tier, tier_limits['free'])

            update_fields.append("subscription_tier = %s")
            params.append(org_data.subscription_tier)
            update_fields.append("max_users = %s")
            params.append(limits['max_users'])
            update_fields.append("max_recipes = %s")
            params.append(limits['max_recipes'])
            update_fields.append("max_distributors = %s")
            params.append(limits['max_distributors'])
            update_fields.append("max_ai_parses_per_month = %s")
            params.append(limits['max_ai_parses_per_month'])

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(org_id)

        query = f"UPDATE organizations SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()

        # Return updated organization
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        updated_org = dict_from_row(cursor.fetchone())
        return updated_org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: int,
    current_user: dict = Depends(require_admin)
):
    """Delete an organization (admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check organization exists
        cursor.execute("SELECT id FROM organizations WHERE id = %s", (org_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Check if org has users
        cursor.execute("SELECT COUNT(*) FROM users WHERE organization_id = %s", (org_id,))
        user_count = cursor.fetchone()[0]

        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete organization with {user_count} users. Remove users first."
            )

        cursor.execute("DELETE FROM organizations WHERE id = %s", (org_id,))
        conn.commit()
        return None


@router.get("/{org_id}/stats")
def get_organization_stats(
    org_id: int,
    current_user: dict = Depends(require_admin)
):
    """Get organization usage statistics (admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get organization
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        org = dict_from_row(cursor.fetchone())

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Get counts
        cursor.execute("SELECT COUNT(*) FROM users WHERE organization_id = %s", (org_id,))
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM recipes WHERE organization_id = %s", (org_id,))
        recipe_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM distributors WHERE organization_id = %s", (org_id,))
        distributor_count = cursor.fetchone()[0]

        return {
            "organization_id": org_id,
            "organization_name": org['name'],
            "subscription_tier": org['subscription_tier'],
            "users": {
                "current": user_count,
                "max": org['max_users'],
                "available": org['max_users'] - user_count if org['max_users'] > 0 else -1
            },
            "recipes": {
                "current": recipe_count,
                "max": org['max_recipes'],
                "available": org['max_recipes'] - recipe_count if org['max_recipes'] > 0 else -1
            },
            "distributors": {
                "current": distributor_count,
                "max": org['max_distributors'],
                "available": org['max_distributors'] - distributor_count if org['max_distributors'] > 0 else -1
            },
            "ai_parses": {
                "used_this_month": org['ai_parses_used_this_month'],
                "max": org['max_ai_parses_per_month'],
                "available": org['max_ai_parses_per_month'] - org['ai_parses_used_this_month'] if org['max_ai_parses_per_month'] > 0 else -1
            },
        }
