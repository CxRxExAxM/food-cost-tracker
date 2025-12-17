"""add_audit_logs_table

Revision ID: 5e7f498e6bd8
Revises: 004
Create Date: 2025-12-17 14:46:48.048034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e7f498e6bd8'
down_revision: Union[str, Sequence[str], None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
            action VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50),
            entity_id INTEGER,
            changes JSON,
            ip_address VARCHAR(45),
            impersonating BOOLEAN DEFAULT FALSE,
            original_super_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for common queries
    op.execute("CREATE INDEX idx_audit_logs_org_id ON audit_logs(organization_id)")
    op.execute("CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id)")
    op.execute("CREATE INDEX idx_audit_logs_action ON audit_logs(action)")
    op.execute("CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS audit_logs")
