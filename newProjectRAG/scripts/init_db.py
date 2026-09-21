#!/usr/bin/env python3
"""Creates the RAG layer's tables — and the pgvector extension, on
Postgres — in the same database backend/ uses. Run once, after backend's
own .env/DB are set up:

    source ../backend/.venv/bin/activate
    pip install -r requirements.txt
    python scripts/init_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag import _pathlink  # noqa: F401,E402
from app.core.db import Base, engine  # noqa: E402
from app import models  # noqa: F401,E402  registers backend's own tables on Base
from rag import models as rag_models  # noqa: F401,E402  registers the RAG tables on Base


def main():
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=engine)
    print("RAG tables ready.")


if __name__ == "__main__":
    main()
