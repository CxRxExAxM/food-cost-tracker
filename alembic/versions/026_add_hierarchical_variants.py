"""Add hierarchical variants support

Revision ID: 026
Revises: 025
Create Date: 2024-01-15

Adds parent_variant_id to ingredient_variants to support nested variant trees.
This allows organizing variants hierarchically:
  Beef (base)
  └── Brisket (variant, cut)
      └── Choice (variant, grade, parent=Brisket)
          └── Beef, Brisket, Choice (common product)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade():
    # Add parent_variant_id for hierarchical structure
    op.add_column('ingredient_variants',
        sa.Column('parent_variant_id', sa.Integer(),
                  sa.ForeignKey('ingredient_variants.id', ondelete='SET NULL'),
                  nullable=True)
    )

    # Add depth column to help with tree queries
    op.add_column('ingredient_variants',
        sa.Column('depth', sa.Integer(), nullable=True, server_default='0')
    )

    # Add index for efficient tree traversal
    op.create_index('ix_ingredient_variants_parent_id', 'ingredient_variants', ['parent_variant_id'])


def downgrade():
    op.drop_index('ix_ingredient_variants_parent_id', table_name='ingredient_variants')
    op.drop_column('ingredient_variants', 'depth')
    op.drop_column('ingredient_variants', 'parent_variant_id')
