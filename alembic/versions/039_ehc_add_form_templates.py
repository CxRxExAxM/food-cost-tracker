"""Add EHC Form Templates for checklist-style forms

Revision ID: 039
Revises: 038
Create Date: 2026-04-10

EHC Form Templates:
- ehc_form_template: Reusable form definitions (e.g., Kitchen Audit Checklist with 58 questions)
- Extended ehc_form_link: template_id, outlet_name, period_label for per-outlet form instances

This enables the "Create from Template" workflow where admins can deploy a template
to multiple outlets at once, each getting their own QR code and form instance.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '039'
down_revision: Union[str, Sequence[str], None] = '038'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EHC Form Template infrastructure."""

    # ============================================
    # Table: ehc_form_template
    # Reusable form definitions. Stores checklist items, settings.
    # Templates are org-scoped and can link to an EHC record type.
    # ============================================
    op.create_table('ehc_form_template',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        sa.Column('name', sa.String(length=255), nullable=False),
        # "Kitchen Audit Checklist", "Internal Food Safety Audit", etc.

        sa.Column('form_type', sa.String(length=50), nullable=False),
        # 'checklist_form', 'table_signoff', etc.

        sa.Column('ehc_record_id', sa.Integer(), nullable=True),
        # Links to ehc_record (e.g., Record 20 for Kitchen Audit)
        # Nullable for templates not tied to a specific EHC record

        # Template configuration (checklist items, settings)
        # Structure for checklist_form:
        # {
        #   "intro_text": "Instructions shown at top of form",
        #   "items": [
        #     {"number": 1, "question": "Are floors clean?", "response_type": "yes_no"},
        #     ...
        #   ],
        #   "corrective_actions": true,
        #   "signature_required": true
        # }
        sa.Column('config', sa.JSON(), nullable=False),

        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_ehc_form_template_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ehc_record_id'], ['ehc_record.id'],
                                name='fk_ehc_form_template_record', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'],
                                name='fk_ehc_form_template_created_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_ehc_form_template_org', 'ehc_form_template', ['organization_id'])
    op.create_index('idx_ehc_form_template_record', 'ehc_form_template', ['ehc_record_id'])
    op.create_index('idx_ehc_form_template_active', 'ehc_form_template', ['is_active'])
    op.create_index('idx_ehc_form_template_type', 'ehc_form_template', ['form_type'])

    # ============================================
    # Extend ehc_form_link for template-based forms
    # ============================================

    # template_id: Links form instance back to its template (for grouping/display)
    op.add_column('ehc_form_link',
        sa.Column('template_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_ehc_form_link_template',
        'ehc_form_link', 'ehc_form_template',
        ['template_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_ehc_form_link_template', 'ehc_form_link', ['template_id'])

    # outlet_name: Which outlet this form instance is for (e.g., "Main Kitchen", "Toro")
    # Freeform string to match existing EHC outlet approach
    op.add_column('ehc_form_link',
        sa.Column('outlet_name', sa.String(length=255), nullable=True)
    )
    op.create_index('idx_ehc_form_link_outlet', 'ehc_form_link', ['outlet_name'])

    # period_label: Human-readable period (e.g., "April 2026", "Q2 2026")
    op.add_column('ehc_form_link',
        sa.Column('period_label', sa.String(length=100), nullable=True)
    )
    op.create_index('idx_ehc_form_link_period', 'ehc_form_link', ['period_label'])

    print("EHC Form Templates: Created ehc_form_template table, extended ehc_form_link")


def downgrade() -> None:
    """Remove EHC Form Template infrastructure."""

    # Remove new columns from ehc_form_link
    op.drop_index('idx_ehc_form_link_period', 'ehc_form_link')
    op.drop_column('ehc_form_link', 'period_label')

    op.drop_index('idx_ehc_form_link_outlet', 'ehc_form_link')
    op.drop_column('ehc_form_link', 'outlet_name')

    op.drop_index('idx_ehc_form_link_template', 'ehc_form_link')
    op.drop_constraint('fk_ehc_form_link_template', 'ehc_form_link', type_='foreignkey')
    op.drop_column('ehc_form_link', 'template_id')

    # Drop ehc_form_template table
    op.drop_index('idx_ehc_form_template_type', 'ehc_form_template')
    op.drop_index('idx_ehc_form_template_active', 'ehc_form_template')
    op.drop_index('idx_ehc_form_template_record', 'ehc_form_template')
    op.drop_index('idx_ehc_form_template_org', 'ehc_form_template')
    op.drop_table('ehc_form_template')

    print("EHC Form Templates: Removed")
