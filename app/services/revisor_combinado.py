"""Combined grading + AI detection in a single Claude API call."""
import json
import logging

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_SYSTEM_PROMPT = """\
Eres un asistente de evaluación académica. Tu tarea es:
1. Revisar y calificar la entrega del alumno según los criterios.
2. Detectar si el texto fue generado por inteligencia artificial.
Responde ÚNICAMENTE en JSON válido con este formato exacto:
{
  "desglose": [{"criterio": str, "ponderacion": int, "puntos": float, "comentario": str}],
  "calificacion_total": float,
  "retroalimentacion": str,
  "ia_probabilidad": float,
  "ia_nivel_riesgo": "bajo"|"medio"|"alto",
  "ia_fragmentos": [{"texto": str, "razon": str}]
}"""

_FALLBACK_RESULT = {
    "desglose": [],
    "calificacion_total": 0.0,
    "retroalimentacion": "No se pudo completar la revisión automática debido a un error en el servicio de IA.",
    "ia_probabilidad": 0.0,
    "ia_nivel_riesgo": "bajo",
    "ia_fragmentos": [],
}


def revisar_y_detectar(texto: str, criterios: list, rubrica: str | None) -> dict:
    criterios_json = json.dumps(criterios, ensure_ascii=False)
    rubrica_texto = rubrica if rubrica else "No proporcionada"

    user_prompt = (
        f"Criterios de evaluación: {criterios_json}\n"
        f"Hoja de respuestas: {rubrica_texto}\n"
        f"Tarea del alumno:\n{texto}"
    )

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                timeout=30.0,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning("Intento %d: JSON inválido en respuesta combinada: %s", attempt + 1, e)
        except anthropic.APITimeoutError as e:
            last_error = e
            logger.warning("Intento %d: timeout al llamar Claude API en revisor combinado", attempt + 1)

    logger.error("Revisor combinado falló tras 2 intentos: %s. Retornando resultado vacío.", last_error)
    return _FALLBACK_RESULT
