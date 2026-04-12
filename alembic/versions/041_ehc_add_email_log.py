"""Add EHC email log table

Revision ID: 041
Revises: 040
Create Date: 2026-04-11

Phase 3 of EHC Settings - Email Infrastructure:
- ehc_email_log: Track sent emails for audit trail and debugging
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '041'
down_revision: Union[str, Sequence[str], None] = '040'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EHC email log table."""

    # ============================================
    # Table: ehc_email_log
    # Track all sent emails for audit trail
    # ============================================
    op.create_table('ehc_email_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Who received the email
        sa.Column('contact_id', sa.Integer(), nullable=True),  # nullable if sent to arbitrary email
        sa.Column('email_to', sa.String(length=255), nullable=False),
        sa.Column('email_to_name', sa.String(length=255), nullable=True),

        # Email content
        sa.Column('email_subject', sa.String(length=500), nullable=True),
        sa.Column('email_type', sa.String(length=50), nullable=False),  # 'form_qr', 'test', 'reminder'

        # What was sent (for form QR emails)
        sa.Column('form_link_id', sa.Integer(), nullable=True),
        sa.Column('outlet_id', sa.Integer(), nullable=True),

        # Resend tracking
        sa.Column('resend_id', sa.String(length=100), nullable=True),  # Resend's message ID
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        # status: 'pending', 'sent', 'delivered', 'bounced', 'failed'
        sa.Column('error_message', sa.Text(), nullable=True),

        sa.Column('sent_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('sent_by_user_id', sa.Integer(), nullable=True),  # who triggered the send

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_ehc_email_log_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['ehc_contact.id'],
                                name='fk_ehc_email_log_contact', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['form_link_id'], ['ehc_form_link.id'],
                                name='fk_ehc_email_log_form_link', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['outlet_id'], ['ehc_outlet.id'],
                                name='fk_ehc_email_log_outlet', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sent_by_user_id'], ['users.id'],
                                name='fk_ehc_email_log_user', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_ehc_email_log_org', 'ehc_email_log', ['organization_id'])
    op.create_index('idx_ehc_email_log_contact', 'ehc_email_log', ['contact_id'])
    op.create_index('idx_ehc_email_log_form_link', 'ehc_email_log', ['form_link_id'])
    op.create_index('idx_ehc_email_log_type', 'ehc_email_log', ['email_type'])
    op.create_index('idx_ehc_email_log_status', 'ehc_email_log', ['status'])
    op.create_index('idx_ehc_email_log_sent_at', 'ehc_email_log', ['sent_at'])

    print("EHC email log table created (ehc_email_log)")


def downgrade() -> None:
    """Remove EHC email log table."""

    op.drop_index('idx_ehc_email_log_sent_at', 'ehc_email_log')
    op.drop_index('idx_ehc_email_log_status', 'ehc_email_log')
    op.drop_index('idx_ehc_email_log_type', 'ehc_email_log')
    op.drop_index('idx_ehc_email_log_form_link', 'ehc_email_log')
    op.drop_index('idx_ehc_email_log_contact', 'ehc_email_log')
    op.drop_index('idx_ehc_email_log_org', 'ehc_email_log')
    op.drop_table('ehc_email_log')

    print("EHC email log table removed")
