"""Text extraction from PDF, Word, and image files."""
import base64
from pathlib import Path

import anthropic
import fitz  # pymupdf
from docx import Document

from app.core.config import settings

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        text = _extract_pdf(file_path)
    elif ext == ".docx":
        text = _extract_docx(file_path)
    elif ext in _IMAGE_EXTENSIONS:
        text = _extract_image_via_claude(file_path, ext)
    else:
        raise ValueError(f"Formato de archivo no soportado: {ext}")

    if len(text.strip()) < 20:
        raise ValueError("No se pudo extraer texto útil del archivo")

    return text.strip()


def _extract_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def _extract_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_image_via_claude(file_path: str, ext: str) -> str:
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    media_type = media_type_map[ext]

    with open(file_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": "Transcribe el texto de esta imagen"},
                ],
            }
        ],
    )
    return response.content[0].text
