from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import verify_password, hash_password, create_access_token, decode_access_token
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, RegisterRequest, RegisterResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        user_id = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")

    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    print(f"[DEBUG /auth/me] id={current_user.id} email={current_user.email} role={current_user.role} is_active={current_user.is_active}")
    return current_user


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if body.password != body.confirmar_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las contraseñas no coinciden")

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este correo ya está registrado")

    user = User(
        nombre=body.nombre,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return RegisterResponse(access_token=token, usuario=UsuarioOut.model_validate(user))


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")
    return current_user


@router.get("/mis-stats")
def get_mis_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.db.models.grupo import Grupo
    from app.db.models.tarea import Tarea
    from app.db.models.entrega import Entrega
    from app.db.models.revision import Revision

    grupos = db.query(Grupo).filter(Grupo.user_id == current_user.id).all()
    grupo_ids = [g.id for g in grupos]

    tareas = db.query(Tarea).filter(Tarea.grupo_id.in_(grupo_ids)).all() if grupo_ids else []
    tarea_ids = [t.id for t in tareas]

    entregas = db.query(Entrega).filter(Entrega.tarea_id.in_(tarea_ids)).all() if tarea_ids else []
    entrega_ids = [e.id for e in entregas]

    total_tareas = len(tareas)
    total_entregas = len(entregas)

    try:
        revisiones = db.query(Revision).filter(Revision.entrega_id.in_(entrega_ids)).all() if entrega_ids else []
        tokens_consumidos = sum((getattr(r, 'tokens_input', 0) or 0) + (getattr(r, 'tokens_output', 0) or 0) for r in revisiones)
        costo_estimado = sum(getattr(r, 'costo_estimado', 0.0) or 0.0 for r in revisiones)
    except Exception:
        tokens_consumidos = 0
        costo_estimado = 0.0

    return {
        "total_tareas": total_tareas,
        "total_entregas": total_entregas,
        "tokens_consumidos": tokens_consumidos,
        "costo_estimado": costo_estimado,
    }
