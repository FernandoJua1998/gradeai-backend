"""Endpoints for triggering grading, polling status, retrieving results, and exporting."""
from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.models.alumno import Alumno
from app.db.models.entrega import Entrega
from app.db.models.grupo import Grupo
from app.db.models.revision import Revision
from app.db.models.tarea import Tarea
from app.db.models.user import User
from app.db.session import get_db
from app.services.exportar import generar_excel
from app.services.motor import procesar_tarea

router = APIRouter(tags=["revision"])


def _get_tarea_or_404(tarea_id: int, user: User, db: Session) -> Tarea:
    tarea = (
        db.query(Tarea)
        .join(Grupo)
        .filter(Tarea.id == tarea_id, Grupo.user_id == user.id)
        .first()
    )
    if not tarea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return tarea


@router.post("/revision/{tarea_id}")
def iniciar_revision(
    tarea_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tarea = _get_tarea_or_404(tarea_id, current_user, db)
    total = db.query(Entrega).filter(Entrega.tarea_id == tarea_id).count()

    # Reset any previous error/done states to pending so they get reprocessed
    (
        db.query(Entrega)
        .filter(Entrega.tarea_id == tarea_id, Entrega.status.in_(["done", "error"]))
        .update({"status": "pending"})
    )
    db.commit()

    background_tasks.add_task(procesar_tarea, tarea.id, db)
    return {"status": "iniciado", "tarea_id": tarea_id, "total_entregas": total}


@router.get("/revision/status/{tarea_id}")
def get_status(
    tarea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_tarea_or_404(tarea_id, current_user, db)

    entregas = db.query(Entrega).filter(Entrega.tarea_id == tarea_id).all()
    total = len(entregas)
    completadas = sum(1 for e in entregas if e.status == "done")
    errores = sum(1 for e in entregas if e.status == "error")

    if total == 0 or completadas + errores == 0:
        general = "pendiente"
    elif completadas + errores < total:
        general = "en_progreso"
    elif errores > 0:
        general = "con_errores"
    else:
        general = "completado"

    return {
        "tarea_id": tarea_id,
        "total": total,
        "completadas": completadas,
        "errores": errores,
        "status": general,
    }


@router.get("/resultados/{tarea_id}")
def get_resultados(
    tarea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_tarea_or_404(tarea_id, current_user, db)

    entregas = (
        db.query(Entrega)
        .join(Alumno)
        .filter(Entrega.tarea_id == tarea_id)
        .all()
    )

    results = []
    for entrega in entregas:
        revision: Revision | None = entrega.revision
        results.append(
            {
                "entrega_id": entrega.id,
                "alumno": entrega.alumno.nombre,
                "calificacion": revision.calificacion if revision else None,
                "ia_probabilidad": revision.ia_probabilidad if revision else None,
                "ia_nivel_riesgo": revision.ia_nivel_riesgo if revision else None,
                "status": entrega.status,
            }
        )

    return sorted(results, key=lambda r: (r["calificacion"] or 0), reverse=True)


@router.get("/resultados/alumno/{entrega_id}")
def get_detalle_alumno(
    entrega_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entrega = (
        db.query(Entrega)
        .join(Tarea)
        .join(Grupo)
        .filter(Entrega.id == entrega_id, Grupo.user_id == current_user.id)
        .first()
    )
    if not entrega:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega no encontrada")

    revision: Revision | None = entrega.revision
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revisión no disponible")

    return {
        "alumno": entrega.alumno.nombre,
        "calificacion_total": revision.calificacion,
        "desglose": revision.desglose,
        "retroalimentacion": revision.retroalimentacion,
        "ia_probabilidad": revision.ia_probabilidad,
        "ia_nivel_riesgo": revision.ia_nivel_riesgo,
        "ia_fragmentos": revision.ia_fragmentos,
    }


@router.get("/exportar/{tarea_id}")
def exportar_excel(
    tarea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_tarea_or_404(tarea_id, current_user, db)
    excel_bytes = generar_excel(tarea_id, db)
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=resultados_{tarea_id}.xlsx"},
    )
