"""add prior year final to waste goals

Revision ID: 037
Revises: 036
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '037'
down_revision = '036'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('waste_goals', 
        sa.Column('prior_year_final', sa.Numeric(10, 2), nullable=True)
    )


def downgrade():
    op.drop_column('waste_goals', 'prior_year_final')
