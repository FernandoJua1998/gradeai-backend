"""add token metrics to revisiones

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("revisiones", sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("revisiones", sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("revisiones", sa.Column("modelo_calificacion", sa.String(), nullable=True, server_default="claude-haiku-4-5-20251001"))
    op.add_column("revisiones", sa.Column("modelo_deteccion", sa.String(), nullable=True, server_default="claude-sonnet-4-6"))
    op.add_column("revisiones", sa.Column("costo_estimado", sa.Float(), nullable=False, server_default="0.0"))


def downgrade() -> None:
    op.drop_column("revisiones", "costo_estimado")
    op.drop_column("revisiones", "modelo_deteccion")
    op.drop_column("revisiones", "modelo_calificacion")
    op.drop_column("revisiones", "tokens_output")
    op.drop_column("revisiones", "tokens_input")
