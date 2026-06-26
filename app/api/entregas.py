import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.grupo import Grupo
from app.db.models.tarea import Tarea
from app.db.models.alumno import Alumno
from app.db.models.entrega import Entrega
from app.schemas.entregas import EntregaResponse

router = APIRouter(tags=["entregas"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


def _get_tarea_or_404(tarea_id: int, user: User, db: Session) -> Tarea:
    tarea = db.query(Tarea).join(Grupo).filter(
        Tarea.id == tarea_id,
        Grupo.user_id == user.id
    ).first()
    if not tarea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return tarea


@router.post("/entregas/lote/{tarea_id}", response_model=list[EntregaResponse], status_code=status.HTTP_201_CREATED)
async def subir_entregas_lote(
    tarea_id: int,
    archivos: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tarea = _get_tarea_or_404(tarea_id, current_user, db)
    entregas_creadas = []

    for archivo in archivos:
        ext = Path(archivo.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Tipo de archivo no permitido: {archivo.filename}. Solo PDF y Word.",
            )

        nombre_alumno = Path(archivo.filename).stem

        # Find or create alumno
        alumno = db.query(Alumno).filter(
            Alumno.grupo_id == tarea.grupo_id,
            Alumno.nombre == nombre_alumno,
        ).first()
        if not alumno:
            alumno = Alumno(grupo_id=tarea.grupo_id, nombre=nombre_alumno)
            db.add(alumno)
            db.flush()

        # Save file
        dest_dir = Path(settings.UPLOAD_DIR) / str(tarea_id) / nombre_alumno
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / archivo.filename

        content = await archivo.read()
        dest_path.write_bytes(content)

        entrega = Entrega(
            tarea_id=tarea_id,
            alumno_id=alumno.id,
            archivo_path=str(dest_path),
            status="pending",
        )
        db.add(entrega)
        db.flush()
        entregas_creadas.append(entrega)

    db.commit()
    for e in entregas_creadas:
        db.refresh(e)
    return entregas_creadas


@router.get("/entregas/{tarea_id}", response_model=list[EntregaResponse])
def get_entregas(
    tarea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_tarea_or_404(tarea_id, current_user, db)
    return db.query(Entrega).filter(Entrega.tarea_id == tarea_id).all()
