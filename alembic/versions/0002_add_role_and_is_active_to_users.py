"""add role and is_active to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(), nullable=False, server_default="teacher"))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))


def downgrade() -> None:
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
