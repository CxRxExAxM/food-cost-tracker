"""add ai recipe parser support

Revision ID: 005
Revises: 5e7f498e6bd8
Create Date: 2025-12-17

Adds support for AI-powered recipe parsing:
- ai_parse_usage table to track parsing attempts and usage limits
- Fields to recipes table to mark AI-imported recipes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, Sequence[str], None] = '5e7f498e6bd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ============================================
    # Step 1: Create ai_parse_usage table
    # ============================================
    op.execute("""
        CREATE TABLE ai_parse_usage (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            outlet_id INTEGER NOT NULL REFERENCES outlets(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(10) NOT NULL,
            parse_status VARCHAR(20) NOT NULL,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
            ingredients_count INTEGER,
            matched_count INTEGER,
            error_message TEXT,
            parse_time_ms INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT check_parse_status CHECK (parse_status IN ('success', 'partial', 'failed'))
        )
    """)

    # Create indexes for performance and rate limiting
    op.execute("CREATE INDEX idx_ai_parse_organization ON ai_parse_usage(organization_id)")
    op.execute("CREATE INDEX idx_ai_parse_user ON ai_parse_usage(user_id)")
    op.execute("CREATE INDEX idx_ai_parse_created ON ai_parse_usage(created_at)")
    op.execute("CREATE INDEX idx_ai_parse_status ON ai_parse_usage(parse_status)")
    op.execute("CREATE INDEX idx_ai_parse_recent_attempts ON ai_parse_usage(organization_id, created_at)")

    # ============================================
    # Step 2: Add AI import tracking to recipes
    # ============================================
    op.add_column('recipes', sa.Column('imported_from_ai', sa.Boolean(), server_default='false'))
    op.add_column('recipes', sa.Column('import_filename', sa.String(255), nullable=True))

    print("✅ AI recipe parser infrastructure created")


def downgrade() -> None:
    """Downgrade schema."""

    # Remove columns from recipes
    op.drop_column('recipes', 'import_filename')
    op.drop_column('recipes', 'imported_from_ai')

    # Drop ai_parse_usage table
    op.execute("DROP TABLE IF EXISTS ai_parse_usage")

    print("✅ AI recipe parser infrastructure removed")
