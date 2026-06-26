from pydantic import BaseModel


class GrupoCreate(BaseModel):
    nombre: str
    materia: str
    ciclo: str


class GrupoUpdate(BaseModel):
    nombre: str | None = None
    materia: str | None = None
    ciclo: str | None = None


class GrupoResponse(BaseModel):
    id: int
    nombre: str
    materia: str
    ciclo: str

    model_config = {"from_attributes": True}
