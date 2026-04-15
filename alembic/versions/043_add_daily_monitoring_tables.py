"""Add daily monitoring core tables

Revision ID: 043
Revises: 042
Create Date: 2026-04-14

Phase 2 of Daily Monitoring Module:
- daily_worksheet: Container for each outlet's daily monitoring entries
- cooler_reading: Individual temperature readings for coolers/freezers (Record 3)
- daily_edit_log: Audit trail for any edits made after initial entry

The daily worksheet is a "living document" for the day that multiple people
contribute to across shifts. Auto-save on each field, no submit button.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '043'
down_revision: Union[str, Sequence[str], None] = '042'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create daily monitoring tables."""

    # ============================================
    # Table: daily_worksheet
    # One record per outlet per date - the "container" for the day
    # ============================================
    op.create_table('daily_worksheet',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Outlet name (string, matches ehc_outlet pattern - not FK for flexibility)
        sa.Column('outlet_name', sa.String(length=50), nullable=False),

        # The date this worksheet covers
        sa.Column('worksheet_date', sa.Date(), nullable=False),

        # Workflow status
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        # 'open' - Active, accepting entries
        # 'review' - Day complete, pending manager review
        # 'approved' - Manager approved, locked

        # Approval tracking
        sa.Column('approved_by', sa.Integer(), nullable=True),  # FK to users
        sa.Column('approved_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_daily_worksheet_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'],
                                name='fk_daily_worksheet_approved_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'outlet_name', 'worksheet_date',
                            name='uq_daily_worksheet_org_outlet_date')
    )

    op.create_index('idx_daily_worksheet_org', 'daily_worksheet', ['organization_id'])
    op.create_index('idx_daily_worksheet_date', 'daily_worksheet', ['worksheet_date'])
    op.create_index('idx_daily_worksheet_status', 'daily_worksheet', ['status'])
    op.create_index('idx_daily_worksheet_outlet', 'daily_worksheet', ['organization_id', 'outlet_name'])

    # ============================================
    # Table: cooler_reading
    # Individual temperature readings for coolers/freezers (Record 3)
    # ============================================
    op.create_table('cooler_reading',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('worksheet_id', UUID(as_uuid=True), nullable=False),

        # Which unit: 'cooler' or 'freezer'
        sa.Column('unit_type', sa.String(length=20), nullable=False),

        # Sequential number within type (1, 2, 3...)
        sa.Column('unit_number', sa.SmallInteger(), nullable=False),

        # Which shift: 'am' or 'pm'
        sa.Column('shift', sa.String(length=10), nullable=False),

        # The temperature reading (nullable = not yet recorded)
        sa.Column('temperature_f', sa.Numeric(precision=5, scale=1), nullable=True),

        # Auto-set when exceeds threshold
        sa.Column('is_flagged', sa.Boolean(), nullable=False, server_default='false'),

        # Corrective action if flagged
        sa.Column('corrective_action', sa.Text(), nullable=True),

        # Optional ALICE ticket reference
        sa.Column('alice_ticket', sa.String(length=50), nullable=True),

        # Who recorded this (staff initials or name)
        sa.Column('recorded_by', sa.String(length=100), nullable=True),

        # Signature for this shift's reading (base64 PNG)
        sa.Column('signature_data', sa.Text(), nullable=True),

        # When the value was actually entered (for audit trail)
        sa.Column('recorded_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['worksheet_id'], ['daily_worksheet.id'],
                                name='fk_cooler_reading_worksheet', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('worksheet_id', 'unit_type', 'unit_number', 'shift',
                            name='uq_cooler_reading_unit_shift')
    )

    op.create_index('idx_cooler_reading_worksheet', 'cooler_reading', ['worksheet_id'])
    op.create_index('idx_cooler_reading_flagged', 'cooler_reading', ['is_flagged'])

    # ============================================
    # Table: daily_edit_log
    # Audit trail for any edits made after initial entry
    # ============================================
    op.create_table('daily_edit_log',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Which table was edited
        sa.Column('table_name', sa.String(length=50), nullable=False),

        # PK of the edited record
        sa.Column('record_id', UUID(as_uuid=True), nullable=False),

        # Which field changed
        sa.Column('field_name', sa.String(length=50), nullable=False),

        # Old and new values
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),

        # Required for next-day edits
        sa.Column('edit_reason', sa.Text(), nullable=True),

        # Who made the edit
        sa.Column('edited_by', sa.String(length=100), nullable=True),

        # When the edit was made
        sa.Column('edited_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_daily_edit_log_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_daily_edit_log_org', 'daily_edit_log', ['organization_id'])
    op.create_index('idx_daily_edit_log_record', 'daily_edit_log', ['table_name', 'record_id'])
    op.create_index('idx_daily_edit_log_date', 'daily_edit_log', ['edited_at'])

    print("Created daily monitoring tables:")
    print("  - daily_worksheet: Container for each outlet's daily entries")
    print("  - cooler_reading: Temperature readings for coolers/freezers")
    print("  - daily_edit_log: Audit trail for edits")


def downgrade() -> None:
    """Remove daily monitoring tables."""

    op.drop_index('idx_daily_edit_log_date', 'daily_edit_log')
    op.drop_index('idx_daily_edit_log_record', 'daily_edit_log')
    op.drop_index('idx_daily_edit_log_org', 'daily_edit_log')
    op.drop_table('daily_edit_log')

    op.drop_index('idx_cooler_reading_flagged', 'cooler_reading')
    op.drop_index('idx_cooler_reading_worksheet', 'cooler_reading')
    op.drop_table('cooler_reading')

    op.drop_index('idx_daily_worksheet_outlet', 'daily_worksheet')
    op.drop_index('idx_daily_worksheet_status', 'daily_worksheet')
    op.drop_index('idx_daily_worksheet_date', 'daily_worksheet')
    op.drop_index('idx_daily_worksheet_org', 'daily_worksheet')
    op.drop_table('daily_worksheet')

    print("Removed daily monitoring tables")
