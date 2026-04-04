"""Add EHC outlet management table

Revision ID: 034
Revises: 033
Create Date: 2026-04-04

EHC Settings - Outlet Management:
- ehc_outlet: Master list of property areas (kitchens, restaurants, bars) with leader info
- Used as suggestion source for outlet selectors throughout EHC module
- NOT a foreign key constraint - decoupled design allows string-based references
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '034'
down_revision: Union[str, Sequence[str], None] = '033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EHC outlet management table."""

    # ============================================
    # Table: ehc_outlet
    # Managed master list of property areas
    # ============================================
    op.create_table('ehc_outlet',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Short name used as tag/pill: "MK", "Toro", "LaHa"
        sa.Column('name', sa.String(length=50), nullable=False),

        # Display name: "Main Kitchen", "Toro Latin Restaurant & Rum Bar"
        sa.Column('full_name', sa.String(length=255), nullable=True),

        # Outlet type for grouping: "Production Kitchen", "Restaurant", "Bar", etc.
        sa.Column('outlet_type', sa.String(length=50), nullable=True),

        # Optional leader contact info for future email distribution
        sa.Column('leader_name', sa.String(length=255), nullable=True),
        sa.Column('leader_email', sa.String(length=255), nullable=True),

        # Soft delete flag
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # For manual ordering in UI
        sa.Column('sort_order', sa.SmallInteger(), nullable=False, server_default='0'),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_ehc_outlet_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_ehc_outlet_org_name')
    )

    # Indexes for efficient querying
    op.create_index('idx_ehc_outlet_org', 'ehc_outlet', ['organization_id'])
    op.create_index('idx_ehc_outlet_active', 'ehc_outlet', ['is_active'])
    op.create_index('idx_ehc_outlet_type', 'ehc_outlet', ['outlet_type'])

    print("EHC outlet management table created (ehc_outlet)")


def downgrade() -> None:
    """Remove EHC outlet management table."""

    op.drop_index('idx_ehc_outlet_type', 'ehc_outlet')
    op.drop_index('idx_ehc_outlet_active', 'ehc_outlet')
    op.drop_index('idx_ehc_outlet_org', 'ehc_outlet')
    op.drop_table('ehc_outlet')

    print("EHC outlet management table removed")
