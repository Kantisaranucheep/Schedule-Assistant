# schedule-assistant/apps/backend/alembic/versions/001_initial_schema.py
"""Initial schema - Clean version for Schedule Assistant

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create calendars table
    op.create_table(
        'calendars',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('timezone', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create event_types table
    op.create_table(
        'event_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('color', sa.Text(), nullable=True),
        sa.Column('default_duration_min', sa.Integer(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_event_types_user_name')
    )

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('calendar_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('start_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('end_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('status', sa.Text(), server_default=sa.text("'confirmed'"), nullable=False),
        sa.Column('created_by', sa.Text(), server_default=sa.text("'user'"), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('confirmed', 'tentative', 'cancelled')", name='ck_events_status'),
        sa.CheckConstraint("created_by IN ('user', 'agent')", name='ck_events_created_by'),
        sa.CheckConstraint('end_at > start_at', name='ck_events_end_after_start'),
        sa.ForeignKeyConstraint(['calendar_id'], ['calendars.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['type_id'], ['event_types.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_events_calendar_start', 'events', ['calendar_id', 'start_at'])
    op.create_index('ix_events_calendar_start_end', 'events', ['calendar_id', 'start_at', 'end_at'])

    # Insert default test user and calendar for development
    op.execute("""
        INSERT INTO users (id, name, email) VALUES 
        ('00000000-0000-0000-0000-000000000001', 'Test User', 'test@example.com')
        ON CONFLICT (id) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO calendars (id, user_id, name, timezone) VALUES 
        ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'My Calendar', 'Asia/Bangkok')
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_index('ix_events_calendar_start_end', table_name='events')
    op.drop_index('ix_events_calendar_start', table_name='events')
    op.drop_table('events')
    op.drop_table('event_types')
    op.drop_table('calendars')
    op.drop_table('users')
