"""Add EHC responsibility code management table

Revision ID: 035
Revises: 034
Create Date: 2026-04-04

EHC Settings - Responsibility Codes:
- ehc_responsibility_code: User-defined responsibility codes (MM, CF, CM, etc.)
- Admin defines what each code means (role and scope)
- Used for audit point assignments and record filtering
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '035'
down_revision: Union[str, Sequence[str], None] = '034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EHC responsibility code management table."""

    # ============================================
    # Table: ehc_responsibility_code
    # User-defined responsibility codes
    # ============================================
    op.create_table('ehc_responsibility_code',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Short code: "MM", "CF", "CM", "AM", "ENG", "FF", "EHC"
        sa.Column('code', sa.String(length=10), nullable=False),

        # Admin-defined role name and scope (start blank, user fills in)
        sa.Column('role_name', sa.String(length=255), nullable=True),
        sa.Column('scope', sa.Text(), nullable=True),

        # Soft delete flag
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # For manual ordering in UI
        sa.Column('sort_order', sa.SmallInteger(), nullable=False, server_default='0'),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_ehc_resp_code_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'code', name='uq_ehc_resp_code_org_code')
    )

    # Indexes for efficient querying
    op.create_index('idx_ehc_resp_code_org', 'ehc_responsibility_code', ['organization_id'])
    op.create_index('idx_ehc_resp_code_active', 'ehc_responsibility_code', ['is_active'])

    print("EHC responsibility code management table created (ehc_responsibility_code)")


def downgrade() -> None:
    """Remove EHC responsibility code management table."""

    op.drop_index('idx_ehc_resp_code_active', 'ehc_responsibility_code')
    op.drop_index('idx_ehc_resp_code_org', 'ehc_responsibility_code')
    op.drop_table('ehc_responsibility_code')

    print("EHC responsibility code management table removed")
