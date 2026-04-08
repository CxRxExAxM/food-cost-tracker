"""add waste tracking tables

Revision ID: 036
Revises: 035
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '036'
down_revision = '035'
branch_labels = None
depends_on = None


def upgrade():
    # Create waste_goals table
    op.create_table(
        'waste_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('year', sa.Integer, nullable=False),
        sa.Column('target_grams_per_cover', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('organization_id', 'year', name='uq_waste_goals_org_year')
    )
    op.create_index('idx_waste_goals_org_year', 'waste_goals', ['organization_id', 'year'])

    # Create waste_monthly_metrics table
    op.create_table(
        'waste_monthly_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('year', sa.Integer, nullable=False),
        sa.Column('month', sa.Integer, nullable=False),
        sa.Column('fb_covers', sa.Integer, nullable=True),
        sa.Column('fte_count', sa.Integer, nullable=True),
        sa.Column('temp_count', sa.Integer, nullable=True),
        sa.Column('theoretic_capture_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('donation_lbs', sa.Numeric(10, 2), nullable=True),
        sa.Column('compost_lbs', sa.Numeric(10, 2), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('organization_id', 'year', 'month', name='uq_waste_monthly_metrics_org_year_month')
    )
    op.create_index('idx_waste_monthly_metrics_org_year', 'waste_monthly_metrics', ['organization_id', 'year'])

    # Create waste_qr_tokens table
    op.create_table(
        'waste_qr_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("category IN ('compost', 'donation')", name='ck_waste_qr_tokens_category')
    )
    op.create_index('idx_waste_qr_tokens_org_active', 'waste_qr_tokens', ['organization_id', 'is_active'])

    # Create waste_weigh_ins table
    op.create_table(
        'waste_weigh_ins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('waste_qr_tokens.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('weight_lbs', sa.Numeric(10, 2), nullable=False),
        sa.Column('recorded_date', sa.Date, nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("category IN ('compost', 'donation')", name='ck_waste_weigh_ins_category'),
        sa.CheckConstraint('weight_lbs >= 0', name='ck_waste_weigh_ins_weight_positive')
    )
    op.create_index('idx_waste_weigh_ins_org_date', 'waste_weigh_ins', ['organization_id', 'recorded_date'])
    op.create_index('idx_waste_weigh_ins_token', 'waste_weigh_ins', ['token_id'])


def downgrade():
    op.drop_table('waste_weigh_ins')
    op.drop_table('waste_qr_tokens')
    op.drop_table('waste_monthly_metrics')
    op.drop_table('waste_goals')
