"""Add EHC (Environmental Health Compliance) module tables

Revision ID: 027
Revises: 026
Create Date: 2026-03-26

EHC Module - Food Safety Audit Compliance Tracking:
- Audit cycles (yearly audit tracking)
- Sections (6 top-level categories)
- Subsections (26 A-Z groupings)
- Audit points (125 scored questions)
- Records (47 evidence documents)
- Record-outlet mappings
- Record submissions (per-period instances)
- Point-record links (evidence relationships)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '027'
down_revision: Union[str, Sequence[str], None] = '026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EHC module infrastructure."""

    # ============================================
    # Table 1: ehc_audit_cycle
    # One per audit year per organization. The top-level container.
    # ============================================
    op.create_table('ehc_audit_cycle',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        sa.Column('name', sa.String(length=100), nullable=False),  # "EHC 2026"
        sa.Column('year', sa.SmallInteger(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),  # Scheduled audit date
        sa.Column('actual_date', sa.Date(), nullable=True),  # NULL until audit happens
        sa.Column('status', sa.String(length=20), nullable=False, server_default='preparing'),
        # Status: preparing | in_progress | completed | archived

        sa.Column('total_score', sa.Numeric(5, 2), nullable=True),  # NULL until scored (out of 100)
        sa.Column('passing_threshold', sa.Numeric(5, 2), nullable=False, server_default='80.0'),
        sa.Column('notes', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_ehc_audit_cycle_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'year', name='unique_ehc_cycle_per_year')
    )

    op.create_index('idx_ehc_audit_cycle_org', 'ehc_audit_cycle', ['organization_id'])
    op.create_index('idx_ehc_audit_cycle_year', 'ehc_audit_cycle', ['year'])
    op.create_index('idx_ehc_audit_cycle_status', 'ehc_audit_cycle', ['status'])

    # ============================================
    # Table 2: ehc_section
    # The 6 sections. Seeded per cycle.
    # ============================================
    op.create_table('ehc_section',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_cycle_id', sa.Integer(), nullable=False),

        sa.Column('ref_number', sa.SmallInteger(), nullable=False),  # 1-6
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.SmallInteger(), nullable=False),
        sa.Column('max_score', sa.Numeric(5, 2), nullable=True),  # Sum of child subsection max scores

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['audit_cycle_id'], ['ehc_audit_cycle.id'],
                                name='fk_ehc_section_cycle', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('audit_cycle_id', 'ref_number', name='unique_section_per_cycle')
    )

    op.create_index('idx_ehc_section_cycle', 'ehc_section', ['audit_cycle_id'])

    # ============================================
    # Table 3: ehc_subsection
    # The 26 subsections (A-Z). Each belongs to a section.
    # ============================================
    op.create_table('ehc_subsection',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),

        sa.Column('ref_code', sa.String(length=5), nullable=False),  # "A", "B", ... "Z"
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.SmallInteger(), nullable=False),
        sa.Column('max_score', sa.Numeric(5, 2), nullable=True),  # Sum of child audit point max scores

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['section_id'], ['ehc_section.id'],
                                name='fk_ehc_subsection_section', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('section_id', 'ref_code', name='unique_subsection_per_section')
    )

    op.create_index('idx_ehc_subsection_section', 'ehc_subsection', ['section_id'])

    # ============================================
    # Table 4: ehc_audit_point
    # The 125 individual questions. The core tracking unit.
    # ============================================
    op.create_table('ehc_audit_point',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('subsection_id', sa.Integer(), nullable=False),

        sa.Column('ref_code', sa.String(length=10), nullable=False),  # "A1", "B2", "M11"
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('nc_level', sa.SmallInteger(), nullable=False),  # 1-4
        sa.Column('max_score', sa.Numeric(5, 2), nullable=False),  # Weighted point value (0.25-2.5)
        sa.Column('actual_score', sa.Numeric(5, 2), nullable=True),  # NULL until scored

        sa.Column('status', sa.String(length=20), nullable=False, server_default='not_started'),
        # Status: not_started | in_progress | evidence_collected | verified | flagged

        sa.Column('flag_color', sa.String(length=10), nullable=True),  # NULL, "red", "orange"
        sa.Column('responsible_area', sa.String(length=100), nullable=True),  # Primary outlet/area
        sa.Column('notes', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['subsection_id'], ['ehc_subsection.id'],
                                name='fk_ehc_audit_point_subsection', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subsection_id', 'ref_code', name='unique_point_per_subsection')
    )

    op.create_index('idx_ehc_audit_point_subsection', 'ehc_audit_point', ['subsection_id'])
    op.create_index('idx_ehc_audit_point_nc_level', 'ehc_audit_point', ['nc_level'])
    op.create_index('idx_ehc_audit_point_status', 'ehc_audit_point', ['status'])

    # ============================================
    # Table 5: ehc_record
    # Master list of records (37 EHC + 10 SCP). Organization-level reference.
    # ============================================
    op.create_table('ehc_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        sa.Column('record_number', sa.String(length=10), nullable=False),  # "3", "1a", "SCP 40"
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('record_type', sa.String(length=20), nullable=False),
        # Type: daily | monthly | bi_monthly | quarterly | annual | one_time | audit_window | as_needed

        sa.Column('location_type', sa.String(length=20), nullable=False),  # outlet_book | office_book
        sa.Column('responsibility_code', sa.String(length=10), nullable=True),
        # Freeform label: "MM", "CF", "CM", "AM", "ENG", "FF", "EHC"

        sa.Column('is_physical_only', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_removed', sa.Boolean(), nullable=False, server_default='false'),
        # True for records 10, 22, 26, 31

        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_ehc_record_organization', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'record_number', name='unique_record_per_org')
    )

    op.create_index('idx_ehc_record_org', 'ehc_record', ['organization_id'])
    op.create_index('idx_ehc_record_type', 'ehc_record', ['record_type'])
    op.create_index('idx_ehc_record_location', 'ehc_record', ['location_type'])

    # ============================================
    # Table 6: ehc_record_outlet
    # Which outlets need which outlet-book records.
    # ============================================
    op.create_table('ehc_record_outlet',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),

        sa.Column('outlet_name', sa.String(length=100), nullable=False),
        # "Toro", "MK", "Casual", etc.

        sa.Column('sub_type', sa.String(length=50), nullable=True),
        # NULL, "Dish", "Glass" (for Record 13 split)

        sa.Column('notes', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['record_id'], ['ehc_record.id'],
                                name='fk_ehc_record_outlet_record', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_ehc_record_outlet_record', 'ehc_record_outlet', ['record_id'])
    op.create_index('idx_ehc_record_outlet_name', 'ehc_record_outlet', ['outlet_name'])

    # ============================================
    # Table 7: ehc_record_submission
    # A specific instance of a record for a given period within an audit cycle.
    # ============================================
    op.create_table('ehc_record_submission',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_cycle_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),

        sa.Column('outlet_name', sa.String(length=100), nullable=True),
        # NULL for office book records

        sa.Column('period_label', sa.String(length=50), nullable=False),
        # "January 2026", "Q1", "May-July", "Annual", "As Needed"

        sa.Column('period_start', sa.Date(), nullable=True),  # NULL for as-needed
        sa.Column('period_end', sa.Date(), nullable=True),  # NULL for as-needed

        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        # Status: pending | in_progress | submitted | approved | not_applicable

        sa.Column('is_physical', sa.Boolean(), nullable=False, server_default='false'),
        # Checked off as physically present

        sa.Column('file_path', sa.String(length=500), nullable=True),
        # NULL or path to uploaded file

        sa.Column('submitted_by', sa.Integer(), nullable=True),  # FK to users
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),  # FK to users
        sa.Column('approved_at', sa.DateTime(), nullable=True),

        sa.Column('notes', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['audit_cycle_id'], ['ehc_audit_cycle.id'],
                                name='fk_ehc_submission_cycle', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['record_id'], ['ehc_record.id'],
                                name='fk_ehc_submission_record', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id'],
                                name='fk_ehc_submission_submitted_by', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'],
                                name='fk_ehc_submission_approved_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_ehc_submission_cycle', 'ehc_record_submission', ['audit_cycle_id'])
    op.create_index('idx_ehc_submission_record', 'ehc_record_submission', ['record_id'])
    op.create_index('idx_ehc_submission_outlet', 'ehc_record_submission', ['outlet_name'])
    op.create_index('idx_ehc_submission_status', 'ehc_record_submission', ['status'])
    op.create_index('idx_ehc_submission_period', 'ehc_record_submission', ['period_label'])

    # ============================================
    # Table 8: ehc_point_record_link
    # Many-to-many: which records satisfy which audit points.
    # ============================================
    op.create_table('ehc_point_record_link',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('audit_point_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),

        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='true'),
        # True if this record is the main evidence for the point

        sa.Column('notes', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['audit_point_id'], ['ehc_audit_point.id'],
                                name='fk_ehc_point_record_point', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['record_id'], ['ehc_record.id'],
                                name='fk_ehc_point_record_record', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('audit_point_id', 'record_id', name='unique_point_record_link')
    )

    op.create_index('idx_ehc_point_record_point', 'ehc_point_record_link', ['audit_point_id'])
    op.create_index('idx_ehc_point_record_record', 'ehc_point_record_link', ['record_id'])

    print("EHC module tables created (8 tables)")


def downgrade() -> None:
    """Remove EHC module infrastructure."""

    # Drop in reverse order of creation (respecting FK dependencies)

    # Table 8: ehc_point_record_link
    op.drop_index('idx_ehc_point_record_record', 'ehc_point_record_link')
    op.drop_index('idx_ehc_point_record_point', 'ehc_point_record_link')
    op.drop_table('ehc_point_record_link')

    # Table 7: ehc_record_submission
    op.drop_index('idx_ehc_submission_period', 'ehc_record_submission')
    op.drop_index('idx_ehc_submission_status', 'ehc_record_submission')
    op.drop_index('idx_ehc_submission_outlet', 'ehc_record_submission')
    op.drop_index('idx_ehc_submission_record', 'ehc_record_submission')
    op.drop_index('idx_ehc_submission_cycle', 'ehc_record_submission')
    op.drop_table('ehc_record_submission')

    # Table 6: ehc_record_outlet
    op.drop_index('idx_ehc_record_outlet_name', 'ehc_record_outlet')
    op.drop_index('idx_ehc_record_outlet_record', 'ehc_record_outlet')
    op.drop_table('ehc_record_outlet')

    # Table 5: ehc_record
    op.drop_index('idx_ehc_record_location', 'ehc_record')
    op.drop_index('idx_ehc_record_type', 'ehc_record')
    op.drop_index('idx_ehc_record_org', 'ehc_record')
    op.drop_table('ehc_record')

    # Table 4: ehc_audit_point
    op.drop_index('idx_ehc_audit_point_status', 'ehc_audit_point')
    op.drop_index('idx_ehc_audit_point_nc_level', 'ehc_audit_point')
    op.drop_index('idx_ehc_audit_point_subsection', 'ehc_audit_point')
    op.drop_table('ehc_audit_point')

    # Table 3: ehc_subsection
    op.drop_index('idx_ehc_subsection_section', 'ehc_subsection')
    op.drop_table('ehc_subsection')

    # Table 2: ehc_section
    op.drop_index('idx_ehc_section_cycle', 'ehc_section')
    op.drop_table('ehc_section')

    # Table 1: ehc_audit_cycle
    op.drop_index('idx_ehc_audit_cycle_status', 'ehc_audit_cycle')
    op.drop_index('idx_ehc_audit_cycle_year', 'ehc_audit_cycle')
    op.drop_index('idx_ehc_audit_cycle_org', 'ehc_audit_cycle')
    op.drop_table('ehc_audit_cycle')

    print("EHC module tables removed")
