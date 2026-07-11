"""Async grading engine: processes all pending submissions for a task."""
import logging
import signal

from sqlalchemy.orm import Session

from app.db.models.alumno import Alumno
from app.db.models.entrega import Entrega
from app.db.models.revision import Revision
from app.db.models.tarea import Tarea
from app.services.parser import extract_text
from app.services.revisor_combinado import revisar_y_detectar

logger = logging.getLogger(__name__)

_TIMEOUT_POR_ENTREGA = 120  # segundos


def _timeout_handler(signum, frame):
    raise TimeoutError("Revisión tardó demasiado")


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

            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(_TIMEOUT_POR_ENTREGA)
            try:
                texto = extract_text(entrega.archivo_path)
                resultado = revisar_y_detectar(texto, tarea.criterios, tarea.rubrica_path, tarea.config_ia)
            finally:
                signal.alarm(0)  # cancelar alarma siempre

            revision = Revision(
                entrega_id=entrega.id,
                calificacion=resultado.get("calificacion_total"),
                desglose=resultado.get("desglose", []),
                retroalimentacion=resultado.get("retroalimentacion"),
                ia_probabilidad=resultado.get("ia_probabilidad"),
                ia_nivel_riesgo=resultado.get("ia_nivel_riesgo"),
                ia_fragmentos=resultado.get("ia_fragmentos", []),
                tokens_input=resultado.get("tokens_input_haiku", 0) + resultado.get("tokens_input_sonnet", 0),
                tokens_output=resultado.get("tokens_output_haiku", 0) + resultado.get("tokens_output_sonnet", 0),
                costo_estimado=resultado.get("costo_estimado", 0.0),
                modelo_calificacion="claude-haiku-4-5-20251001",
                modelo_deteccion="claude-sonnet-4-6",
            )
            db.add(revision)

            entrega.status = "done"
            db.commit()
            logger.info("Entrega procesada: alumno=%s entrega_id=%d", alumno_nombre, entrega.id)

        except TimeoutError:
            logger.error(
                "Timeout procesando entrega: alumno=%s entrega_id=%d (límite %ds)",
                alumno_nombre, entrega.id, _TIMEOUT_POR_ENTREGA,
            )
            try:
                entrega.status = "error"
                db.commit()
            except Exception:
                db.rollback()
                entrega.status = "error"
                db.commit()

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
