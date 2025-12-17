"""
Audit logging utilities for tracking critical system actions.
"""
from typing import Optional, Dict, Any
from .database import get_db
import json


def log_audit(
    action: str,
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    changes: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    impersonating: bool = False,
    original_super_admin_id: Optional[int] = None
):
    """
    Log an audit event to the audit_logs table.

    Args:
        action: The action being performed (e.g., 'user_created', 'subscription_updated')
        user_id: ID of the user performing the action
        organization_id: ID of the organization affected
        entity_type: Type of entity affected (e.g., 'user', 'organization', 'outlet')
        entity_id: ID of the specific entity affected
        changes: Dictionary of changes (before/after values)
        ip_address: IP address of the requester
        impersonating: Whether this action was performed while impersonating
        original_super_admin_id: If impersonating, the ID of the super admin
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Convert changes dict to JSON string
            changes_json = json.dumps(changes) if changes else None

            cursor.execute("""
                INSERT INTO audit_logs (
                    user_id,
                    organization_id,
                    action,
                    entity_type,
                    entity_id,
                    changes,
                    ip_address,
                    impersonating,
                    original_super_admin_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                organization_id,
                action,
                entity_type,
                entity_id,
                changes_json,
                ip_address,
                1 if impersonating else 0,
                original_super_admin_id
            ))

            conn.commit()
    except Exception as e:
        # Fail gracefully if audit_logs table doesn't exist yet
        # This allows endpoints to work even if migration hasn't run
        print(f"Warning: Failed to log audit event: {e}")


# Action constants for consistency
class AuditAction:
    # User actions
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    USER_PASSWORD_RESET = "user_password_reset"
    USER_ROLE_CHANGED = "user_role_changed"

    # Organization actions
    ORG_CREATED = "organization_created"
    ORG_UPDATED = "organization_updated"
    ORG_SUSPENDED = "organization_suspended"
    ORG_ACTIVATED = "organization_activated"
    SUBSCRIPTION_UPDATED = "subscription_updated"

    # Outlet actions
    OUTLET_ASSIGNED = "outlet_assigned"
    OUTLET_UNASSIGNED = "outlet_unassigned"
    OUTLET_ASSIGNMENTS_UPDATED = "outlet_assignments_updated"

    # Impersonation actions
    IMPERSONATION_STARTED = "impersonation_started"
    IMPERSONATION_ENDED = "impersonation_ended"


# Entity type constants
class EntityType:
    USER = "user"
    ORGANIZATION = "organization"
    OUTLET = "outlet"
    PRODUCT = "product"
    RECIPE = "recipe"
