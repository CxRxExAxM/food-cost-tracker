"""
Tier limit enforcement utilities.

This module provides functions to check and enforce tier-based limits
for organizations across the application.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from .models import Organization, User, Recipe, Distributor
import sqlite3


def check_recipe_limit_sql(conn: sqlite3.Connection, organization_id: int) -> None:
    """
    Check if organization can create a new recipe (raw SQL version).

    Raises HTTPException if recipe limit is reached.
    """
    cursor = conn.cursor()

    # Get organization limits
    cursor.execute(
        "SELECT max_recipes, subscription_tier FROM organizations WHERE id = ?",
        (organization_id,)
    )
    result = cursor.fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    max_recipes, subscription_tier = result

    # -1 means unlimited
    if max_recipes == -1:
        return

    # Get current recipe count
    cursor.execute(
        "SELECT COUNT(*) FROM recipes WHERE organization_id = ?",
        (organization_id,)
    )
    current_recipe_count = cursor.fetchone()[0]

    if current_recipe_count >= max_recipes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Recipe limit reached. Your {subscription_tier} tier allows {max_recipes} recipes. Please upgrade to add more recipes."
        )


def check_user_limit_sql(conn: sqlite3.Connection, organization_id: int) -> None:
    """
    Check if organization can create a new user (raw SQL version).

    Raises HTTPException if user limit is reached.
    """
    cursor = conn.cursor()

    # Get organization limits
    cursor.execute(
        "SELECT max_users, subscription_tier FROM organizations WHERE id = ?",
        (organization_id,)
    )
    result = cursor.fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    max_users, subscription_tier = result

    # -1 means unlimited
    if max_users == -1:
        return

    # Get current user count
    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE organization_id = ?",
        (organization_id,)
    )
    current_user_count = cursor.fetchone()[0]

    if current_user_count >= max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User limit reached. Your {subscription_tier} tier allows {max_users} users. Please upgrade to add more users."
        )


def check_distributor_limit_sql(conn: sqlite3.Connection, organization_id: int) -> None:
    """
    Check if organization can create a new distributor (raw SQL version).

    Raises HTTPException if distributor limit is reached.
    """
    cursor = conn.cursor()

    # Get organization limits
    cursor.execute(
        "SELECT max_distributors, subscription_tier FROM organizations WHERE id = ?",
        (organization_id,)
    )
    result = cursor.fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    max_distributors, subscription_tier = result

    # -1 means unlimited
    if max_distributors == -1:
        return

    # Get current distributor count
    cursor.execute(
        "SELECT COUNT(*) FROM distributors WHERE organization_id = ?",
        (organization_id,)
    )
    current_distributor_count = cursor.fetchone()[0]

    if current_distributor_count >= max_distributors:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Distributor limit reached. Your {subscription_tier} tier allows {max_distributors} distributors. Please upgrade to add more distributors."
        )


def check_user_limit(db: Session, organization_id: int) -> None:
    """
    Check if organization can create a new user.

    Raises HTTPException if user limit is reached.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # -1 means unlimited
    if org.max_users == -1:
        return

    current_user_count = db.query(User).filter(User.organization_id == organization_id).count()

    if current_user_count >= org.max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User limit reached. Your {org.subscription_tier} tier allows {org.max_users} users. Please upgrade to add more users."
        )


def check_recipe_limit(db: Session, organization_id: int) -> None:
    """
    Check if organization can create a new recipe.

    Raises HTTPException if recipe limit is reached.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # -1 means unlimited
    if org.max_recipes == -1:
        return

    current_recipe_count = db.query(Recipe).filter(Recipe.organization_id == organization_id).count()

    if current_recipe_count >= org.max_recipes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Recipe limit reached. Your {org.subscription_tier} tier allows {org.max_recipes} recipes. Please upgrade to add more recipes."
        )


def check_distributor_limit(db: Session, organization_id: int) -> None:
    """
    Check if organization can create a new distributor.

    Raises HTTPException if distributor limit is reached.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # -1 means unlimited
    if org.max_distributors == -1:
        return

    current_distributor_count = db.query(Distributor).filter(Distributor.organization_id == organization_id).count()

    if current_distributor_count >= org.max_distributors:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Distributor limit reached. Your {org.subscription_tier} tier allows {org.max_distributors} distributors. Please upgrade to add more distributors."
        )


def check_ai_parse_limit(db: Session, organization_id: int) -> None:
    """
    Check if organization can perform an AI parse.

    Raises HTTPException if AI parse limit is reached for the month.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # -1 means unlimited
    if org.max_ai_parses_per_month == -1:
        return

    if org.ai_parses_used_this_month >= org.max_ai_parses_per_month:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"AI parse limit reached for this month. Your {org.subscription_tier} tier allows {org.max_ai_parses_per_month} AI parses per month. Please upgrade or wait until next month."
        )


def increment_ai_parse_count(db: Session, organization_id: int) -> None:
    """
    Increment the AI parse count for an organization.

    Call this after a successful AI parse operation.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org:
        org.ai_parses_used_this_month += 1
        db.commit()


def get_organization_limits(db: Session, organization_id: int) -> dict:
    """
    Get the current usage and limits for an organization.

    Returns a dictionary with current usage, max limits, and available counts.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    user_count = db.query(User).filter(User.organization_id == organization_id).count()
    recipe_count = db.query(Recipe).filter(Recipe.organization_id == organization_id).count()
    distributor_count = db.query(Distributor).filter(Distributor.organization_id == organization_id).count()

    return {
        "users": {
            "current": user_count,
            "max": org.max_users,
            "available": org.max_users - user_count if org.max_users > 0 else -1,
            "limit_reached": user_count >= org.max_users if org.max_users > 0 else False
        },
        "recipes": {
            "current": recipe_count,
            "max": org.max_recipes,
            "available": org.max_recipes - recipe_count if org.max_recipes > 0 else -1,
            "limit_reached": recipe_count >= org.max_recipes if org.max_recipes > 0 else False
        },
        "distributors": {
            "current": distributor_count,
            "max": org.max_distributors,
            "available": org.max_distributors - distributor_count if org.max_distributors > 0 else -1,
            "limit_reached": distributor_count >= org.max_distributors if org.max_distributors > 0 else False
        },
        "ai_parses": {
            "used_this_month": org.ai_parses_used_this_month,
            "max": org.max_ai_parses_per_month,
            "available": org.max_ai_parses_per_month - org.ai_parses_used_this_month if org.max_ai_parses_per_month > 0 else -1,
            "limit_reached": org.ai_parses_used_this_month >= org.max_ai_parses_per_month if org.max_ai_parses_per_month > 0 else False
        }
    }
