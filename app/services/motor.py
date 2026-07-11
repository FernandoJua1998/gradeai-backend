"""Async grading engine: processes all pending submissions for a task."""
import concurrent.futures
import logging
import traceback

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_TIMEOUT_POR_ENTREGA = 90  # segundos


def _procesar_entrega(entrega_id: int, tarea_criterios, tarea_rubrica, tarea_config_ia, db_url: str):
    """Corre en thread separado con su propia sesión de BD."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.models.entrega import Entrega
    from app.db.models.revision import Revision
    from app.services.parser import extract_text
    from app.services.revisor_combinado import revisar_y_detectar

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        entrega = db.query(Entrega).filter(Entrega.id == entrega_id).first()
        if not entrega:
            return

        entrega.status = "processing"
        db.commit()

        texto = extract_text(entrega.archivo_path)
        resultado = revisar_y_detectar(texto, tarea_criterios, tarea_rubrica, tarea_config_ia)

        revision = Revision(
            entrega_id=entrega.id,
            calificacion=resultado.get("calificacion_total", 0),
            desglose=resultado.get("desglose", []),
            retroalimentacion=resultado.get("retroalimentacion", ""),
            ia_probabilidad=resultado.get("ia_probabilidad", 0),
            ia_nivel_riesgo=resultado.get("ia_nivel_riesgo", "bajo"),
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
        logger.info("[MOTOR] Entrega %d completada", entrega_id)

    except Exception as e:
        logger.error("[MOTOR] ERROR entrega %d: %s", entrega_id, e)
        traceback.print_exc()
        try:
            entrega = db.query(Entrega).filter(Entrega.id == entrega_id).first()
            if entrega:
                entrega.status = "error"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
        engine.dispose()


def procesar_tarea(tarea_id: int, db: Session) -> None:
    from app.core.config import settings
    from app.db.models.entrega import Entrega
    from app.db.models.tarea import Tarea

    tarea = db.query(Tarea).filter(Tarea.id == tarea_id).first()
    if not tarea:
        logger.error("Tarea %d no encontrada", tarea_id)
        return

    entregas = db.query(Entrega).filter(
        Entrega.tarea_id == tarea_id,
        Entrega.status == "pending",
    ).all()

    entrega_ids = [e.id for e in entregas]
    criterios = tarea.criterios
    rubrica = tarea.rubrica_path
    config_ia = tarea.config_ia
    db_url = settings.DATABASE_URL

    for entrega_id in entrega_ids:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _procesar_entrega,
                entrega_id, criterios, rubrica, config_ia, db_url,
            )
            try:
                future.result(timeout=_TIMEOUT_POR_ENTREGA)
            except concurrent.futures.TimeoutError:
                logger.error("[MOTOR] TIMEOUT entrega %d (límite %ds)", entrega_id, _TIMEOUT_POR_ENTREGA)
                entrega = db.query(Entrega).filter(Entrega.id == entrega_id).first()
                if entrega:
                    entrega.status = "error"
                    db.commit()
            except Exception as e:
                logger.error("[MOTOR] ERROR INESPERADO entrega %d: %s", entrega_id, e)
