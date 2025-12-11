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
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
        return TokenData(user_id=user_id, email=email, role=role)
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
