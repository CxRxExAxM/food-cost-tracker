"""add product_conversions table for user-defined unit conversions

Revision ID: 007
Revises: 006
Create Date: 2024-12-18

Adds support for user-defined unit conversions on common products:
- Example: "1 ea Banana = 5 oz" (conversion_factor: 5.0)
- Conversions are organization-scoped
- Applied automatically in recipe cost calculations
- Bidirectional conversions (can create reverse automatically)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, Sequence[str], None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create product_conversions table
    op.create_table(
        'product_conversions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('common_product_id', sa.Integer(), nullable=False),
        sa.Column('from_unit_id', sa.Integer(), nullable=False),
        sa.Column('to_unit_id', sa.Integer(), nullable=False),
        sa.Column('conversion_factor', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['common_product_id'], ['common_products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_unit_id'], ['units.id']),
        sa.ForeignKeyConstraint(['to_unit_id'], ['units.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # Create unique constraint to prevent duplicate conversions
    op.create_unique_constraint(
        'uq_product_conversion',
        'product_conversions',
        ['common_product_id', 'from_unit_id', 'to_unit_id']
    )

    # Create index for faster lookups
    op.create_index(
        'idx_product_conversions_common_product',
        'product_conversions',
        ['common_product_id']
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index('idx_product_conversions_common_product', table_name='product_conversions')
    op.drop_constraint('uq_product_conversion', 'product_conversions', type_='unique')
    op.drop_table('product_conversions')
