from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.grupo import Grupo
from app.db.models.alumno import Alumno
from app.schemas.alumnos import AlumnoCreate, AlumnoUpdate, AlumnoResponse

router = APIRouter(tags=["alumnos"])


def _verify_grupo(grupo_id: int, user: User, db: Session) -> Grupo:
    grupo = db.query(Grupo).filter(Grupo.id == grupo_id, Grupo.user_id == user.id).first()
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo no encontrado")
    return grupo


@router.get("/grupos/{grupo_id}/alumnos", response_model=list[AlumnoResponse])
def list_alumnos(grupo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_grupo(grupo_id, current_user, db)
    return db.query(Alumno).filter(Alumno.grupo_id == grupo_id).all()


@router.post("/grupos/{grupo_id}/alumnos", response_model=AlumnoResponse, status_code=status.HTTP_201_CREATED)
def create_alumno(grupo_id: int, body: AlumnoCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_grupo(grupo_id, current_user, db)
    alumno = Alumno(grupo_id=grupo_id, nombre=body.nombre)
    db.add(alumno)
    db.commit()
    db.refresh(alumno)
    return alumno


@router.put("/alumnos/{alumno_id}", response_model=AlumnoResponse)
def update_alumno(alumno_id: int, body: AlumnoUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alumno = db.query(Alumno).join(Grupo).filter(
        Alumno.id == alumno_id,
        Grupo.user_id == current_user.id
    ).first()
    if not alumno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado")
    alumno.nombre = body.nombre
    db.commit()
    db.refresh(alumno)
    return alumno


@router.delete("/alumnos/{alumno_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alumno(alumno_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alumno = db.query(Alumno).join(Grupo).filter(
        Alumno.id == alumno_id,
        Grupo.user_id == current_user.id
    ).first()
    if not alumno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado")
    db.delete(alumno)
    db.commit()
