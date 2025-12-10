"""add_max_users_to_organizations

Revision ID: cc2c3eef7f15
Revises: b87a96e83060
Create Date: 2025-12-09 18:06:09.894612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc2c3eef7f15'
down_revision: Union[str, Sequence[str], None] = 'b87a96e83060'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - PostgreSQL and SQLite compatible."""
    # Add max_users column
    op.add_column('organizations', sa.Column('max_users', sa.Integer(), server_default='2', nullable=True))

    # Drop and recreate check constraint for subscription_tier
    # Note: SQLite doesn't enforce constraint names, so drop_constraint might fail silently
    try:
        op.drop_constraint('check_subscription_tier', 'organizations', type_='check')
    except Exception:
        pass  # SQLite doesn't have named constraints, ignore

    op.create_check_constraint(
        'check_subscription_tier',
        'organizations',
        "subscription_tier IN ('free', 'basic', 'pro', 'enterprise')"
    )


def downgrade() -> None:
    """Downgrade schema - PostgreSQL and SQLite compatible."""
    # Remove max_users column
    op.drop_column('organizations', 'max_users')

    # Revert check constraint to original values
    try:
        op.drop_constraint('check_subscription_tier', 'organizations', type_='check')
    except Exception:
        pass  # SQLite doesn't have named constraints, ignore

    op.create_check_constraint(
        'check_subscription_tier',
        'organizations',
        "subscription_tier IN ('free', 'paid', 'enterprise')"
    )
