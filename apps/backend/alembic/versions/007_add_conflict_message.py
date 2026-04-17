"""
Add conflict_message column to event_collaboration_invitations

Revision ID: 007
Revises: 006
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        'event_collaboration_invitations',
        sa.Column('conflict_message', sa.Text, nullable=True)
    )

def downgrade():
    op.drop_column('event_collaboration_invitations', 'conflict_message')
