from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth
from app.api import grupos
from app.api import alumnos
from app.api import tareas
from app.api import entregas
from app.api import revision

app = FastAPI(title="GradeAI API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(grupos.router)
app.include_router(alumnos.router)
app.include_router(tareas.router)
app.include_router(entregas.router)
app.include_router(revision.router)


@app.get("/health")
def health():
    return {"status": "ok"}
