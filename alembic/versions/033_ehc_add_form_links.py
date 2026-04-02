"""Add EHC Digital Forms tables for tokenized public signature collection

Revision ID: 033
Revises: 032
Create Date: 2026-04-02

EHC Digital Forms:
- ehc_form_link: Tokenized public links for signature collection (staff declarations, team rosters)
- ehc_form_response: Individual responses with signatures from unauthenticated staff
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '033'
down_revision: Union[str, Sequence[str], None] = '032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EHC Digital Forms tables."""

    # ============================================
    # Table 1: ehc_form_link
    # One per generated form link. Tied to a specific record submission.
    # Token provides public access - no authentication required.
    # ============================================
    op.create_table('ehc_form_link',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('audit_cycle_id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=True),  # Nullable - can link after creation
        sa.Column('record_id', sa.Integer(), nullable=False),

        # Token: 43-character URL-safe string via secrets.token_urlsafe(32)
        sa.Column('token', sa.String(length=64), nullable=False),

        # Form type determines rendering and PDF generation
        sa.Column('form_type', sa.String(length=50), nullable=False),
        # Types: 'staff_declaration', 'team_roster', 'checklist' (future)

        sa.Column('title', sa.String(length=255), nullable=True),
        # Display title: "Food Safety Declaration — EHC 2026"

        # Form-specific configuration (team members, expected count, etc.)
        sa.Column('config', sa.JSON(), nullable=False),

        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),  # NULL = no expiry
        sa.Column('expected_responses', sa.Integer(), nullable=True),  # Target count (e.g., 95)

        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_ehc_form_link_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audit_cycle_id'], ['ehc_audit_cycle.id'],
                                name='fk_ehc_form_link_cycle', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submission_id'], ['ehc_record_submission.id'],
                                name='fk_ehc_form_link_submission', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['record_id'], ['ehc_record.id'],
                                name='fk_ehc_form_link_record', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'],
                                name='fk_ehc_form_link_created_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Unique constraint on token for fast lookup
    op.create_index('idx_ehc_form_link_token', 'ehc_form_link', ['token'], unique=True)
    op.create_index('idx_ehc_form_link_org', 'ehc_form_link', ['organization_id'])
    op.create_index('idx_ehc_form_link_cycle', 'ehc_form_link', ['audit_cycle_id'])
    op.create_index('idx_ehc_form_link_submission', 'ehc_form_link', ['submission_id'])
    op.create_index('idx_ehc_form_link_active', 'ehc_form_link', ['is_active'])

    # ============================================
    # Table 2: ehc_form_response
    # One per individual signature/submission against a form link.
    # No FK to users - respondents are unauthenticated staff.
    # ============================================
    op.create_table('ehc_form_response',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('form_link_id', sa.Integer(), nullable=False),

        sa.Column('respondent_name', sa.String(length=255), nullable=False),
        sa.Column('respondent_role', sa.String(length=100), nullable=True),  # Position/title
        sa.Column('respondent_dept', sa.String(length=100), nullable=True),  # Department

        # Form-specific answers (acknowledgment checkbox, team_member_index, etc.)
        sa.Column('response_data', sa.JSON(), nullable=True),

        # Base64-encoded PNG signature from canvas pad (typically 5-15KB)
        sa.Column('signature_data', sa.Text(), nullable=False),

        sa.Column('submitted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        # Lightweight audit trail (no auth, but track device info)
        sa.Column('ip_address', sa.String(length=45), nullable=True),  # IPv6 max length
        sa.Column('user_agent', sa.String(length=500), nullable=True),

        sa.ForeignKeyConstraint(['form_link_id'], ['ehc_form_link.id'],
                                name='fk_ehc_form_response_link', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_ehc_form_response_link', 'ehc_form_response', ['form_link_id'])
    op.create_index('idx_ehc_form_response_name', 'ehc_form_response', ['respondent_name'])
    op.create_index('idx_ehc_form_response_submitted', 'ehc_form_response', ['submitted_at'])

    print("EHC Digital Forms tables created (2 tables: ehc_form_link, ehc_form_response)")


def downgrade() -> None:
    """Remove EHC Digital Forms tables."""

    # Drop in reverse order (ehc_form_response references ehc_form_link)
    op.drop_index('idx_ehc_form_response_submitted', 'ehc_form_response')
    op.drop_index('idx_ehc_form_response_name', 'ehc_form_response')
    op.drop_index('idx_ehc_form_response_link', 'ehc_form_response')
    op.drop_table('ehc_form_response')

    op.drop_index('idx_ehc_form_link_active', 'ehc_form_link')
    op.drop_index('idx_ehc_form_link_submission', 'ehc_form_link')
    op.drop_index('idx_ehc_form_link_cycle', 'ehc_form_link')
    op.drop_index('idx_ehc_form_link_org', 'ehc_form_link')
    op.drop_index('idx_ehc_form_link_token', 'ehc_form_link')
    op.drop_table('ehc_form_link')

    print("EHC Digital Forms tables removed")
