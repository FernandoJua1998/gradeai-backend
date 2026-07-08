from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import hash_password


def seed():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "admin@gradeai.com").first()
        if not existing:
            user = User(
                email="admin@gradeai.com",
                password_hash=hash_password("gradeai2026"),
                nombre="Administrador",
            )
            db.add(user)
            db.commit()
            print("Usuario creado: admin@gradeai.com / gradeai2026")
        else:
            print("Usuario ya existe")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
