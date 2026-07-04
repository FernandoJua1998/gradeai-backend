from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.grupo import Grupo
from app.db.models.tarea import Tarea
from app.schemas.tareas import TareaCreate, TareaUpdate, TareaResponse

router = APIRouter(tags=["tareas"])


def _verify_grupo(grupo_id: int, user: User, db: Session) -> Grupo:
    grupo = db.query(Grupo).filter(Grupo.id == grupo_id, Grupo.user_id == user.id).first()
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo no encontrado")
    return grupo


def _get_tarea_or_404(tarea_id: int, user: User, db: Session) -> Tarea:
    tarea = db.query(Tarea).join(Grupo).filter(
        Tarea.id == tarea_id,
        Grupo.user_id == user.id
    ).first()
    if not tarea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return tarea


@router.get("/grupos/{grupo_id}/tareas", response_model=list[TareaResponse])
def list_tareas(grupo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_grupo(grupo_id, current_user, db)
    return db.query(Tarea).filter(Tarea.grupo_id == grupo_id).all()


@router.post("/tareas", response_model=TareaResponse, status_code=status.HTTP_201_CREATED)
def create_tarea(body: TareaCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_grupo(body.grupo_id, current_user, db)
    data = body.model_dump()
    # Serialize nested objects to plain dicts for JSONB storage
    data["criterios"] = [c.model_dump() for c in body.criterios]
    data["config_ia"] = body.config_ia.model_dump()
    tarea = Tarea(**data)
    db.add(tarea)
    db.commit()
    db.refresh(tarea)
    return tarea


@router.get("/tareas/{tarea_id}", response_model=TareaResponse)
def get_tarea(tarea_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_tarea_or_404(tarea_id, current_user, db)


@router.put("/tareas/{tarea_id}", response_model=TareaResponse)
def update_tarea(tarea_id: int, body: TareaUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tarea = _get_tarea_or_404(tarea_id, current_user, db)
    update_data = body.model_dump(exclude_none=True)
    if "criterios" in update_data:
        update_data["criterios"] = [c.model_dump() for c in body.criterios]
    if "config_ia" in update_data:
        update_data["config_ia"] = body.config_ia.model_dump()
    for field, value in update_data.items():
        setattr(tarea, field, value)
    db.commit()
    db.refresh(tarea)
    return tarea


@router.delete("/tareas/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tarea(tarea_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tarea = _get_tarea_or_404(tarea_id, current_user, db)
    db.delete(tarea)
    db.commit()
