from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
import sqlalchemy as sa
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.grupo import Grupo
from app.db.models.tarea import Tarea
from app.db.models.entrega import Entrega
from app.db.models.revision import Revision
from app.api.auth import get_current_admin

router = APIRouter()


@router.get("/usuarios")
def list_usuarios(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for u in users:
        grupos_ids = db.query(Grupo.id).filter(Grupo.user_id == u.id).subquery()
        tareas_ids = db.query(Tarea.id).filter(Tarea.grupo_id.in_(grupos_ids)).subquery()
        entregas_ids = db.query(Entrega.id).filter(Entrega.tarea_id.in_(tareas_ids)).subquery()

        total_tareas = db.query(Tarea).filter(Tarea.grupo_id.in_(grupos_ids)).count()
        total_entregas = db.query(Entrega).filter(Entrega.tarea_id.in_(tareas_ids)).count()

        rev_stats = db.query(
            func.count(Revision.id).label("total"),
            func.coalesce(func.sum(Revision.tokens_input), 0).label("tokens_input"),
            func.coalesce(func.sum(Revision.tokens_output), 0).label("tokens_output"),
            func.coalesce(func.sum(Revision.costo_estimado), 0.0).label("costo"),
        ).filter(Revision.entrega_id.in_(entregas_ids)).one()

        result.append({
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if hasattr(u, "created_at") and u.created_at else None,
            "total_tareas": total_tareas,
            "total_entregas": total_entregas,
            "total_revisiones": rev_stats.total,
            "total_tokens_input": int(rev_stats.tokens_input),
            "total_tokens_output": int(rev_stats.tokens_output),
            "costo_total_estimado": round(float(rev_stats.costo), 6),
        })
    return result


@router.get("/usuarios/{user_id}/stats")
def get_usuario_stats(user_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")

    grupos_ids = db.query(Grupo.id).filter(Grupo.user_id == u.id).subquery()
    tareas_ids = db.query(Tarea.id).filter(Tarea.grupo_id.in_(grupos_ids)).subquery()
    entregas_ids = db.query(Entrega.id).filter(Entrega.tarea_id.in_(tareas_ids)).subquery()

    # Últimos 6 meses
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly = db.query(
        extract("year", Revision.created_at).label("year"),
        extract("month", Revision.created_at).label("month"),
        func.count(Revision.id).label("revisiones"),
        func.coalesce(func.sum(Revision.tokens_input), 0).label("tokens_input"),
        func.coalesce(func.sum(Revision.tokens_output), 0).label("tokens_output"),
        func.coalesce(func.sum(Revision.costo_estimado), 0.0).label("costo"),
    ).filter(
        Revision.entrega_id.in_(entregas_ids),
        Revision.created_at >= six_months_ago,
    ).group_by("year", "month").order_by("year", "month").all()

    monthly_data = [
        {
            "year": int(r.year),
            "month": int(r.month),
            "revisiones": r.revisiones,
            "tokens_input": int(r.tokens_input),
            "tokens_output": int(r.tokens_output),
            "costo": round(float(r.costo), 6),
        }
        for r in monthly
    ]

    return {
        "usuario": {"id": u.id, "nombre": u.nombre, "email": u.email},
        "por_mes": monthly_data,
    }


@router.patch("/usuarios/{user_id}/toggle-status")
def toggle_usuario_status(user_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(400, "No puedes desactivar tu propia cuenta")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    u.is_active = not u.is_active
    db.commit()
    db.refresh(u)
    return {"id": u.id, "is_active": u.is_active}


@router.delete("/usuarios/{user_id}")
def delete_usuario(user_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(400, "No puedes eliminarte a ti mismo")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    db.delete(u)
    db.commit()
    return {"detail": "Usuario eliminado"}


@router.get("/stats/global")
def get_global_stats(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    total_usuarios = db.query(User).count()
    total_tareas = db.query(Tarea).count()
    total_entregas = db.query(Entrega).count()

    rev_stats = db.query(
        func.coalesce(func.sum(Revision.tokens_input), 0).label("tokens_input"),
        func.coalesce(func.sum(Revision.tokens_output), 0).label("tokens_output"),
        func.coalesce(func.sum(Revision.costo_estimado), 0.0).label("costo"),
    ).one()

    return {
        "total_usuarios": total_usuarios,
        "total_tareas": total_tareas,
        "total_entregas": total_entregas,
        "total_tokens_input": int(rev_stats.tokens_input),
        "total_tokens_output": int(rev_stats.tokens_output),
        "costo_total": round(float(rev_stats.costo), 6),
    }
