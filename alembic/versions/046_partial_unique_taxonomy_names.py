"""Partial unique indexes for active taxonomy names

Revision ID: 046
Revises: 045
Create Date: 2026-06-24

Replaces the all-rows unique constraints on base_ingredients.name and
common_products.(organization_id, common_name) with partial unique
indexes scoped to is_active = 1.

Why: with a soft-delete model (is_active 0/1), a full-table unique
constraint counts archived rows, so a name that was ever archived can
never be re-inserted. The app worked around this by "reactivating" the
old archived row and repointing it to a new taxonomy path — which
silently reattached any FKs (e.g. recipe_ingredients) still on that old
id. Scoping uniqueness to active rows lets archived names free up, so a
fresh INSERT is allowed and archived rows keep their original FK history.

The new indexes are also case-insensitive (LOWER(...)), matching the
duplicate checks the application already performs.
"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '046'
down_revision: Union[str, Sequence[str], None] = '045'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- common_products: org-scoped, case-insensitive, active-only ---
    op.execute("ALTER TABLE common_products DROP CONSTRAINT IF EXISTS unique_common_name_per_org")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_common_name_per_org_active
        ON common_products (organization_id, LOWER(common_name))
        WHERE is_active = 1
    """)

    # --- base_ingredients: global, case-insensitive, active-only ---
    op.execute("ALTER TABLE base_ingredients DROP CONSTRAINT IF EXISTS uq_base_ingredients_name")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_base_ingredients_name_active
        ON base_ingredients (LOWER(name))
        WHERE is_active = 1
    """)


def downgrade() -> None:
    # Restore the original all-rows unique constraints.
    op.execute("DROP INDEX IF EXISTS uq_base_ingredients_name_active")
    op.execute("ALTER TABLE base_ingredients ADD CONSTRAINT uq_base_ingredients_name UNIQUE (name)")

    op.execute("DROP INDEX IF EXISTS uq_common_name_per_org_active")
    op.execute("ALTER TABLE common_products ADD CONSTRAINT unique_common_name_per_org UNIQUE (organization_id, common_name)")
