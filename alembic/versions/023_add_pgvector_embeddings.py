"""Add pgvector extension and embeddings to common_products

Revision ID: 023
Revises: 022
Create Date: 2026-03-24

Adds semantic search capability for ingredient matching:
- Enables pgvector extension
- Adds embedding column to common_products
- Creates IVFFlat index for fast similarity search
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    # Enable pgvector extension
    # Note: On Render PostgreSQL, this should work out of the box
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Add embedding column to common_products
    # Using 1024 dimensions (Voyage AI voyage-3.5-lite default)
    op.execute('ALTER TABLE common_products ADD COLUMN embedding vector(1024)')

    # Create IVFFlat index for fast approximate nearest neighbor search
    # Using cosine distance (vector_cosine_ops) which works well for normalized embeddings
    # lists=100 is a good default for tables with <100k rows
    op.execute('''
        CREATE INDEX idx_common_products_embedding
        ON common_products
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    ''')


def downgrade():
    op.execute('DROP INDEX IF EXISTS idx_common_products_embedding')
    op.execute('ALTER TABLE common_products DROP COLUMN IF EXISTS embedding')
    # Note: Not dropping the extension as other tables might use it
