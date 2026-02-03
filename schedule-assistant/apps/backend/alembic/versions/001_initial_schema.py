# schedule-assistant/apps/backend/alembic/versions/001_initial_schema.py
"""Initial schema

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

    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timezone', sa.Text(), server_default=sa.text("'Asia/Bangkok'"), nullable=False),
        sa.Column('default_duration_min', sa.Integer(), server_default=sa.text('60'), nullable=False),
        sa.Column('buffer_min', sa.Integer(), server_default=sa.text('10'), nullable=False),
        sa.Column('preferences', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('extracted_json', postgresql.JSONB(), nullable=True),
        sa.Column('action_json', postgresql.JSONB(), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name='ck_chat_messages_role'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_messages_session_created', 'chat_messages', ['session_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('user_settings')
    op.drop_index('ix_events_calendar_start_end', table_name='events')
    op.drop_index('ix_events_calendar_start', table_name='events')
    op.drop_table('events')
    op.drop_table('event_types')
    op.drop_table('calendars')
    op.drop_table('users')
