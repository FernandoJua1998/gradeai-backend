"""Tests for app/services/revisor.py — grading via Claude API (mocked)."""
import json

import pytest


CRITERIOS = [
    {"nombre": "Comprensión", "descripcion": "Entiende el tema", "peso": 0.5},
    {"nombre": "Redacción", "descripcion": "Escribe con claridad", "peso": 0.5},
]

MOCK_RESPONSE = {
    "desglose": [
        {"criterio": "Comprensión", "ponderacion": 50, "puntos": 40.0, "comentario": "Buen entendimiento"},
        {"criterio": "Redacción", "ponderacion": 50, "puntos": 45.0, "comentario": "Muy clara"},
    ],
    "calificacion_total": 85.0,
    "retroalimentacion": "Buen trabajo en general. Puede mejorar la profundidad de análisis.",
}


def _make_mock_response(content: str):
    """Build a minimal mock that looks like an Anthropic response."""
    class MockContent:
        text = content

    class MockResponse:
        content = [MockContent()]

    return MockResponse()


def test_revisar_entrega_mock(mocker):
    mocker.patch(
        "app.services.revisor._client.messages.create",
        return_value=_make_mock_response(json.dumps(MOCK_RESPONSE)),
    )

    from app.services.revisor import revisar_entrega

    result = revisar_entrega("Texto de la tarea del alumno.", CRITERIOS, None)

    assert "desglose" in result
    assert "calificacion_total" in result
    assert "retroalimentacion" in result
    assert result["calificacion_total"] == 85.0
    assert len(result["desglose"]) == 2


def test_revisar_entrega_retries_on_invalid_json(mocker):
    """Should retry twice on JSON error, then return fallback."""
    mocker.patch(
        "app.services.revisor._client.messages.create",
        return_value=_make_mock_response("esto no es json {{{"),
    )

    from app.services.revisor import revisar_entrega

    result = revisar_entrega("Texto de prueba para el test.", CRITERIOS, None)

    # After 3 failed attempts, fallback result is returned
    assert result["calificacion_total"] == 0.0
    assert "retroalimentacion" in result


def test_revisar_entrega_strips_markdown_fences(mocker):
    """Should strip ```json ... ``` wrappers before parsing."""
    wrapped = f"```json\n{json.dumps(MOCK_RESPONSE)}\n```"
    mocker.patch(
        "app.services.revisor._client.messages.create",
        return_value=_make_mock_response(wrapped),
    )

    from app.services.revisor import revisar_entrega

    result = revisar_entrega("Texto de prueba.", CRITERIOS, "rubrica de ejemplo")
    assert result["calificacion_total"] == 85.0
