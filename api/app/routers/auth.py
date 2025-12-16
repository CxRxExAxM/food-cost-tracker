"""
Authentication router for user registration, login, and management - PostgreSQL version.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta

from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import (
    UserCreate, UserLogin, UserResponse, UserUpdate, Token,
    get_password_hash, authenticate_user, create_access_token,
    get_current_user, require_admin, ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/setup-status")
def check_setup_status():
    """Check if initial setup has been completed."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        count = result["count"] if result else 0
        return {
            "setup_required": count == 0,
            "user_count": count
        }


@router.post("/setup", response_model=Token)
def initial_setup(user: UserCreate):
    """
    Initial setup endpoint - creates the first organization and admin user.
    Only works if no users exist yet.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if any users exist
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        count = result["count"] if result else 0

        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setup already completed"
            )

        # Create first organization (extract from email or use default)
        org_name = user.email.split('@')[0].replace('.', ' ').title() + "'s Organization"
        org_slug = user.email.split('@')[0].replace('.', '_').lower()

        cursor.execute("""
            INSERT INTO organizations (name, slug, subscription_tier, subscription_status)
            VALUES (%s, %s, 'free', 'active')
            RETURNING id
        """, (org_name, org_slug))

        result = cursor.fetchone()
        organization_id = result["id"]

        # Create first admin user with organization
        hashed_password = get_password_hash(user.password)
        cursor.execute("""
            INSERT INTO users (email, username, hashed_password, full_name, role, organization_id)
            VALUES (%s, %s, %s, %s, 'admin', %s)
            RETURNING id
        """, (user.email, user.username, hashed_password, user.full_name, organization_id))

        result = cursor.fetchone()
        user_id = result["id"]
        conn.commit()

        # Generate token with organization_id
        access_token = create_access_token(
            data={
                "sub": str(user_id),
                "email": user.email,
                "role": "admin",
                "organization_id": organization_id
            },
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, current_user: dict = Depends(require_admin)):
    """Register a new user in the same organization. Only admins can create new users."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Validate role
        if user.role not in ["admin", "chef", "viewer"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be: admin, chef, or viewer"
            )

        # Create user in the same organization as current user
        organization_id = current_user["organization_id"]
        hashed_password = get_password_hash(user.password)
        cursor.execute("""
            INSERT INTO users (email, username, hashed_password, full_name, role, organization_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user.email, user.username, hashed_password, user.full_name, user.role, organization_id))

        result = cursor.fetchone()
        user_id = result["id"]
        conn.commit()

        return {
            "id": user_id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": True,
            "organization_id": organization_id
        }


@router.post("/login", response_model=Token)
def login(credentials: UserLogin):
    """Login with email and password, receive JWT token."""
    user = authenticate_user(credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": str(user["id"]),
            "email": user["email"],
            "role": user["role"],
            "organization_id": user["organization_id"]
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user's information."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Fetch organization details
        cursor.execute("""
            SELECT name, subscription_tier
            FROM organizations
            WHERE id = %s
        """, (current_user["organization_id"],))

        org = cursor.fetchone()
        org_name = org["name"] if org else None
        org_tier = org["subscription_tier"] if org else None

    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "is_active": bool(current_user["is_active"]),
        "organization_id": current_user["organization_id"],
        "is_super_admin": bool(current_user.get("is_super_admin", 0)),
        "organization_name": org_name,
        "organization_tier": org_tier
    }


@router.get("/users", response_model=list[UserResponse])
def list_users(current_user: dict = Depends(require_admin)):
    """List all users in the same organization. Admin only."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, username, full_name, role, is_active, organization_id
            FROM users
            WHERE organization_id = %s
            ORDER BY username
        """, (current_user["organization_id"],))
        users = dicts_from_rows(cursor.fetchall())
        return [{**u, "is_active": bool(u["is_active"])} for u in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, updates: UserUpdate, current_user: dict = Depends(require_admin)):
    """Update a user's role or active status. Admin only."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check user exists and is in same organization
        cursor.execute("SELECT * FROM users WHERE id = %s AND organization_id = %s", (user_id, current_user["organization_id"]))
        user = dict_from_row(cursor.fetchone())
        if not user:
            raise HTTPException(status_code=404, detail="User not found in your organization")

        # Build update query
        update_fields = []
        params = []

        if updates.full_name is not None:
            update_fields.append("full_name = %s")
            params.append(updates.full_name)

        if updates.role is not None:
            if updates.role not in ["admin", "chef", "viewer"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role"
                )
            update_fields.append("role = %s")
            params.append(updates.role)

        if updates.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(1 if updates.is_active else 0)

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, tuple(params))
        conn.commit()

        # Fetch updated user
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        updated_user = dict_from_row(cursor.fetchone())

        return {
            **updated_user,
            "is_active": bool(updated_user["is_active"])
        }
