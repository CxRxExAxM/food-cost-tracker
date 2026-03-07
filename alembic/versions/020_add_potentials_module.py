"""Add potentials module tables

Revision ID: 020
Revises: 019
Create Date: 2025-03-07

Potentials module - F&B Planning Dashboard:
- Events table for hitlist events (organization-scoped)
- Forecast metrics table for daily forecast data
- Group rooms table for per-group room data
- Import log table for tracking file imports
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '020'
down_revision: Union[str, Sequence[str], None] = '019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add potentials module infrastructure."""

    # ============================================
    # Table 1: potentials_events
    # Stores all hitlist events, deduplicated by event_id within organization
    # ============================================
    op.create_table('potentials_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),  # Opera event ID

        # Event details
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('booking_name', sa.String(length=255), nullable=True),
        sa.Column('event_name', sa.String(length=255), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),  # breakfast, lunch, dinner, reception
        sa.Column('venue', sa.String(length=255), nullable=True),
        sa.Column('time', sa.String(length=50), nullable=True),
        sa.Column('attendees', sa.Integer(), nullable=True),
        sa.Column('gtd', sa.Integer(), nullable=True),  # Guaranteed count
        sa.Column('notes', sa.Text(), nullable=True),

        # Import tracking
        sa.Column('source_file', sa.String(length=255), nullable=True),
        sa.Column('imported_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_potentials_events_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'event_id', name='unique_event_per_org')
    )

    # Indexes for potentials_events
    op.create_index('idx_potentials_events_org', 'potentials_events', ['organization_id'])
    op.create_index('idx_potentials_events_date', 'potentials_events', ['date'])
    op.create_index('idx_potentials_events_category', 'potentials_events', ['category'])
    op.create_index('idx_potentials_events_booking', 'potentials_events', ['booking_name'])

    # ============================================
    # Table 2: potentials_forecast_metrics
    # Stores forecast data by date + metric name
    # ============================================
    op.create_table('potentials_forecast_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Numeric(12, 2), nullable=True),

        # Import tracking
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('source_file', sa.String(length=255), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_potentials_forecast_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'date', 'metric_name', name='unique_forecast_metric')
    )

    # Indexes for potentials_forecast_metrics
    op.create_index('idx_potentials_forecast_org', 'potentials_forecast_metrics', ['organization_id'])
    op.create_index('idx_potentials_forecast_date', 'potentials_forecast_metrics', ['date'])

    # ============================================
    # Table 3: potentials_group_rooms
    # Per-group daily room data (arrivals, departures, rooms in-house)
    # ============================================
    op.create_table('potentials_group_rooms',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        sa.Column('block_code', sa.String(length=100), nullable=True),
        sa.Column('block_name', sa.String(length=255), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('rooms', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('arrivals', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('departures', sa.Integer(), nullable=True, server_default='0'),

        # Import tracking
        sa.Column('source_file', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_potentials_group_rooms_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'block_code', 'date', name='unique_group_room_date')
    )

    # Indexes for potentials_group_rooms
    op.create_index('idx_potentials_group_rooms_org', 'potentials_group_rooms', ['organization_id'])
    op.create_index('idx_potentials_group_rooms_date', 'potentials_group_rooms', ['date'])
    op.create_index('idx_potentials_group_rooms_block', 'potentials_group_rooms', ['block_name'])

    # ============================================
    # Table 4: potentials_import_log
    # Tracks file imports for audit and status
    # ============================================
    op.create_table('potentials_import_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        sa.Column('filename', sa.String(length=255), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),  # 'hitlist' or 'forecast'
        sa.Column('imported_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('records_added', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('records_updated', sa.Integer(), nullable=True, server_default='0'),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_potentials_import_log_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for potentials_import_log
    op.create_index('idx_potentials_import_log_org', 'potentials_import_log', ['organization_id'])
    op.create_index('idx_potentials_import_log_type', 'potentials_import_log', ['file_type'])

    print("Potentials module tables created")


def downgrade() -> None:
    """Remove potentials module infrastructure."""

    # Drop indexes and tables in reverse order
    op.drop_index('idx_potentials_import_log_type', 'potentials_import_log')
    op.drop_index('idx_potentials_import_log_org', 'potentials_import_log')
    op.drop_table('potentials_import_log')

    op.drop_index('idx_potentials_group_rooms_block', 'potentials_group_rooms')
    op.drop_index('idx_potentials_group_rooms_date', 'potentials_group_rooms')
    op.drop_index('idx_potentials_group_rooms_org', 'potentials_group_rooms')
    op.drop_table('potentials_group_rooms')

    op.drop_index('idx_potentials_forecast_date', 'potentials_forecast_metrics')
    op.drop_index('idx_potentials_forecast_org', 'potentials_forecast_metrics')
    op.drop_table('potentials_forecast_metrics')

    op.drop_index('idx_potentials_events_booking', 'potentials_events')
    op.drop_index('idx_potentials_events_category', 'potentials_events')
    op.drop_index('idx_potentials_events_date', 'potentials_events')
    op.drop_index('idx_potentials_events_org', 'potentials_events')
    op.drop_table('potentials_events')

    print("Potentials module tables removed")
