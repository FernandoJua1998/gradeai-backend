from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.api.auth import get_current_user

router = APIRouter()


def get_current_admin(
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    return current_user


@router.get("/usuarios")
def list_usuarios(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    from app.db.models.grupo import Grupo
    from app.db.models.tarea import Tarea
    from app.db.models.entrega import Entrega
    from app.db.models.revision import Revision

    usuarios = db.query(User).all()
    resultado = []
    for u in usuarios:
        grupos = db.query(Grupo).filter(Grupo.user_id == u.id).all()
        grupo_ids = [g.id for g in grupos]

        tareas = db.query(Tarea).filter(Tarea.grupo_id.in_(grupo_ids)).all() if grupo_ids else []
        tarea_ids = [t.id for t in tareas]

        entregas = db.query(Entrega).filter(Entrega.tarea_id.in_(tarea_ids)).all() if tarea_ids else []
        entrega_ids = [e.id for e in entregas]

        revisiones = db.query(Revision).filter(Revision.entrega_id.in_(entrega_ids)).all() if entrega_ids else []

        tokens = 0
        costo = 0.0
        for r in revisiones:
            try:
                tokens += (getattr(r, 'tokens_input', 0) or 0) + (getattr(r, 'tokens_output', 0) or 0)
                costo += getattr(r, 'costo_estimado', 0.0) or 0.0
            except Exception:
                pass

        resultado.append({
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "role": u.role or "teacher",
            "is_active": u.is_active if u.is_active is not None else True,
            "total_tareas": len(tareas),
            "total_entregas": len(entregas),
            "tokens_consumidos": tokens,
            "costo_estimado": costo,
        })
    return resultado


@router.get("/stats/global")
def get_global_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    from app.db.models.tarea import Tarea
    from app.db.models.entrega import Entrega
    from app.db.models.revision import Revision

    total_usuarios = db.query(User).count()
    total_tareas = db.query(Tarea).count()
    total_entregas = db.query(Entrega).count()

    revisiones = db.query(Revision).all()
    total_tokens = 0
    costo_total = 0.0
    for r in revisiones:
        try:
            total_tokens += (getattr(r, 'tokens_input', 0) or 0) + (getattr(r, 'tokens_output', 0) or 0)
            costo_total += getattr(r, 'costo_estimado', 0.0) or 0.0
        except Exception:
            pass

    return {
        "total_usuarios": total_usuarios,
        "total_tareas": total_tareas,
        "total_entregas": total_entregas,
        "total_tokens": total_tokens,
        "costo_total": costo_total,
    }


@router.patch("/usuarios/{user_id}/toggle-status")
def toggle_status(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.delete("/usuarios/{user_id}")
def delete_usuario(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()
    return {"message": "Usuario eliminado"}
