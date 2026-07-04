from pydantic import BaseModel


class AlumnoCreate(BaseModel):
    nombre: str


class AlumnoUpdate(BaseModel):
    nombre: str


class AlumnoResponse(BaseModel):
    id: int
    grupo_id: int
    nombre: str

    model_config = {"from_attributes": True}
