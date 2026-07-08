"""Mixed-model grading pipeline: Haiku for grading, Sonnet for AI detection."""
import json
import logging

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_SYSTEM_PROMPT_CALIFICACION = """\
Eres un asistente de evaluación académica. Revisa y califica \
la entrega del alumno según los criterios. Sé justo y detallado.
Responde ÚNICAMENTE en JSON válido con este formato exacto:
{
  "desglose": [{"criterio": str, "ponderacion": int, "puntos": float, "comentario": str}],
  "calificacion_total": float,
  "retroalimentacion": str
}"""

_SYSTEM_PROMPT_DETECCION = """\
Eres un experto en detectar texto generado por inteligencia artificial.
Analiza el texto considerando: uniformidad excesiva, vocabulario atípico
para el nivel escolar, ausencia de errores naturales, frases genéricas,
estructura demasiado perfecta.
Responde ÚNICAMENTE en JSON válido con este formato exacto:
{
  "ia_probabilidad": float (0-100),
  "ia_nivel_riesgo": "bajo"|"medio"|"alto",
  "ia_fragmentos": [{"texto": str, "razon": str}]
}"""

_FALLBACK_CALIFICACION = {
    "desglose": [],
    "calificacion_total": 0.0,
    "retroalimentacion": "No se pudo completar la revisión automática debido a un error en el servicio de IA.",
}

_FALLBACK_DETECCION = {
    "ia_probabilidad": 0.0,
    "ia_nivel_riesgo": "bajo",
    "ia_fragmentos": [],
}


def _llamar_claude(model: str, max_tokens: int, system: str, user_prompt: str, label: str) -> dict | None:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = _client.messages.create(
                model=model,
                max_tokens=max_tokens,
                timeout=30.0,
                system=system,
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
            logger.warning("Intento %d: JSON inválido en %s: %s", attempt + 1, label, e)
        except anthropic.APITimeoutError as e:
            last_error = e
            logger.warning("Intento %d: timeout en %s", attempt + 1, label)
    logger.error("%s falló tras 2 intentos: %s", label, last_error)
    return None


def revisar_y_detectar(texto: str, criterios: list, rubrica: str | None, config_ia: dict | None = None) -> dict:
    criterios_json = json.dumps(criterios, ensure_ascii=False)
    rubrica_texto = rubrica if rubrica else "No proporcionada"
    prompt_calificacion = (
        f"Criterios de evaluación: {criterios_json}\n"
        f"Hoja de respuestas: {rubrica_texto}\n"
        f"Tarea del alumno:\n{texto}"
    )

    calificacion = _llamar_claude(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=_SYSTEM_PROMPT_CALIFICACION,
        user_prompt=prompt_calificacion,
        label="calificación (Haiku)",
    ) or _FALLBACK_CALIFICACION

    modo = (config_ia or {}).get("modo", "informacional")
    if modo == "desactivado":
        deteccion = _FALLBACK_DETECCION
    else:
        deteccion = _llamar_claude(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=_SYSTEM_PROMPT_DETECCION,
            user_prompt=f"Analiza el siguiente texto:\n{texto}",
            label="detección IA (Sonnet)",
        ) or _FALLBACK_DETECCION

    return {
        "desglose": calificacion.get("desglose", []),
        "calificacion_total": calificacion.get("calificacion_total", 0.0),
        "retroalimentacion": calificacion.get("retroalimentacion"),
        "ia_probabilidad": deteccion.get("ia_probabilidad", 0.0),
        "ia_nivel_riesgo": deteccion.get("ia_nivel_riesgo", "bajo"),
        "ia_fragmentos": deteccion.get("ia_fragmentos", []),
    }
