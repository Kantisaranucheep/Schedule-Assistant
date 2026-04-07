"""Add notification columns to user_settings.

Revision ID: 003
Revises: 002
Create Date: 2025-01-20

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add notification columns to user_settings table
    op.add_column(
        'user_settings',
        sa.Column('notification_email', sa.String(255), nullable=True)
    )
    op.add_column(
        'user_settings',
        sa.Column('notifications_enabled', sa.Boolean, server_default='false', nullable=False)
    )
    op.add_column(
        'user_settings',
        sa.Column('window_notifications_enabled', sa.Boolean, server_default='true', nullable=False)
    )
    op.add_column(
        'user_settings',
        sa.Column('notification_times_json', sa.Text, nullable=True, server_default='[]')
    )


def downgrade() -> None:
    op.drop_column('user_settings', 'notification_times_json')
    op.drop_column('user_settings', 'window_notifications_enabled')
    op.drop_column('user_settings', 'notifications_enabled')
    op.drop_column('user_settings', 'notification_email')
