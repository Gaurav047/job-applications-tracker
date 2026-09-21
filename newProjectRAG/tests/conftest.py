import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["RAG_FAKE_EMBEDDINGS"] = "1"

import pytest

from rag import _pathlink  # noqa: F401
from app.core.db import Base, SessionLocal, engine
from app import models  # noqa: F401  registers backend's own models on Base
from rag import models as rag_models  # noqa: F401  registers the RAG models on Base


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
