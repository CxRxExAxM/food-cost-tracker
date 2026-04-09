"""add waste weigh-in tokens and submissions

Revision ID: 038
Revises: 037
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '038'
down_revision = '037'
branch_labels = None
depends_on = None


def upgrade():
    # Create waste_weigh_in_tokens table
    op.create_table(
        'waste_weigh_in_tokens',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('organization_id', sa.Integer, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(50), nullable=False, unique=True),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('qr_code_base64', sa.Text, nullable=True),
        sa.Column('active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    )

    # Create waste_weigh_ins table
    op.create_table(
        'waste_weigh_ins',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('organization_id', sa.Integer, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_id', sa.Integer, sa.ForeignKey('waste_weigh_in_tokens.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recorded_date', sa.Date, nullable=False),
        sa.Column('category', sa.String(20), nullable=False),  # 'donation' or 'compost'
        sa.Column('weight_lbs', sa.Numeric(10, 2), nullable=False),
        sa.Column('submitted_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('submitted_by_name', sa.String(100), nullable=True)  # Optional staff name
    )

    # Create indexes
    op.create_index('idx_weigh_in_tokens_org', 'waste_weigh_in_tokens', ['organization_id'])
    op.create_index('idx_weigh_in_tokens_token', 'waste_weigh_in_tokens', ['token'])
    op.create_index('idx_weigh_ins_token', 'waste_weigh_ins', ['token_id'])
    op.create_index('idx_weigh_ins_date', 'waste_weigh_ins', ['recorded_date'])


def downgrade():
    op.drop_index('idx_weigh_ins_date')
    op.drop_index('idx_weigh_ins_token')
    op.drop_index('idx_weigh_in_tokens_token')
    op.drop_index('idx_weigh_in_tokens_org')
    op.drop_table('waste_weigh_ins')
    op.drop_table('waste_weigh_in_tokens')
