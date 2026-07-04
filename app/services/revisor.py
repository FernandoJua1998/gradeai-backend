"""Automatic assignment grading via Claude API."""
import json
import logging

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_SYSTEM_PROMPT = """\
Eres un asistente de evaluación académica. Revisa la entrega del alumno
y califica según los criterios provistos. Sé justo, detallado y constructivo.
Responde ÚNICAMENTE en JSON válido con este formato exacto:
{
  "desglose": [
    {"criterio": str, "ponderacion": int, "puntos": float, "comentario": str}
  ],
  "calificacion_total": float,
  "retroalimentacion": str
}"""

_FALLBACK_RESULT = {
    "desglose": [],
    "calificacion_total": 0.0,
    "retroalimentacion": "No se pudo completar la revisión automática debido a un error en el servicio de IA.",
}


def revisar_entrega(texto: str, criterios: list, rubrica: str | None) -> dict:
    criterios_json = json.dumps(criterios, ensure_ascii=False)
    rubrica_texto = rubrica if rubrica else "No proporcionada"

    user_prompt = (
        f"Criterios de evaluación: {criterios_json}\n"
        f"Hoja de respuestas: {rubrica_texto}\n"
        f"Tarea del alumno:\n{texto}"
    )

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                timeout=30.0,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning("Intento %d: JSON inválido en respuesta del revisor: %s", attempt + 1, e)
        except anthropic.APITimeoutError as e:
            last_error = e
            logger.warning("Intento %d: timeout al llamar Claude API en revisor", attempt + 1)

    logger.error("Revisor falló tras 3 intentos: %s. Retornando resultado vacío.", last_error)
    return _FALLBACK_RESULT
