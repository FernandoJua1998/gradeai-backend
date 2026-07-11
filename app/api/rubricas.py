"""CRUD endpoints for reusable rubrics, plus AI-assisted extraction and suggestion."""
import json
import logging
import tempfile
import os

import anthropic
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.rubrica import Rubrica
from app.services.parser import extract_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rubricas", tags=["rubricas"])

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_HAIKU = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Pydantic schemas (inline — no separate schemas file needed)
# ---------------------------------------------------------------------------


class CriterioIn(BaseModel):
    nombre: str
    ponderacion: int


class RubricaCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    criterios: list[CriterioIn]


class RubricaUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    criterios: list[CriterioIn] | None = None


class RubricaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    criterios: list
    created_at: str
    updated_at: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj: Rubrica) -> "RubricaResponse":
        return cls(
            id=obj.id,
            nombre=obj.nombre,
            descripcion=obj.descripcion,
            criterios=obj.criterios,
            created_at=obj.created_at.isoformat(),
            updated_at=obj.updated_at.isoformat() if obj.updated_at else None,
        )


class SugerirBody(BaseModel):
    nombre_tarea: str
    materia: str
    nivel_escolar: str
    tipo_tarea: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_rubrica_or_404(rubrica_id: int, user: User, db: Session) -> Rubrica:
    rubrica = db.query(Rubrica).filter(Rubrica.id == rubrica_id, Rubrica.user_id == user.id).first()
    if not rubrica:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rúbrica no encontrada")
    return rubrica


def _validate_ponderaciones(criterios: list) -> None:
    total = sum(c.ponderacion if hasattr(c, "ponderacion") else c.get("ponderacion", 0) for c in criterios)
    if total != 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Las ponderaciones deben sumar 100 (actualmente suman {total})",
        )


def _llamar_claude(system: str, user_prompt: str, label: str) -> dict:
    """Call Haiku with 2-attempt retry on JSON errors. Returns parsed dict."""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = _client.messages.create(
                model=_HAIKU,
                max_tokens=800,
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
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"No se pudo obtener respuesta válida de la IA ({label})",
    )


# ---------------------------------------------------------------------------
# Endpoints (static routes BEFORE /{id} to avoid routing conflicts)
# ---------------------------------------------------------------------------


@router.post("/extraer", status_code=status.HTTP_200_OK)
def extraer_rubrica(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Extract a rubric from an uploaded PDF or Word document using Haiku."""
    suffix = os.path.splitext(file.filename or "")[1] or ".pdf"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name

        texto = extract_text(tmp_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    system = (
        "Eres un asistente que extrae rúbricas de evaluación de documentos.\n"
        "Analiza el texto y extrae los criterios de evaluación con sus ponderaciones.\n"
        "Si las ponderaciones no suman 100, ajústalas proporcionalmente.\n"
        'Responde ÚNICAMENTE en JSON válido con este formato:\n'
        '{"nombre": str, "descripcion": str, "criterios": [{"nombre": str, "ponderacion": int}]}'
    )
    user_prompt = f"Extrae la rúbrica de este documento:\n{texto}"

    return _llamar_claude(system, user_prompt, "extraer rúbrica")


@router.post("/sugerir", status_code=status.HTTP_200_OK)
def sugerir_rubrica(
    body: SugerirBody,
    current_user: User = Depends(get_current_user),
):
    """Ask Haiku to suggest a rubric based on task metadata."""
    system = (
        "Eres un experto en evaluación educativa. Sugiere una rúbrica de evaluación completa y apropiada para la tarea descrita.\n"
        "Las ponderaciones deben sumar exactamente 100.\n"
        'Responde ÚNICAMENTE en JSON válido con este formato:\n'
        '{"nombre": str, "descripcion": str, "criterios": [{"nombre": str, "ponderacion": int}]}'
    )
    user_prompt = (
        f"Tarea: {body.nombre_tarea}\n"
        f"Materia: {body.materia}\n"
        f"Nivel escolar: {body.nivel_escolar}\n"
        f"Tipo de tarea: {body.tipo_tarea}"
    )

    return _llamar_claude(system, user_prompt, "sugerir rúbrica")


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[RubricaResponse])
def list_rubricas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rubricas = db.query(Rubrica).filter(Rubrica.user_id == current_user.id).all()
    return [RubricaResponse.from_orm_obj(r) for r in rubricas]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_rubrica(
    body: RubricaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_ponderaciones(body.criterios)
    criterios_dict = [c.model_dump() for c in body.criterios]
    rubrica = Rubrica(
        user_id=current_user.id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        criterios=criterios_dict,
    )
    db.add(rubrica)
    db.commit()
    db.refresh(rubrica)
    return RubricaResponse.from_orm_obj(rubrica)


@router.get("/{rubrica_id}")
def get_rubrica(
    rubrica_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rubrica = _get_rubrica_or_404(rubrica_id, current_user, db)
    return RubricaResponse.from_orm_obj(rubrica)


@router.put("/{rubrica_id}")
def update_rubrica(
    rubrica_id: int,
    body: RubricaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rubrica = _get_rubrica_or_404(rubrica_id, current_user, db)
    if body.nombre is not None:
        rubrica.nombre = body.nombre
    if body.descripcion is not None:
        rubrica.descripcion = body.descripcion
    if body.criterios is not None:
        _validate_ponderaciones(body.criterios)
        rubrica.criterios = [c.model_dump() for c in body.criterios]
    db.commit()
    db.refresh(rubrica)
    return RubricaResponse.from_orm_obj(rubrica)


@router.delete("/{rubrica_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rubrica(
    rubrica_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rubrica = _get_rubrica_or_404(rubrica_id, current_user, db)
    db.delete(rubrica)
    db.commit()
