"""
Super Admin router - Platform owner dashboard for managing all organizations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..auth import get_current_super_admin
from ..database import get_db, dict_from_row


router = APIRouter(prefix="/super-admin", tags=["super-admin"])


# Pydantic models
class OrganizationCreate(BaseModel):
    name: str
    slug: str
    subscription_tier: str = "free"
    max_users: int = 2
    max_recipes: int = 5


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    subscription_tier: Optional[str] = None
    subscription_status: Optional[str] = None
    max_users: Optional[int] = None
    max_recipes: Optional[int] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    subscription_tier: str
    subscription_status: str
    max_users: int
    max_recipes: int
    created_at: datetime
    users_count: Optional[int] = None
    outlets_count: Optional[int] = None
    products_count: Optional[int] = None
    recipes_count: Optional[int] = None


class PlatformStatsResponse(BaseModel):
    total_organizations: int
    total_users: int
    total_outlets: int
    total_products: int
    total_recipes: int
    orgs_by_tier: dict
    active_organizations: int
    inactive_organizations: int


# Organizations endpoints
@router.get("/organizations", response_model=List[OrganizationResponse])
def list_all_organizations(
    skip: int = 0,
    limit: int = 100,
    tier: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_super_admin)
):
    """List all organizations with stats (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Build query with filters
        where_clauses = []
        params = []

        if tier:
            where_clauses.append("o.subscription_tier = %s")
            params.append(tier)

        if status_filter:
            where_clauses.append("o.subscription_status = %s")
            params.append(status_filter)

        if search:
            where_clauses.append("o.name ILIKE %s")
            params.append(f"%{search}%")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get organizations with counts
        query = f"""
            SELECT
                o.*,
                COUNT(DISTINCT u.id) as users_count,
                COUNT(DISTINCT ot.id) as outlets_count,
                COUNT(DISTINCT p.id) as products_count,
                COUNT(DISTINCT r.id) as recipes_count
            FROM organizations o
            LEFT JOIN users u ON u.organization_id = o.id AND u.is_active = 1
            LEFT JOIN outlets ot ON ot.organization_id = o.id AND ot.is_active = 1
            LEFT JOIN products p ON p.organization_id = o.id AND p.is_active = 1
            LEFT JOIN recipes r ON r.organization_id = o.id AND r.is_active = 1
            WHERE {where_clause}
            GROUP BY o.id
            ORDER BY o.created_at DESC
            LIMIT %s OFFSET %s
        """

        params.extend([limit, skip])
        cursor.execute(query, params)

        organizations = [dict_from_row(row) for row in cursor.fetchall()]
        return organizations


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
def get_organization_detail(
    org_id: int,
    current_user: dict = Depends(get_current_super_admin)
):
    """Get detailed organization information (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                o.*,
                COUNT(DISTINCT u.id) as users_count,
                COUNT(DISTINCT ot.id) as outlets_count,
                COUNT(DISTINCT p.id) as products_count,
                COUNT(DISTINCT r.id) as recipes_count
            FROM organizations o
            LEFT JOIN users u ON u.organization_id = o.id AND u.is_active = 1
            LEFT JOIN outlets ot ON ot.organization_id = o.id AND ot.is_active = 1
            LEFT JOIN products p ON p.organization_id = o.id AND p.is_active = 1
            LEFT JOIN recipes r ON r.organization_id = o.id AND r.is_active = 1
            WHERE o.id = %s
            GROUP BY o.id
        """, (org_id,))

        org = cursor.fetchone()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        return dict_from_row(org)


@router.post("/organizations", response_model=OrganizationResponse)
def create_organization(
    org: OrganizationCreate,
    current_user: dict = Depends(get_current_super_admin)
):
    """Create a new organization (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if slug already exists
        cursor.execute("SELECT id FROM organizations WHERE slug = %s", (org.slug,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization slug already exists"
            )

        # Create organization
        cursor.execute("""
            INSERT INTO organizations
            (name, slug, subscription_tier, subscription_status, max_users, max_recipes)
            VALUES (%s, %s, %s, 'active', %s, %s)
            RETURNING *
        """, (org.name, org.slug, org.subscription_tier, org.max_users, org.max_recipes))

        new_org = dict_from_row(cursor.fetchone())

        # Create default outlet for the organization
        cursor.execute("""
            INSERT INTO outlets (name, location, organization_id)
            VALUES ('Default Outlet', 'Main Location', %s)
        """, (new_org["id"],))

        conn.commit()

        # Add counts (will be 0 for new org)
        new_org["users_count"] = 0
        new_org["outlets_count"] = 1
        new_org["products_count"] = 0
        new_org["recipes_count"] = 0

        return new_org


@router.patch("/organizations/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    current_user: dict = Depends(get_current_super_admin)
):
    """Update organization details (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check organization exists
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Build update query
        update_fields = []
        params = []

        if org_update.name is not None:
            update_fields.append("name = %s")
            params.append(org_update.name)

        if org_update.subscription_tier is not None:
            update_fields.append("subscription_tier = %s")
            params.append(org_update.subscription_tier)

        if org_update.subscription_status is not None:
            update_fields.append("subscription_status = %s")
            params.append(org_update.subscription_status)

        if org_update.max_users is not None:
            update_fields.append("max_users = %s")
            params.append(org_update.max_users)

        if org_update.max_recipes is not None:
            update_fields.append("max_recipes = %s")
            params.append(org_update.max_recipes)

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        update_fields.append("updated_at = NOW()")
        params.append(org_id)

        query = f"""
            UPDATE organizations
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
        """

        cursor.execute(query, params)
        updated_org = dict_from_row(cursor.fetchone())
        conn.commit()

        # Add counts
        cursor.execute("""
            SELECT
                COUNT(DISTINCT u.id) as users_count,
                COUNT(DISTINCT ot.id) as outlets_count,
                COUNT(DISTINCT p.id) as products_count,
                COUNT(DISTINCT r.id) as recipes_count
            FROM organizations o
            LEFT JOIN users u ON u.organization_id = o.id AND u.is_active = 1
            LEFT JOIN outlets ot ON ot.organization_id = o.id AND ot.is_active = 1
            LEFT JOIN products p ON p.organization_id = o.id AND p.is_active = 1
            LEFT JOIN recipes r ON r.organization_id = o.id AND r.is_active = 1
            WHERE o.id = %s
        """, (org_id,))

        counts = dict_from_row(cursor.fetchone())
        updated_org.update(counts)

        return updated_org


@router.delete("/organizations/{org_id}")
def delete_organization(
    org_id: int,
    current_user: dict = Depends(get_current_super_admin)
):
    """Soft delete organization (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE organizations
            SET subscription_status = 'inactive', updated_at = NOW()
            WHERE id = %s
            RETURNING id
        """, (org_id,))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        conn.commit()
        return {"message": "Organization deactivated successfully"}


# Platform statistics endpoint
@router.get("/stats/overview", response_model=PlatformStatsResponse)
def get_platform_stats(
    current_user: dict = Depends(get_current_super_admin)
):
    """Get platform-wide statistics (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Total organizations
        cursor.execute("SELECT COUNT(*) as count FROM organizations")
        total_orgs = cursor.fetchone()["count"]

        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = 1")
        total_users = cursor.fetchone()["count"]

        # Total outlets
        cursor.execute("SELECT COUNT(*) as count FROM outlets WHERE is_active = 1")
        total_outlets = cursor.fetchone()["count"]

        # Total products
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1")
        total_products = cursor.fetchone()["count"]

        # Total recipes
        cursor.execute("SELECT COUNT(*) as count FROM recipes WHERE is_active = 1")
        total_recipes = cursor.fetchone()["count"]

        # Organizations by tier
        cursor.execute("""
            SELECT subscription_tier, COUNT(*) as count
            FROM organizations
            GROUP BY subscription_tier
        """)
        orgs_by_tier = {row["subscription_tier"]: row["count"] for row in cursor.fetchall()}

        # Active vs inactive orgs
        cursor.execute("""
            SELECT subscription_status, COUNT(*) as count
            FROM organizations
            GROUP BY subscription_status
        """)
        status_counts = {row["subscription_status"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_organizations": total_orgs,
            "total_users": total_users,
            "total_outlets": total_outlets,
            "total_products": total_products,
            "total_recipes": total_recipes,
            "orgs_by_tier": orgs_by_tier,
            "active_organizations": status_counts.get("active", 0),
            "inactive_organizations": status_counts.get("inactive", 0) + status_counts.get("suspended", 0)
        }


# User management endpoints
@router.get("/users")
def list_all_users(
    skip: int = 0,
    limit: int = 100,
    org_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_super_admin)
):
    """List all users across all organizations (super admin only)."""
    with get_db() as conn:
        cursor = conn.cursor()

        where_clauses = ["u.is_active = 1"]
        params = []

        if org_id:
            where_clauses.append("u.organization_id = %s")
            params.append(org_id)

        if search:
            where_clauses.append("(u.email ILIKE %s OR u.username ILIKE %s OR u.full_name ILIKE %s)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])

        where_clause = " AND ".join(where_clauses)
        params.extend([limit, skip])

        cursor.execute(f"""
            SELECT
                u.*,
                o.name as organization_name,
                o.subscription_tier
            FROM users u
            JOIN organizations o ON o.id = u.organization_id
            WHERE {where_clause}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, params)

        users = [dict_from_row(row) for row in cursor.fetchall()]
        return users
