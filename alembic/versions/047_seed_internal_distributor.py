"""Seed an Internal / Housemade distributor

Revision ID: 047
Revises: 046
Create Date: 2026-06-25

Adds a global "Internal / Housemade" vendor so products that have no external
supplier (in-house preparations, sub-recipes sold as products, items awaiting
an invoice import) can still be created with a distributor link and therefore
carry a price in price_history. Pricing is keyed on distributor_products, so a
product needs *some* distributor to hold a price.

Idempotent: ON CONFLICT on the unique name/code does nothing, so re-running is
safe and it won't clobber a row an admin may have created via the new
POST /distributors endpoint.
"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '047'
down_revision: Union[str, Sequence[str], None] = '046'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO distributors (name, code, is_active)
        VALUES ('Internal / Housemade', 'internal', 1)
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    # Only remove the seeded row if nothing references it, to avoid cascading
    # deletes of distributor_products/price_history created against it.
    op.execute("""
        DELETE FROM distributors d
        WHERE d.code = 'internal'
          AND NOT EXISTS (
              SELECT 1 FROM distributor_products dp WHERE dp.distributor_id = d.id
          )
    """)
