from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tarea(Base):
    __tablename__ = "tareas"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupos.id"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    criterios: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    rubrica_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    config_ia: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    grupo: Mapped["Grupo"] = relationship("Grupo", back_populates="tareas")
    entregas: Mapped[list["Entrega"]] = relationship("Entrega", back_populates="tarea")
