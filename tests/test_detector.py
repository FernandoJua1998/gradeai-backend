"""Tests for app/services/detector.py — AI detection (mocked)."""
import json

import pytest


MOCK_BAJO = {
    "probabilidad": 15.0,
    "nivel_riesgo": "bajo",
    "fragmentos": [],
}

MOCK_ALTO = {
    "probabilidad": 85.0,
    "nivel_riesgo": "alto",
    "fragmentos": [
        {"texto": "La inteligencia artificial es un campo vasto.", "razon": "Frases demasiado genéricas"},
    ],
}


def _make_mock_response(content: str):
    class MockContent:
        text = content

    class MockResponse:
        content = [MockContent()]

    return MockResponse()


def test_detectar_ia_mock_bajo(mocker):
    mocker.patch(
        "app.services.detector._client.messages.create",
        return_value=_make_mock_response(json.dumps(MOCK_BAJO)),
    )

    from app.services.detector import detectar_ia

    result = detectar_ia("Texto escrito por un alumno de forma natural con errores.")

    assert "probabilidad" in result
    assert "nivel_riesgo" in result
    assert "fragmentos" in result
    assert result["nivel_riesgo"] == "bajo"
    assert result["probabilidad"] == 15.0


def test_detectar_ia_mock_alto(mocker):
    mocker.patch(
        "app.services.detector._client.messages.create",
        return_value=_make_mock_response(json.dumps(MOCK_ALTO)),
    )

    from app.services.detector import detectar_ia

    result = detectar_ia("La inteligencia artificial es un campo vasto y en constante evolución.")

    assert result["nivel_riesgo"] == "alto"
    assert result["probabilidad"] == 85.0
    assert len(result["fragmentos"]) == 1


def test_detectar_ia_nivel_riesgo_overridden_by_probability(mocker):
    """nivel_riesgo should be recalculated from probabilidad, ignoring model's value."""
    wrong_nivel = {"probabilidad": 60.0, "nivel_riesgo": "bajo", "fragmentos": []}
    mocker.patch(
        "app.services.detector._client.messages.create",
        return_value=_make_mock_response(json.dumps(wrong_nivel)),
    )

    from app.services.detector import detectar_ia

    result = detectar_ia("Texto de prueba.")
    # 60% should be "medio" regardless of what the model said
    assert result["nivel_riesgo"] == "medio"


def test_detectar_ia_retries_on_invalid_json(mocker):
    mocker.patch(
        "app.services.detector._client.messages.create",
        return_value=_make_mock_response("no es json"),
    )

    from app.services.detector import detectar_ia

    with pytest.raises(ValueError, match="JSON válido"):
        detectar_ia("Texto de prueba.")
