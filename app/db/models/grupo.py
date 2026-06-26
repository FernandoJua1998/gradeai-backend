from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Grupo(Base):
    __tablename__ = "grupos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    materia: Mapped[str] = mapped_column(String(255), nullable=False)
    ciclo: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="grupos")
    tareas: Mapped[list["Tarea"]] = relationship("Tarea", back_populates="grupo")
    alumnos: Mapped[list["Alumno"]] = relationship("Alumno", back_populates="grupo")
