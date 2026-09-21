from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import applications, auth, billing, jobs, resumes, tailoring
from app.core.db import Base, engine
from app import models  # noqa: F401  ensures models are registered before create_all
from rag import models as rag_models  # noqa: F401  registers the RAG tables on Base

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Job Application Assistant", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(billing.router)
app.include_router(tailoring.router)
app.include_router(applications.router)

# Minimal demo UI for exercising the API flow in a browser — same origin as
# the API itself, so no CORS setup is needed.
app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")


@app.get("/health")
def health():
    return {"status": "ok"}
