from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.grupo import Grupo
from app.schemas.grupos import GrupoCreate, GrupoUpdate, GrupoResponse

router = APIRouter(prefix="/grupos", tags=["grupos"])


def _get_grupo_or_404(grupo_id: int, user: User, db: Session) -> Grupo:
    grupo = db.query(Grupo).filter(Grupo.id == grupo_id, Grupo.user_id == user.id).first()
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo no encontrado")
    return grupo


@router.get("", response_model=list[GrupoResponse])
def list_grupos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Grupo).filter(Grupo.user_id == current_user.id).all()


@router.post("", response_model=GrupoResponse, status_code=status.HTTP_201_CREATED)
def create_grupo(body: GrupoCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupo = Grupo(**body.model_dump(), user_id=current_user.id)
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@router.get("/{grupo_id}", response_model=GrupoResponse)
def get_grupo(grupo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_grupo_or_404(grupo_id, current_user, db)


@router.put("/{grupo_id}", response_model=GrupoResponse)
def update_grupo(grupo_id: int, body: GrupoUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupo = _get_grupo_or_404(grupo_id, current_user, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(grupo, field, value)
    db.commit()
    db.refresh(grupo)
    return grupo


@router.delete("/{grupo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grupo(grupo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    grupo = _get_grupo_or_404(grupo_id, current_user, db)
    db.delete(grupo)
    db.commit()
