"""Add cooking, cooling, and thawing record tables

Revision ID: 044
Revises: 043
Create Date: 2026-04-15

Phase 3 of Daily Monitoring Module:
- cooking_record: Cook/reheat/holding entries (Records 4 & 6)
- cooling_record: Cooling log entries (Record 5)
- thawing_record: Thawing log entries (Record 12)

These tables follow the same pattern as cooler_reading:
- Linked to daily_worksheet
- Auto-flagging when thresholds exceeded
- Corrective action capture
- Signature support
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '044'
down_revision: Union[str, Sequence[str], None] = '043'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create cooking, cooling, and thawing record tables."""

    # ============================================
    # Table: cooking_record
    # Cook/reheat/holding entries (Records 4 & 6)
    # ============================================
    op.create_table('cooking_record',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('worksheet_id', UUID(as_uuid=True), nullable=False),

        # Meal period: 'breakfast' | 'lunch' | 'dinner'
        sa.Column('meal_period', sa.String(length=20), nullable=False),

        # Entry type: 'cook' | 'reheat' | 'hot_hold' | 'cold_hold'
        sa.Column('entry_type', sa.String(length=20), nullable=False),

        # Sequential within meal period (1, 2, 3...)
        sa.Column('slot_number', sa.SmallInteger(), nullable=False),

        # What was temped (user enters)
        sa.Column('item_name', sa.String(length=200), nullable=True),

        # The temperature reading
        sa.Column('temperature_f', sa.Numeric(precision=5, scale=1), nullable=True),

        # Time the temp was taken
        sa.Column('time_recorded', sa.Time(), nullable=True),

        # Auto-set when below/above threshold
        sa.Column('is_flagged', sa.Boolean(), nullable=False, server_default='false'),

        # Corrective action if flagged
        sa.Column('corrective_action', sa.Text(), nullable=True),

        # Optional ALICE ticket reference
        sa.Column('alice_ticket', sa.String(length=50), nullable=True),

        # Who recorded this
        sa.Column('recorded_by', sa.String(length=100), nullable=True),

        # Signature for this entry (base64 PNG)
        sa.Column('signature_data', sa.Text(), nullable=True),

        # When the value was actually entered
        sa.Column('recorded_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['worksheet_id'], ['daily_worksheet.id'],
                                name='fk_cooking_record_worksheet', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_cooking_record_worksheet', 'cooking_record', ['worksheet_id'])
    op.create_index('idx_cooking_record_meal', 'cooking_record', ['worksheet_id', 'meal_period'])
    op.create_index('idx_cooking_record_flagged', 'cooking_record', ['is_flagged'])

    # ============================================
    # Table: cooling_record
    # Cooling log entries (Record 5)
    # ============================================
    op.create_table('cooling_record',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('worksheet_id', UUID(as_uuid=True), nullable=False),

        # What item is being cooled
        sa.Column('item_name', sa.String(length=200), nullable=False),

        # When cooling began
        sa.Column('start_time', sa.DateTime(), nullable=True),

        # When cooling completed
        sa.Column('end_time', sa.DateTime(), nullable=True),

        # Temp after 2 hours (must be <= 70F)
        sa.Column('temp_2hr_f', sa.Numeric(precision=5, scale=1), nullable=True),

        # Temp after 6 hours (must be <= 41F)
        sa.Column('temp_6hr_f', sa.Numeric(precision=5, scale=1), nullable=True),

        # Cooling method: 'ambient' | 'blast_chill' | 'ice_bath' | 'shallow_pan' | 'other'
        sa.Column('method', sa.String(length=30), nullable=True),

        # Auto-set when temps exceed thresholds
        sa.Column('is_flagged', sa.Boolean(), nullable=False, server_default='false'),

        # Corrective action if flagged
        sa.Column('corrective_action', sa.Text(), nullable=True),

        # Optional ALICE ticket reference
        sa.Column('alice_ticket', sa.String(length=50), nullable=True),

        # Who recorded this
        sa.Column('recorded_by', sa.String(length=100), nullable=True),

        # Signature (base64 PNG)
        sa.Column('signature_data', sa.Text(), nullable=True),

        # When the value was actually entered
        sa.Column('recorded_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['worksheet_id'], ['daily_worksheet.id'],
                                name='fk_cooling_record_worksheet', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_cooling_record_worksheet', 'cooling_record', ['worksheet_id'])
    op.create_index('idx_cooling_record_flagged', 'cooling_record', ['is_flagged'])

    # ============================================
    # Table: thawing_record
    # Thawing log entries (Record 12)
    # ============================================
    op.create_table('thawing_record',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('worksheet_id', UUID(as_uuid=True), nullable=False),

        # What item is being thawed
        sa.Column('item_name', sa.String(length=200), nullable=False),

        # When thawing began
        sa.Column('start_time', sa.DateTime(), nullable=True),

        # Finish date (may be next day for walk-in thawing)
        sa.Column('finish_date', sa.Date(), nullable=True),

        # Finish time
        sa.Column('finish_time', sa.Time(), nullable=True),

        # Final temp (must be <= 41F)
        sa.Column('finish_temp_f', sa.Numeric(precision=5, scale=1), nullable=True),

        # Thawing method: 'walkin' | 'running_water' | 'microwave' | 'cooking' | 'other'
        sa.Column('method', sa.String(length=30), nullable=True),

        # Auto-set when finish temp exceeds threshold
        sa.Column('is_flagged', sa.Boolean(), nullable=False, server_default='false'),

        # Corrective action if flagged
        sa.Column('corrective_action', sa.Text(), nullable=True),

        # Optional ALICE ticket reference
        sa.Column('alice_ticket', sa.String(length=50), nullable=True),

        # Who recorded this
        sa.Column('recorded_by', sa.String(length=100), nullable=True),

        # Signature (base64 PNG)
        sa.Column('signature_data', sa.Text(), nullable=True),

        # When the value was actually entered
        sa.Column('recorded_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['worksheet_id'], ['daily_worksheet.id'],
                                name='fk_thawing_record_worksheet', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_thawing_record_worksheet', 'thawing_record', ['worksheet_id'])
    op.create_index('idx_thawing_record_flagged', 'thawing_record', ['is_flagged'])

    print("Created daily monitoring record tables:")
    print("  - cooking_record: Cook/reheat/holding entries (Records 4 & 6)")
    print("  - cooling_record: Cooling log entries (Record 5)")
    print("  - thawing_record: Thawing log entries (Record 12)")


def downgrade() -> None:
    """Remove cooking, cooling, and thawing record tables."""

    op.drop_index('idx_thawing_record_flagged', 'thawing_record')
    op.drop_index('idx_thawing_record_worksheet', 'thawing_record')
    op.drop_table('thawing_record')

    op.drop_index('idx_cooling_record_flagged', 'cooling_record')
    op.drop_index('idx_cooling_record_worksheet', 'cooling_record')
    op.drop_table('cooling_record')

    op.drop_index('idx_cooking_record_flagged', 'cooking_record')
    op.drop_index('idx_cooking_record_meal', 'cooking_record')
    op.drop_index('idx_cooking_record_worksheet', 'cooking_record')
    op.drop_table('cooking_record')

    print("Removed cooking, cooling, and thawing record tables")
