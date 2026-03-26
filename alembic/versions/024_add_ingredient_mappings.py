"""Add ingredient_mappings table for learning loop

Revision ID: 024
Revises: 023
Create Date: 2026-03-26

Records user ingredient->product mappings to improve future AI recipe parsing.
Supports three-tier security model for future network effect feature.
See Architecture Notes in Notion for full design context.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    # Create ingredient_mappings table
    op.create_table(
        'ingredient_mappings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),

        # Raw text from recipe/invoice parsing (normalized to lowercase)
        sa.Column('raw_name', sa.String(255), nullable=False),

        # Links to common_products (future: base_ingredients/ingredient_variants)
        sa.Column('common_product_id', sa.Integer(), sa.ForeignKey('common_products.id', ondelete='SET NULL')),

        # Three-tier security model (ready for network effect)
        sa.Column('is_shared', sa.Boolean(), server_default='false'),

        # Match metadata
        sa.Column('confidence_score', sa.Float()),
        sa.Column('match_type', sa.String(20)),  # 'user_selected', 'accepted_suggestion', 'search'
        sa.Column('use_count', sa.Integer(), server_default='1'),

        # Audit trail
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
    )

    # Unique constraint: one mapping per raw_name per organization
    op.create_unique_constraint(
        'uq_ingredient_mappings_org_raw_name',
        'ingredient_mappings',
        ['organization_id', 'raw_name']
    )

    # Index for fast lookup during recipe parsing
    op.execute('''
        CREATE INDEX idx_ingredient_mappings_lookup
        ON ingredient_mappings(organization_id, LOWER(raw_name))
    ''')

    # Index for future network effect - query shared mappings across tenants
    op.execute('''
        CREATE INDEX idx_ingredient_mappings_shared
        ON ingredient_mappings(LOWER(raw_name))
        WHERE is_shared = TRUE
    ''')


def downgrade():
    op.execute('DROP INDEX IF EXISTS idx_ingredient_mappings_shared')
    op.execute('DROP INDEX IF EXISTS idx_ingredient_mappings_lookup')
    op.drop_constraint('uq_ingredient_mappings_org_raw_name', 'ingredient_mappings', type_='unique')
    op.drop_table('ingredient_mappings')
