from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import auth, billing, jobs, resumes, tailoring
from app.core.db import Base, engine
from app import models  # noqa: F401  ensures models are registered before create_all

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Job Application Assistant", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(billing.router)
app.include_router(tailoring.router)

# Minimal demo UI for exercising the API flow in a browser — same origin as
# the API itself, so no CORS setup is needed.
app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")


@app.get("/health")
def health():
    return {"status": "ok"}
