"""Add user_profiles table for persona and priorities

Revision ID: 006
Revises: 005
Create Date: 2024-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User profiles table for storing persona and priority preferences
    op.create_table(
        'user_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  unique=True, nullable=False, index=True),
        # User's natural language story/persona
        sa.Column('user_story', sa.Text, nullable=True),
        # Extracted priorities from LLM (event_type -> weight)
        sa.Column('priority_config', postgresql.JSON, nullable=True, server_default='{}'),
        # Default priorities for common event types
        sa.Column('default_priorities', postgresql.JSON, nullable=True, 
                  server_default='{"meeting": 7, "exam": 10, "study": 8, "deadline": 10, "appointment": 7, "class": 8, "work": 8, "exercise": 5, "social": 4, "party": 3, "personal": 5, "travel": 6, "other": 5}'),
        # Scheduling strategy preference
        sa.Column('scheduling_strategy', sa.String(50), server_default='balanced'),
        # When priorities were last extracted
        sa.Column('priorities_extracted_at', sa.String(50), nullable=True),
        # Standard timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('user_profiles')
