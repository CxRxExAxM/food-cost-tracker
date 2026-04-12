"""Add EHC contacts for settings tab

Revision ID: 040
Revises: 039
Create Date: 2026-04-11

Phase 2 of EHC Settings - Contact Management:
- ehc_contact: People involved in EHC (not necessarily users)
- ehc_contact_outlet: Many-to-many with is_primary flag
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '040'
down_revision: Union[str, Sequence[str], None] = '039'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EHC contact tables."""

    # ============================================
    # Table: ehc_contact
    # People involved in EHC at this property
    # NOT necessarily RestauranTek users (yet)
    # ============================================
    op.create_table('ehc_contact',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Contact info
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),  # "Executive Sous Chef"

        # Soft delete
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Optional link to RestauranTek user (populated later when they get accounts)
        sa.Column('user_id', sa.Integer(), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_ehc_contact_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name='fk_ehc_contact_user', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'email', name='uq_ehc_contact_org_email')
    )

    op.create_index('idx_ehc_contact_org', 'ehc_contact', ['organization_id'])
    op.create_index('idx_ehc_contact_active', 'ehc_contact', ['is_active'])
    op.create_index('idx_ehc_contact_user', 'ehc_contact', ['user_id'])

    # ============================================
    # Table: ehc_contact_outlet
    # Many-to-many: which contacts are assigned to which outlets
    # One contact can be primary for multiple outlets
    # One outlet can have one primary contact
    # ============================================
    op.create_table('ehc_contact_outlet',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('outlet_id', sa.Integer(), nullable=False),

        # Is this the primary contact for this outlet?
        # When deploying forms, system looks up primary contact for auto-email
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['contact_id'], ['ehc_contact.id'],
                                name='fk_ehc_contact_outlet_contact', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outlet_id'], ['ehc_outlet.id'],
                                name='fk_ehc_contact_outlet_outlet', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contact_id', 'outlet_id', name='uq_ehc_contact_outlet')
    )

    op.create_index('idx_ehc_contact_outlet_contact', 'ehc_contact_outlet', ['contact_id'])
    op.create_index('idx_ehc_contact_outlet_outlet', 'ehc_contact_outlet', ['outlet_id'])
    op.create_index('idx_ehc_contact_outlet_primary', 'ehc_contact_outlet', ['outlet_id', 'is_primary'])

    print("EHC contact tables created (ehc_contact, ehc_contact_outlet)")


def downgrade() -> None:
    """Remove EHC contact tables."""

    op.drop_index('idx_ehc_contact_outlet_primary', 'ehc_contact_outlet')
    op.drop_index('idx_ehc_contact_outlet_outlet', 'ehc_contact_outlet')
    op.drop_index('idx_ehc_contact_outlet_contact', 'ehc_contact_outlet')
    op.drop_table('ehc_contact_outlet')

    op.drop_index('idx_ehc_contact_user', 'ehc_contact')
    op.drop_index('idx_ehc_contact_active', 'ehc_contact')
    op.drop_index('idx_ehc_contact_org', 'ehc_contact')
    op.drop_table('ehc_contact')

    print("EHC contact tables removed")
