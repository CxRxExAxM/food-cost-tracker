"""Add daily monitoring configuration fields to ehc_outlet

Revision ID: 042
Revises: 041
Create Date: 2026-04-14

Phase 1 of Daily Monitoring Module:
- Equipment counts (coolers, freezers)
- Capability toggles (cooking, cooling, thawing, buffets)
- Meal period configuration (breakfast, lunch, dinner)
- Temperature thresholds for auto-flagging
- Master enable toggle for the feature

These fields configure what appears on each outlet's daily worksheet.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '042'
down_revision: Union[str, Sequence[str], None] = '041'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add daily monitoring configuration fields to ehc_outlet."""

    # ============================================
    # Equipment Counts
    # How many coolers/freezers does this outlet have?
    # ============================================
    op.add_column('ehc_outlet', sa.Column(
        'cooler_count', sa.Integer(), nullable=False, server_default='0'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'freezer_count', sa.Integer(), nullable=False, server_default='0'
    ))

    # ============================================
    # Capability Toggles
    # Which sections appear on the daily worksheet?
    # ============================================
    op.add_column('ehc_outlet', sa.Column(
        'has_cooking', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'has_cooling', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'has_thawing', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'has_hot_buffet', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'has_cold_buffet', sa.Boolean(), nullable=False, server_default='false'
    ))

    # ============================================
    # Meal Period Configuration
    # Which meal periods does this outlet serve?
    # ============================================
    op.add_column('ehc_outlet', sa.Column(
        'serves_breakfast', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'serves_lunch', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'serves_dinner', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'readings_per_service', sa.Integer(), nullable=False, server_default='3'
    ))

    # ============================================
    # Temperature Thresholds
    # Auto-flag readings outside these ranges
    # Defaults from Fairmont Safe Food and Hygiene Standards
    # ============================================
    op.add_column('ehc_outlet', sa.Column(
        'cooler_max_f', sa.Numeric(precision=5, scale=1), nullable=False, server_default='41.0'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'freezer_max_f', sa.Numeric(precision=5, scale=1), nullable=False, server_default='0.0'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'cook_min_f', sa.Numeric(precision=5, scale=1), nullable=False, server_default='165.0'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'reheat_min_f', sa.Numeric(precision=5, scale=1), nullable=False, server_default='165.0'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'hot_hold_min_f', sa.Numeric(precision=5, scale=1), nullable=False, server_default='140.0'
    ))
    op.add_column('ehc_outlet', sa.Column(
        'cold_hold_max_f', sa.Numeric(precision=5, scale=1), nullable=False, server_default='41.0'
    ))

    # ============================================
    # Master Toggle
    # Enable/disable daily monitoring for this outlet
    # ============================================
    op.add_column('ehc_outlet', sa.Column(
        'daily_monitoring_enabled', sa.Boolean(), nullable=False, server_default='false'
    ))

    print("Added daily monitoring configuration fields to ehc_outlet:")
    print("  - Equipment counts: cooler_count, freezer_count")
    print("  - Capabilities: has_cooking, has_cooling, has_thawing, has_hot_buffet, has_cold_buffet")
    print("  - Meal periods: serves_breakfast, serves_lunch, serves_dinner, readings_per_service")
    print("  - Thresholds: cooler_max_f, freezer_max_f, cook_min_f, reheat_min_f, hot_hold_min_f, cold_hold_max_f")
    print("  - Master toggle: daily_monitoring_enabled")


def downgrade() -> None:
    """Remove daily monitoring configuration fields from ehc_outlet."""

    # Remove in reverse order of addition
    op.drop_column('ehc_outlet', 'daily_monitoring_enabled')

    op.drop_column('ehc_outlet', 'cold_hold_max_f')
    op.drop_column('ehc_outlet', 'hot_hold_min_f')
    op.drop_column('ehc_outlet', 'reheat_min_f')
    op.drop_column('ehc_outlet', 'cook_min_f')
    op.drop_column('ehc_outlet', 'freezer_max_f')
    op.drop_column('ehc_outlet', 'cooler_max_f')

    op.drop_column('ehc_outlet', 'readings_per_service')
    op.drop_column('ehc_outlet', 'serves_dinner')
    op.drop_column('ehc_outlet', 'serves_lunch')
    op.drop_column('ehc_outlet', 'serves_breakfast')

    op.drop_column('ehc_outlet', 'has_cold_buffet')
    op.drop_column('ehc_outlet', 'has_hot_buffet')
    op.drop_column('ehc_outlet', 'has_thawing')
    op.drop_column('ehc_outlet', 'has_cooling')
    op.drop_column('ehc_outlet', 'has_cooking')

    op.drop_column('ehc_outlet', 'freezer_count')
    op.drop_column('ehc_outlet', 'cooler_count')

    print("Removed daily monitoring configuration fields from ehc_outlet")
