"""Async grading engine: processes all pending submissions for a task."""
import logging

from sqlalchemy.orm import Session

from app.db.models.entrega import Entrega
from app.db.models.revision import Revision
from app.db.models.tarea import Tarea
from app.services.detector import detectar_ia
from app.services.parser import extract_text
from app.services.revisor import revisar_entrega

logger = logging.getLogger(__name__)


def procesar_tarea(tarea_id: int, db: Session) -> None:
    tarea: Tarea = db.get(Tarea, tarea_id)
    if not tarea:
        logger.error("Tarea %d no encontrada", tarea_id)
        return

    entregas = (
        db.query(Entrega)
        .filter(Entrega.tarea_id == tarea_id, Entrega.status == "pending")
        .all()
    )

    for entrega in entregas:
        try:
            entrega.status = "processing"
            db.commit()

            texto = extract_text(entrega.archivo_path)

            resultado = revisar_entrega(texto, tarea.criterios, tarea.rubrica_path)

            ia_result = None
            config_ia = tarea.config_ia or {}
            if config_ia.get("modo", "informacional") != "desactivado":
                ia_result = detectar_ia(texto)

            revision = Revision(
                entrega_id=entrega.id,
                calificacion=resultado.get("calificacion_total"),
                desglose=resultado.get("desglose", []),
                retroalimentacion=resultado.get("retroalimentacion"),
                ia_probabilidad=ia_result.get("probabilidad") if ia_result else None,
                ia_nivel_riesgo=ia_result.get("nivel_riesgo") if ia_result else None,
                ia_fragmentos=ia_result.get("fragmentos", []) if ia_result else [],
            )
            db.add(revision)

            entrega.status = "done"
            db.commit()

        except Exception as exc:
            logger.exception("Error procesando entrega %d: %s", entrega.id, exc)
            entrega.status = "error"
            db.commit()
