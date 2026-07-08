"""Async grading engine: processes all pending submissions for a task."""
import logging

from sqlalchemy.orm import Session

from app.db.models.alumno import Alumno
from app.db.models.entrega import Entrega
from app.db.models.revision import Revision
from app.db.models.tarea import Tarea
from app.services.parser import extract_text
from app.services.revisor_combinado import revisar_y_detectar

logger = logging.getLogger(__name__)


def procesar_tarea(tarea_id: int, db: Session) -> None:
    tarea: Tarea = db.get(Tarea, tarea_id)
    if not tarea:
        logger.error("Tarea %d no encontrada", tarea_id)
        return

    entregas = (
        db.query(Entrega)
        .join(Alumno)
        .filter(Entrega.tarea_id == tarea_id, Entrega.status == "pending")
        .all()
    )

    for entrega in entregas:
        alumno_nombre = entrega.alumno.nombre if entrega.alumno else f"id={entrega.id}"
        try:
            entrega.status = "processing"
            db.commit()

            texto = extract_text(entrega.archivo_path)

            resultado = revisar_y_detectar(texto, tarea.criterios, tarea.rubrica_path, tarea.config_ia)

            revision = Revision(
                entrega_id=entrega.id,
                calificacion=resultado.get("calificacion_total"),
                desglose=resultado.get("desglose", []),
                retroalimentacion=resultado.get("retroalimentacion"),
                ia_probabilidad=resultado.get("ia_probabilidad"),
                ia_nivel_riesgo=resultado.get("ia_nivel_riesgo"),
                ia_fragmentos=resultado.get("ia_fragmentos", []),
            )
            db.add(revision)

            entrega.status = "done"
            db.commit()
            logger.info("Entrega procesada: alumno=%s entrega_id=%d", alumno_nombre, entrega.id)

        except Exception as exc:
            error_type = type(exc).__name__
            logger.exception(
                "Error procesando entrega: alumno=%s entrega_id=%d error=%s: %s",
                alumno_nombre, entrega.id, error_type, exc,
            )
            # Ensure entrega never stays in "processing" state
            try:
                entrega.status = "error"
                db.commit()
            except Exception:
                db.rollback()
                entrega.status = "error"
                db.commit()
