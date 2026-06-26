from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Alumno(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupos.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)

    grupo: Mapped["Grupo"] = relationship("Grupo", back_populates="alumnos")
    entregas: Mapped[list["Entrega"]] = relationship("Entrega", back_populates="alumno")
