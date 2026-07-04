from typing import Any
from pydantic import BaseModel


class CriterioItem(BaseModel):
    nombre: str
    ponderacion: float


class ConfigIA(BaseModel):
    modo: str  # "desactivado" | "informativo" | "penalizacion_auto" | "penalizacion_manual"
    penalizacion_porcentaje: int = 0


class TareaCreate(BaseModel):
    titulo: str
    grupo_id: int
    criterios: list[CriterioItem]
    config_ia: ConfigIA
    rubrica_path: str | None = None


class TareaUpdate(BaseModel):
    titulo: str | None = None
    criterios: list[CriterioItem] | None = None
    config_ia: ConfigIA | None = None


class TareaResponse(BaseModel):
    id: int
    grupo_id: int
    titulo: str
    criterios: Any
    config_ia: Any
    rubrica_path: str | None

    model_config = {"from_attributes": True}
