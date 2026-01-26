"""Add base_conversions table for standard unit conversions

Create base_conversions table for organization/outlet-level unit conversions.
These are standard conversions (OZ → LB, GAL → QT) that can be customized
per organization or outlet.

Revision ID: 013
Revises: 012
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================
    # Table: base_conversions
    # Standard unit conversions (not product-specific)
    # ============================================
    op.create_table('base_conversions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # NULL organization_id = system default (applies to all orgs)
        sa.Column('organization_id', sa.Integer(), nullable=True),
        # NULL outlet_id = applies to entire organization
        sa.Column('outlet_id', sa.Integer(), nullable=True),
        sa.Column('from_unit_id', sa.Integer(), nullable=False),
        sa.Column('to_unit_id', sa.Integer(), nullable=False),
        sa.Column('conversion_factor', sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), server_default='1', nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_base_conversions_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outlet_id'], ['outlets.id'],
                                name='fk_base_conversions_outlet', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_unit_id'], ['units.id'],
                                name='fk_base_conversions_from_unit', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_unit_id'], ['units.id'],
                                name='fk_base_conversions_to_unit', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'],
                                name='fk_base_conversions_created_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Unique constraint: one conversion per from/to unit pair per scope
    # (outlet_id NULL means org-wide, organization_id NULL means system-wide)
    op.create_index('idx_base_conversions_lookup',
                    'base_conversions',
                    ['organization_id', 'outlet_id', 'from_unit_id', 'to_unit_id'],
                    unique=True)
    op.create_index('idx_base_conversions_org', 'base_conversions', ['organization_id'])
    op.create_index('idx_base_conversions_outlet', 'base_conversions', ['outlet_id'])

    # ============================================
    # Seed system-wide default conversions
    # These apply to all organizations (organization_id = NULL)
    # ============================================
    op.execute("""
        -- Weight conversions (relative to OZ)
        INSERT INTO base_conversions (organization_id, outlet_id, from_unit_id, to_unit_id, conversion_factor, notes)
        SELECT NULL, NULL, f.id, t.id,
            CASE
                -- OZ to others
                WHEN f.abbreviation = 'OZ' AND t.abbreviation = 'LB' THEN 0.0625
                WHEN f.abbreviation = 'OZ' AND t.abbreviation = 'G' THEN 28.3495
                WHEN f.abbreviation = 'OZ' AND t.abbreviation = 'KG' THEN 0.0283495
                -- LB to others
                WHEN f.abbreviation = 'LB' AND t.abbreviation = 'OZ' THEN 16
                WHEN f.abbreviation = 'LB' AND t.abbreviation = 'G' THEN 453.592
                WHEN f.abbreviation = 'LB' AND t.abbreviation = 'KG' THEN 0.453592
                -- G to others
                WHEN f.abbreviation = 'G' AND t.abbreviation = 'OZ' THEN 0.035274
                WHEN f.abbreviation = 'G' AND t.abbreviation = 'LB' THEN 0.00220462
                WHEN f.abbreviation = 'G' AND t.abbreviation = 'KG' THEN 0.001
                -- KG to others
                WHEN f.abbreviation = 'KG' AND t.abbreviation = 'OZ' THEN 35.274
                WHEN f.abbreviation = 'KG' AND t.abbreviation = 'LB' THEN 2.20462
                WHEN f.abbreviation = 'KG' AND t.abbreviation = 'G' THEN 1000
            END,
            'System default weight conversion'
        FROM units f
        CROSS JOIN units t
        WHERE f.abbreviation IN ('OZ', 'LB', 'G', 'KG')
          AND t.abbreviation IN ('OZ', 'LB', 'G', 'KG')
          AND f.id != t.id
        ON CONFLICT DO NOTHING;

        -- Volume conversions (relative to FL OZ)
        INSERT INTO base_conversions (organization_id, outlet_id, from_unit_id, to_unit_id, conversion_factor, notes)
        SELECT NULL, NULL, f.id, t.id,
            CASE
                -- FL OZ to others
                WHEN f.abbreviation = 'FL OZ' AND t.abbreviation = 'CUP' THEN 0.125
                WHEN f.abbreviation = 'FL OZ' AND t.abbreviation = 'PT' THEN 0.0625
                WHEN f.abbreviation = 'FL OZ' AND t.abbreviation = 'QT' THEN 0.03125
                WHEN f.abbreviation = 'FL OZ' AND t.abbreviation = 'GAL' THEN 0.0078125
                WHEN f.abbreviation = 'FL OZ' AND t.abbreviation = 'ML' THEN 29.5735
                WHEN f.abbreviation = 'FL OZ' AND t.abbreviation = 'L' THEN 0.0295735
                WHEN f.abbreviation = 'FL OZ' AND t.abbreviation = 'TBSP' THEN 2
                WHEN f.abbreviation = 'FL OZ' AND t.abbreviation = 'TSP' THEN 6
                -- GAL to others
                WHEN f.abbreviation = 'GAL' AND t.abbreviation = 'FL OZ' THEN 128
                WHEN f.abbreviation = 'GAL' AND t.abbreviation = 'CUP' THEN 16
                WHEN f.abbreviation = 'GAL' AND t.abbreviation = 'PT' THEN 8
                WHEN f.abbreviation = 'GAL' AND t.abbreviation = 'QT' THEN 4
                WHEN f.abbreviation = 'GAL' AND t.abbreviation = 'ML' THEN 3785.41
                WHEN f.abbreviation = 'GAL' AND t.abbreviation = 'L' THEN 3.78541
                -- QT to others
                WHEN f.abbreviation = 'QT' AND t.abbreviation = 'FL OZ' THEN 32
                WHEN f.abbreviation = 'QT' AND t.abbreviation = 'CUP' THEN 4
                WHEN f.abbreviation = 'QT' AND t.abbreviation = 'PT' THEN 2
                WHEN f.abbreviation = 'QT' AND t.abbreviation = 'GAL' THEN 0.25
                WHEN f.abbreviation = 'QT' AND t.abbreviation = 'ML' THEN 946.353
                WHEN f.abbreviation = 'QT' AND t.abbreviation = 'L' THEN 0.946353
                -- PT to others
                WHEN f.abbreviation = 'PT' AND t.abbreviation = 'FL OZ' THEN 16
                WHEN f.abbreviation = 'PT' AND t.abbreviation = 'CUP' THEN 2
                WHEN f.abbreviation = 'PT' AND t.abbreviation = 'QT' THEN 0.5
                WHEN f.abbreviation = 'PT' AND t.abbreviation = 'GAL' THEN 0.125
                -- CUP to others
                WHEN f.abbreviation = 'CUP' AND t.abbreviation = 'FL OZ' THEN 8
                WHEN f.abbreviation = 'CUP' AND t.abbreviation = 'PT' THEN 0.5
                WHEN f.abbreviation = 'CUP' AND t.abbreviation = 'QT' THEN 0.25
                WHEN f.abbreviation = 'CUP' AND t.abbreviation = 'GAL' THEN 0.0625
                WHEN f.abbreviation = 'CUP' AND t.abbreviation = 'ML' THEN 236.588
                WHEN f.abbreviation = 'CUP' AND t.abbreviation = 'TBSP' THEN 16
                WHEN f.abbreviation = 'CUP' AND t.abbreviation = 'TSP' THEN 48
                -- TBSP to others
                WHEN f.abbreviation = 'TBSP' AND t.abbreviation = 'FL OZ' THEN 0.5
                WHEN f.abbreviation = 'TBSP' AND t.abbreviation = 'TSP' THEN 3
                WHEN f.abbreviation = 'TBSP' AND t.abbreviation = 'ML' THEN 14.7868
                WHEN f.abbreviation = 'TBSP' AND t.abbreviation = 'CUP' THEN 0.0625
                -- TSP to others
                WHEN f.abbreviation = 'TSP' AND t.abbreviation = 'FL OZ' THEN 0.166667
                WHEN f.abbreviation = 'TSP' AND t.abbreviation = 'TBSP' THEN 0.333333
                WHEN f.abbreviation = 'TSP' AND t.abbreviation = 'ML' THEN 4.92892
                WHEN f.abbreviation = 'TSP' AND t.abbreviation = 'CUP' THEN 0.0208333
                -- L to others
                WHEN f.abbreviation = 'L' AND t.abbreviation = 'FL OZ' THEN 33.814
                WHEN f.abbreviation = 'L' AND t.abbreviation = 'ML' THEN 1000
                WHEN f.abbreviation = 'L' AND t.abbreviation = 'GAL' THEN 0.264172
                WHEN f.abbreviation = 'L' AND t.abbreviation = 'QT' THEN 1.05669
                -- ML to others
                WHEN f.abbreviation = 'ML' AND t.abbreviation = 'FL OZ' THEN 0.033814
                WHEN f.abbreviation = 'ML' AND t.abbreviation = 'L' THEN 0.001
                WHEN f.abbreviation = 'ML' AND t.abbreviation = 'TSP' THEN 0.202884
                WHEN f.abbreviation = 'ML' AND t.abbreviation = 'TBSP' THEN 0.067628
            END,
            'System default volume conversion'
        FROM units f
        CROSS JOIN units t
        WHERE f.abbreviation IN ('FL OZ', 'CUP', 'PT', 'QT', 'GAL', 'ML', 'L', 'TBSP', 'TSP')
          AND t.abbreviation IN ('FL OZ', 'CUP', 'PT', 'QT', 'GAL', 'ML', 'L', 'TBSP', 'TSP')
          AND f.id != t.id
        ON CONFLICT DO NOTHING;

        -- Clean up any NULL conversion factors (pairs that weren't defined)
        DELETE FROM base_conversions WHERE conversion_factor IS NULL;
    """)

    print("✅ Base conversions table created and seeded with system defaults")


def downgrade():
    op.drop_index('idx_base_conversions_outlet', 'base_conversions')
    op.drop_index('idx_base_conversions_org', 'base_conversions')
    op.drop_index('idx_base_conversions_lookup', 'base_conversions')
    op.drop_table('base_conversions')

    print("✅ Base conversions table removed")
