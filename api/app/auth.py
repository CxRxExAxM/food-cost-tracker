"""
Authentication utilities for JWT-based auth - PostgreSQL version.
"""
from datetime import datetime, timedelta
from typing import Optional
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .database import get_db, dict_from_row

# Configuration - use environment variable in production
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token extraction
security = HTTPBearer()


# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
    organization_id: Optional[int] = None


class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "viewer"


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    organization_id: int
    is_super_admin: bool = False


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# JWT utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        organization_id: int = payload.get("organization_id")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
        return TokenData(user_id=user_id, email=email, role=role, organization_id=organization_id)
    except (JWTError, ValueError):
        return None


# Database utilities
def get_user_by_email(email: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return dict_from_row(cursor.fetchone())


def get_user_by_id(user_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return dict_from_row(cursor.fetchone())


def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    if not user["is_active"]:
        return None
    return user


# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate JWT token, return current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        token_data = decode_token(token)

        if token_data is None:
            raise credentials_exception

        user = get_user_by_id(token_data.user_id)

        if user is None:
            raise credentials_exception

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )

        return user
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception


async def get_current_super_admin(current_user: dict = Depends(get_current_user)):
    """Verify user is a super admin."""
    if not current_user.get('is_super_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


# Role-based access control dependencies
def require_role(allowed_roles: list):
    """Factory function to create role-checking dependencies."""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


# Convenience dependencies
require_admin = require_role(["admin"])
require_chef_or_admin = require_role(["admin", "chef"])
require_any_auth = require_role(["admin", "chef", "viewer"])


# ============================================
# Outlet Filtering Utilities
# ============================================

def get_user_outlet_ids(user_id: int) -> list:
    """
    Get list of outlet IDs that a user has access to.
    Returns empty list if user has access to ALL outlets (org-wide admin).
    """
    from .database import get_db

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT outlet_id FROM user_outlets
            WHERE user_id = %s
        """, (user_id,))

        rows = cursor.fetchall()

        if not rows:
            # No outlet assignments = org-wide admin
            return []

        return [row["outlet_id"] for row in rows]


def build_outlet_filter(current_user: dict, table_alias: str = "") -> tuple:
    """
    Build SQL WHERE clause for outlet filtering.

    Args:
        current_user: User dict from get_current_user
        table_alias: Optional table alias (e.g., "p" for products)

    Returns:
        Tuple of (where_clause, params)

    Example:
        where_clause, params = build_outlet_filter(current_user, "p")
        query = f"SELECT * FROM products p WHERE {where_clause}"
        cursor.execute(query, params)
    """
    outlet_ids = get_user_outlet_ids(current_user["id"])
    prefix = f"{table_alias}." if table_alias else ""

    if not outlet_ids:
        # Org-wide admin - sees all outlets in organization
        where_clause = f"{prefix}organization_id = %s"
        params = [current_user["organization_id"]]
    else:
        # Outlet-scoped user - sees only assigned outlets
        placeholders = ', '.join(['%s'] * len(outlet_ids))
        where_clause = f"{prefix}organization_id = %s AND {prefix}outlet_id IN ({placeholders})"
        params = [current_user["organization_id"]] + outlet_ids

    return where_clause, params


def check_outlet_access(current_user: dict, outlet_id: int) -> bool:
    """
    Check if user has access to a specific outlet.

    Args:
        current_user: User dict from get_current_user
        outlet_id: Outlet ID to check

    Returns:
        True if user has access, False otherwise
    """
    # Check if outlet belongs to user's organization
    from .database import get_db

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, current_user["organization_id"]))

        if not cursor.fetchone():
            return False

    # Get user's outlet access
    outlet_ids = get_user_outlet_ids(current_user["id"])

    if not outlet_ids:
        # Org-wide admin - has access to all outlets
        return True

    # Check if outlet_id is in user's list
    return outlet_id in outlet_ids


def require_outlet_access(outlet_id: int):
    """
    Dependency to check outlet access.
    Raises 403 if user doesn't have access to the outlet.

    Usage:
        @router.get("/products")
        def list_products(
            outlet_id: int,
            current_user: dict = Depends(require_outlet_access(outlet_id))
        ):
            ...
    """
    async def outlet_access_checker(current_user: dict = Depends(get_current_user)):
        if not check_outlet_access(current_user, outlet_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this outlet"
            )
        return current_user
    return outlet_access_checker
