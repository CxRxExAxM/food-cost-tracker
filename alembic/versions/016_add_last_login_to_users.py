"""Add last_login column to users table

Revision ID: 016
Revises: 015
Create Date: 2025-01-29
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add last_login timestamp column to track when users last logged in
    op.add_column('users',
        sa.Column('last_login', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'last_login')
