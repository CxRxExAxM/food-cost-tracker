"""Add natural language chat infrastructure

Revision ID: 022
Revises: 021
Create Date: 2024-03-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade():
    # Create property_events table
    op.create_table(
        'property_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_property_events_org_date', 'property_events', ['organization_id', 'start_date'])
    op.create_index('ix_property_events_year', 'property_events', ['year'])

    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_sessions_org_user', 'chat_sessions', ['organization_id', 'user_id'])
    op.create_index('ix_chat_sessions_updated', 'chat_sessions', ['updated_at'])

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result_type', sa.String(length=50), nullable=True),
        sa.Column('result_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("role IN ('user', 'assistant')", name='check_message_role')
    )
    op.create_index('ix_chat_messages_session', 'chat_messages', ['session_id'])
    op.create_index('ix_chat_messages_created', 'chat_messages', ['created_at'])

    # Seed property_events with Scottsdale events
    # Note: These will be inserted for organization_id=1. Adjust if needed.
    op.execute("""
        INSERT INTO property_events (organization_id, name, start_date, end_date, year, category, notes)
        VALUES
            -- 2024 Events
            (1, 'WM Phoenix Open', '2024-02-05', '2024-02-11', 2024, 'local_event', 'Major PGA Tour golf tournament at TPC Scottsdale'),
            (1, 'Barrett-Jackson Scottsdale', '2024-01-20', '2024-01-28', 2024, 'local_event', 'World''s largest collector car auction'),
            (1, 'Spring Training', '2024-02-16', '2024-03-24', 2024, 'seasonal', 'MLB spring training season'),
            (1, 'Spring Break', '2024-03-09', '2024-03-17', 2024, 'seasonal', 'Peak spring break tourism period'),
            (1, 'Arizona Super Bowl LVII', '2023-02-12', '2023-02-12', 2023, 'local_event', 'Super Bowl held at State Farm Stadium'),

            -- 2025 Events
            (1, 'WM Phoenix Open', '2025-02-03', '2025-02-09', 2025, 'local_event', 'Major PGA Tour golf tournament at TPC Scottsdale'),
            (1, 'Barrett-Jackson Scottsdale', '2025-01-18', '2025-01-26', 2025, 'local_event', 'World''s largest collector car auction'),
            (1, 'Spring Training', '2025-02-14', '2025-03-23', 2025, 'seasonal', 'MLB spring training season'),
            (1, 'Spring Break', '2025-03-08', '2025-03-16', 2025, 'seasonal', 'Peak spring break tourism period'),

            -- 2026 Events
            (1, 'WM Phoenix Open', '2026-02-02', '2026-02-08', 2026, 'local_event', 'Major PGA Tour golf tournament at TPC Scottsdale'),
            (1, 'Barrett-Jackson Scottsdale', '2026-01-17', '2026-01-25', 2026, 'local_event', 'World''s largest collector car auction'),
            (1, 'Spring Training', '2026-02-20', '2026-03-29', 2026, 'seasonal', 'MLB spring training season'),
            (1, 'Spring Break', '2026-03-14', '2026-03-22', 2026, 'seasonal', 'Peak spring break tourism period')
        ON CONFLICT DO NOTHING;
    """)


def downgrade():
    op.drop_index('ix_chat_messages_created', table_name='chat_messages')
    op.drop_index('ix_chat_messages_session', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('ix_chat_sessions_updated', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_org_user', table_name='chat_sessions')
    op.drop_table('chat_sessions')

    op.drop_index('ix_property_events_year', table_name='property_events')
    op.drop_index('ix_property_events_org_date', table_name='property_events')
    op.drop_table('property_events')
