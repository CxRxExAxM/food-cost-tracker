"""
Authentication router for user registration, login, and management.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta

from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import (
    UserCreate, UserLogin, UserResponse, UserUpdate, Token,
    get_password_hash, authenticate_user, create_access_token,
    get_current_user, require_admin, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..tier_limits import check_user_limit_sql

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, current_user: dict = Depends(require_admin)):
    """
    Register a new user. Only admins can create new users.
    """
    with get_db() as conn:
        # Check tier limits before creating user
        check_user_limit_sql(conn, current_user["organization_id"])

        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (user.username,))
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

        # Create user in same organization as the admin creating them
        hashed_password = get_password_hash(user.password)
        cursor.execute("""
            INSERT INTO users (organization_id, email, username, hashed_password, full_name, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (current_user["organization_id"], user.email, user.username, hashed_password, user.full_name, user.role))

        conn.commit()
        user_id = cursor.lastrowid

        return {
            "id": user_id,
            "organization_id": current_user["organization_id"],
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": True
        }


@router.post("/login", response_model=Token)
def login(credentials: UserLogin):
    """
    Login with email and password, receive JWT token.
    """
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
            "organization_id": user["organization_id"],
            "email": user["email"],
            "role": user["role"]
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current logged-in user's information with organization details.
    """
    from ..database import get_db, dict_from_row

    # Fetch organization details if organization_id exists
    org_name = None
    org_tier = None

    if current_user.get("organization_id"):
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name, subscription_tier
                    FROM organizations
                    WHERE id = ?
                """, (current_user["organization_id"],))
                org = dict_from_row(cursor.fetchone())

                if org:
                    org_name = org["name"]
                    org_tier = org["subscription_tier"]
        except Exception as e:
            # Log error but don't fail the request
            print(f"Warning: Failed to fetch organization details: {e}")

    return {
        "id": current_user["id"],
        "organization_id": current_user.get("organization_id"),
        "organization_name": org_name,
        "organization_tier": org_tier,
        "email": current_user["email"],
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "is_active": bool(current_user["is_active"])
    }


@router.get("/users", response_model=list[UserResponse])
def list_users(current_user: dict = Depends(require_admin)):
    """
    List all users in current organization. Admin only.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, organization_id, email, username, full_name, role, is_active
            FROM users
            WHERE organization_id = ?
            ORDER BY username
        """, (current_user["organization_id"],))
        users = dicts_from_rows(cursor.fetchall())
        return [{**u, "is_active": bool(u["is_active"])} for u in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, updates: UserUpdate, current_user: dict = Depends(require_admin)):
    """
    Update a user's role or active status. Admin only.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check user exists
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = dict_from_row(cursor.fetchone())
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Build update query
        update_fields = []
        params = []

        if updates.full_name is not None:
            update_fields.append("full_name = ?")
            params.append(updates.full_name)

        if updates.role is not None:
            if updates.role not in ["admin", "chef", "viewer"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role"
                )
            update_fields.append("role = ?")
            params.append(updates.role)

        if updates.is_active is not None:
            update_fields.append("is_active = ?")
            params.append(1 if updates.is_active else 0)

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()

        # Return updated user
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        updated_user = dict_from_row(cursor.fetchone())

        return {
            "id": updated_user["id"],
            "email": updated_user["email"],
            "username": updated_user["username"],
            "full_name": updated_user["full_name"],
            "role": updated_user["role"],
            "is_active": bool(updated_user["is_active"])
        }


@router.post("/setup", response_model=Token)
def initial_setup(user: UserCreate):
    """
    Create the initial admin user. Only works if no users exist.
    This endpoint is for initial setup only.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if any users exist
        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()[0]

        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setup already completed. Users exist in the system."
            )

        # Create default organization first
        cursor.execute("""
            INSERT INTO organizations (name, slug, subscription_tier, subscription_status)
            VALUES (?, ?, 'free', 'active')
        """, ("Default Organization", "default"))
        conn.commit()
        organization_id = cursor.lastrowid

        # Create admin user
        hashed_password = get_password_hash(user.password)
        cursor.execute("""
            INSERT INTO users (organization_id, email, username, hashed_password, full_name, role)
            VALUES (?, ?, ?, ?, ?, 'admin')
        """, (organization_id, user.email, user.username, hashed_password, user.full_name))

        conn.commit()
        user_id = cursor.lastrowid

        # Generate token for immediate login
        access_token = create_access_token(
            data={
                "sub": str(user_id),
                "organization_id": organization_id,
                "email": user.email,
                "role": "admin"
            },
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {"access_token": access_token, "token_type": "bearer"}


@router.get("/setup-status")
def check_setup_status():
    """
    Check if initial setup is needed (no users exist).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()[0]

        return {
            "setup_required": count == 0,
            "user_count": count
        }
