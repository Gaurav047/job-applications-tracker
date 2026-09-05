from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, billing, jobs, resumes, tailoring
from app.core.db import Base, engine
from app import models  # noqa: F401  ensures models are registered before create_all


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


@app.get("/health")
def health():
    return {"status": "ok"}
