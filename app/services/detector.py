"""AI-generated content detection via Claude API."""
import json
import logging

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_SYSTEM_PROMPT = """\
Eres un experto en detectar texto generado por inteligencia artificial.
Analiza el texto considerando: uniformidad excesiva, vocabulario atípico
para el nivel escolar, ausencia de errores naturales, frases genéricas,
estructura demasiado perfecta.
Responde ÚNICAMENTE en JSON válido con este formato exacto:
{
  "probabilidad": float (0-100),
  "nivel_riesgo": "bajo" | "medio" | "alto",
  "fragmentos": [
    {"texto": str, "razon": str}
  ]
}"""


def detectar_ia(texto: str) -> dict:
    for attempt in range(3):
        try:
            response = _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Analiza el siguiente texto:\n{texto}"}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            # Enforce nivel_riesgo based on probabilidad
            prob = float(result.get("probabilidad", 0))
            if prob < 40:
                result["nivel_riesgo"] = "bajo"
            elif prob <= 70:
                result["nivel_riesgo"] = "medio"
            else:
                result["nivel_riesgo"] = "alto"
            return result
        except json.JSONDecodeError as e:
            logger.warning("Intento %d: JSON inválido en respuesta del detector: %s", attempt + 1, e)
            if attempt == 2:
                raise ValueError("El modelo no devolvió JSON válido tras 3 intentos") from e
