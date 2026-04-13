"""
Add event_collaborators and event_collaboration_invitations tables

Revision ID: 005
Revises: 004
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'event_collaborators',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('event_id', psql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), index=True),
        sa.Column('user_id', psql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='editor'),
    )
    op.create_table(
        'event_collaboration_invitations',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('event_id', psql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), index=True),
        sa.Column('inviter_id', psql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('invitee_id', psql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table('event_collaboration_invitations')
    op.drop_table('event_collaborators')
