"""Tests for app/services/parser.py — PDF and Word extraction."""
import os
import tempfile

import pytest


def _create_pdf(text: str) -> str:
    """Create a minimal valid PDF with given text, return path."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), text)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    doc.save(tmp.name)
    doc.close()
    return tmp.name


def _create_docx(text: str) -> str:
    """Create a minimal .docx with given text, return path."""
    from docx import Document

    doc = Document()
    doc.add_paragraph(text)
    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    doc.save(tmp.name)
    return tmp.name


def test_extract_pdf():
    from app.services.parser import extract_text

    content = "Este es el contenido de la tarea del alumno para el test."
    path = _create_pdf(content)
    try:
        result = extract_text(path)
        assert len(result) >= 20
        assert "tarea" in result.lower() or "alumno" in result.lower()
    finally:
        os.unlink(path)


def test_extract_docx():
    from app.services.parser import extract_text

    content = "Este es el contenido del documento Word para el test de la tarea."
    path = _create_docx(content)
    try:
        result = extract_text(path)
        assert len(result) >= 20
        assert "documento" in result.lower() or "tarea" in result.lower()
    finally:
        os.unlink(path)


def test_extract_pdf_encrypted_raises():
    """An encrypted PDF should raise ValueError."""
    import fitz

    doc = fitz.open()
    doc.new_page()
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    doc.save(tmp.name, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret")
    doc.close()

    from app.services.parser import extract_text

    try:
        with pytest.raises(ValueError, match="encriptado"):
            extract_text(tmp.name)
    finally:
        os.unlink(tmp.name)


def test_extract_unsupported_format_raises():
    from app.services.parser import extract_text

    with pytest.raises(ValueError, match="no soportado"):
        extract_text("archivo.txt")


def test_extract_short_text_raises():
    """A PDF with almost no text should raise ValueError."""
    import fitz

    doc = fitz.open()
    doc.new_page()  # blank page
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    doc.save(tmp.name)
    doc.close()

    from app.services.parser import extract_text

    try:
        with pytest.raises(ValueError, match="texto útil"):
            extract_text(tmp.name)
    finally:
        os.unlink(tmp.name)
