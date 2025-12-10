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
    """Upgrade schema."""
    # SQLite requires batch mode for altering tables with constraints
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        # Add max_users column
        batch_op.add_column(sa.Column('max_users', sa.Integer(), server_default='2', nullable=True))

        # Drop and recreate check constraint for subscription_tier
        batch_op.drop_constraint('check_subscription_tier', type_='check')
        batch_op.create_check_constraint(
            'check_subscription_tier',
            "subscription_tier IN ('free', 'basic', 'pro', 'enterprise')"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        # Remove max_users column
        batch_op.drop_column('max_users')

        # Revert check constraint to original values
        batch_op.drop_constraint('check_subscription_tier', type_='check')
        batch_op.create_check_constraint(
            'check_subscription_tier',
            "subscription_tier IN ('free', 'paid', 'enterprise')"
        )
