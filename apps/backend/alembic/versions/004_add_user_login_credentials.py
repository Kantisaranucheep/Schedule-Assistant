"""Add username and password columns to users.

Revision ID: 004
Revises: 003
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('username', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('password', sa.String(length=255), nullable=True))

    # Backfill existing rows so we can enforce NOT NULL constraints.
    op.execute("UPDATE users SET username = email WHERE username IS NULL")
    op.execute("UPDATE users SET password = 'demo1234' WHERE password IS NULL")

    op.alter_column('users', 'username', nullable=False)
    op.alter_column('users', 'password', nullable=False)

    op.create_index('ix_users_username', 'users', ['username'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'password')
    op.drop_column('users', 'username')
