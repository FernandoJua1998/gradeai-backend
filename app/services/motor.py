"""Grading engine: processes pending submissions for a task via FastAPI BackgroundTasks."""
import traceback

from app.db.session import SessionLocal
from app.db.models.entrega import Entrega
from app.db.models.tarea import Tarea
from app.db.models.revision import Revision
from app.services.parser import extract_text
from app.services.revisor_combinado import revisar_y_detectar


def procesar_tarea_simple(tarea_id: int):
    print(f"[MOTOR] Iniciando procesamiento de tarea {tarea_id}")
    db = SessionLocal()
    try:
        tarea = db.query(Tarea).filter(Tarea.id == tarea_id).first()
        if not tarea:
            print(f"[MOTOR] Tarea {tarea_id} no encontrada")
            return

        entregas = db.query(Entrega).filter(
            Entrega.tarea_id == tarea_id,
            Entrega.status == "pending",
        ).all()

        print(f"[MOTOR] {len(entregas)} entregas pendientes")

        for entrega in entregas:
            print(f"[MOTOR] Procesando entrega {entrega.id}")
            try:
                entrega.status = "processing"
                db.commit()

                texto = extract_text(entrega.archivo_path)
                print(f"[MOTOR] Texto extraído: {len(texto)} chars")

                resultado = revisar_y_detectar(
                    texto,
                    tarea.criterios,
                    tarea.rubrica_path,
                    tarea.config_ia,
                )
                print(f"[MOTOR] Revisión completada: {resultado.get('calificacion_total')}")

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
                print(f"[MOTOR] Entrega {entrega.id} → done")

            except Exception as e:
                print(f"[MOTOR] ERROR entrega {entrega.id}: {e}")
                traceback.print_exc()
                try:
                    entrega.status = "error"
                    db.commit()
                except Exception:
                    db.rollback()

    except Exception as e:
        print(f"[MOTOR] ERROR GENERAL: {e}")
        traceback.print_exc()
    finally:
        db.close()
        print(f"[MOTOR] Procesamiento tarea {tarea_id} finalizado")
