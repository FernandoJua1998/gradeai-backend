from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Float, Text, ForeignKey, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Revision(Base):
    __tablename__ = "revisiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    entrega_id: Mapped[int] = mapped_column(ForeignKey("entregas.id"), unique=True, nullable=False)
    calificacion: Mapped[float | None] = mapped_column(Float, nullable=True)
    desglose: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    retroalimentacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    ia_probabilidad: Mapped[float | None] = mapped_column(Float, nullable=True)
    ia_nivel_riesgo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ia_fragmentos: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    entrega: Mapped["Entrega"] = relationship("Entrega", back_populates="revision")
