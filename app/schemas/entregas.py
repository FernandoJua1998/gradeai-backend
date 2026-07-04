from pydantic import BaseModel


class EntregaResponse(BaseModel):
    id: int
    tarea_id: int
    alumno_id: int
    archivo_path: str
    status: str

    model_config = {"from_attributes": True}
