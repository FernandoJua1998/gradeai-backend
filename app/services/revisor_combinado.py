"""Mixed-model grading pipeline: Haiku for grading, Sonnet for AI detection."""
import json
import logging

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_SYSTEM_PROMPT_CALIFICACION = """\
Eres un asistente de evaluación académica. Revisa y califica \
la entrega del alumno según los criterios provistos.

IMPORTANTE sobre la calificación:
- Cada criterio tiene una ponderación sobre 100
- Los "puntos" de cada criterio deben ser un valor entre 0 \
y su ponderación (ej: si ponderacion=80, puntos puede ser \
entre 0.0 y 80.0)
- calificacion_total es la suma de todos los puntos obtenidos
- Ejemplo: criterio redacción ponderacion=80, puntos=65.0
           criterio referencias ponderacion=20, puntos=0.0
           calificacion_total=65.0

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
    data, _ = _llamar_claude_con_uso(model, max_tokens, system, user_prompt, label)
    return data


def _llamar_claude_con_uso(
    model: str, max_tokens: int, system: str, user_prompt: str, label: str
) -> tuple[dict | None, tuple[int, int]]:
    """Call Claude and return (parsed_dict, (input_tokens, output_tokens)).
    On failure returns (None, (0, 0))."""
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
            parsed = json.loads(raw)
            usage = (response.usage.input_tokens, response.usage.output_tokens)
            return parsed, usage
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning("Intento %d: JSON inválido en %s: %s", attempt + 1, label, e)
        except anthropic.APITimeoutError as e:
            last_error = e
            logger.warning("Intento %d: timeout en %s", attempt + 1, label)
    logger.error("%s falló tras 2 intentos: %s", label, last_error)
    return None, (0, 0)


_ZERO_TOKEN_FIELDS = {
    "tokens_input_haiku": 0,
    "tokens_output_haiku": 0,
    "tokens_input_sonnet": 0,
    "tokens_output_sonnet": 0,
    "costo_estimado": 0.0,
}


def revisar_y_detectar(texto: str, criterios: list, rubrica: str | None, config_ia: dict | None = None) -> dict:
    texto = texto[:8000]
    criterios_json = json.dumps(criterios, ensure_ascii=False)
    rubrica_texto = rubrica if rubrica else "No proporcionada"
    prompt_calificacion = (
        f"Criterios de evaluación: {criterios_json}\n"
        f"Hoja de respuestas: {rubrica_texto}\n"
        f"Tarea del alumno:\n{texto}"
    )

    calificacion_data, (tokens_input_haiku, tokens_output_haiku) = _llamar_claude_con_uso(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=_SYSTEM_PROMPT_CALIFICACION,
        user_prompt=prompt_calificacion,
        label="calificación (Haiku)",
    )
    calificacion = calificacion_data or _FALLBACK_CALIFICACION

    modo = (config_ia or {}).get("modo", "informacional")
    if modo == "desactivado":
        deteccion = _FALLBACK_DETECCION
        tokens_input_sonnet, tokens_output_sonnet = 0, 0
    else:
        deteccion_data, (tokens_input_sonnet, tokens_output_sonnet) = _llamar_claude_con_uso(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_SYSTEM_PROMPT_DETECCION,
            user_prompt=f"Analiza el siguiente texto:\n{texto}",
            label="detección IA (Sonnet)",
        )
        deteccion = deteccion_data or _FALLBACK_DETECCION

    costo_estimado = (
        (tokens_input_haiku / 1_000_000 * 0.80)
        + (tokens_output_haiku / 1_000_000 * 4.00)
        + (tokens_input_sonnet / 1_000_000 * 3.00)
        + (tokens_output_sonnet / 1_000_000 * 15.00)
    )

    return {
        "desglose": calificacion.get("desglose", []),
        "calificacion_total": calificacion.get("calificacion_total", 0.0),
        "retroalimentacion": calificacion.get("retroalimentacion"),
        "ia_probabilidad": deteccion.get("ia_probabilidad", 0.0),
        "ia_nivel_riesgo": deteccion.get("ia_nivel_riesgo", "bajo"),
        "ia_fragmentos": deteccion.get("ia_fragmentos", []),
        "tokens_input_haiku": tokens_input_haiku,
        "tokens_output_haiku": tokens_output_haiku,
        "tokens_input_sonnet": tokens_input_sonnet,
        "tokens_output_sonnet": tokens_output_sonnet,
        "costo_estimado": costo_estimado,
    }
