"""Add foh_manager role to users table constraint

Revision ID: 021
Revises: 020
Create Date: 2024-03-07

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the old constraint and add a new one with foh_manager
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_role")
    op.execute("""
        ALTER TABLE users ADD CONSTRAINT check_role
        CHECK (role IN ('admin', 'chef', 'viewer', 'foh_manager'))
    """)


def downgrade():
    # Revert to old constraint (will fail if any foh_manager users exist)
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_role")
    op.execute("""
        ALTER TABLE users ADD CONSTRAINT check_role
        CHECK (role IN ('admin', 'chef', 'viewer'))
    """)
