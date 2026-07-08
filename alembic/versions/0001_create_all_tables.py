"""create all tables

Revision ID: 0001
Revises:
Create Date: 2026-07-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "grupos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("materia", sa.String(255), nullable=False),
        sa.Column("ciclo", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "tareas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grupo_id", sa.Integer(), sa.ForeignKey("grupos.id"), nullable=False),
        sa.Column("titulo", sa.String(500), nullable=False),
        sa.Column("criterios", JSONB(), nullable=False),
        sa.Column("rubrica_path", sa.String(500), nullable=True),
        sa.Column("config_ia", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "alumnos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grupo_id", sa.Integer(), sa.ForeignKey("grupos.id"), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
    )

    op.create_table(
        "entregas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tarea_id", sa.Integer(), sa.ForeignKey("tareas.id"), nullable=False),
        sa.Column("alumno_id", sa.Integer(), sa.ForeignKey("alumnos.id"), nullable=False),
        sa.Column("archivo_path", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "revisiones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entrega_id", sa.Integer(), sa.ForeignKey("entregas.id"), nullable=False, unique=True),
        sa.Column("calificacion", sa.Float(), nullable=True),
        sa.Column("desglose", JSONB(), nullable=False),
        sa.Column("retroalimentacion", sa.Text(), nullable=True),
        sa.Column("ia_probabilidad", sa.Float(), nullable=True),
        sa.Column("ia_nivel_riesgo", sa.String(20), nullable=True),
        sa.Column("ia_fragmentos", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("revisiones")
    op.drop_table("entregas")
    op.drop_table("alumnos")
    op.drop_table("tareas")
    op.drop_table("grupos")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
