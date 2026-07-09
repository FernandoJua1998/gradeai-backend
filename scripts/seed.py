"""Create initial teacher user. Run with: python -m scripts.seed"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import User  # noqa

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

email = sys.argv[1] if len(sys.argv) > 1 else "admin@gradeai.com"
password = sys.argv[2] if len(sys.argv) > 2 else "changeme123"
nombre = sys.argv[3] if len(sys.argv) > 3 else "Administrador"

Base.metadata.create_all(engine)

with Session(engine) as session:
    existing = session.query(User).filter(User.email == email).first()
    if not existing:
        user = User(email=email, password_hash=hash_password(password), nombre=nombre, role="admin")
        session.add(user)
        session.commit()
        print(f"Usuario creado: {email} / {password}")
    else:
        existing.role = "admin"
        session.commit()
        print(f"Usuario admin actualizado con role=admin")
