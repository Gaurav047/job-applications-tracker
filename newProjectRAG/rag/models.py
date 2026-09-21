"""SQLAlchemy models for the RAG layer.

These are registered on the *backend's own* `Base`, so they live in the
same database/metadata as `master_resumes`, `job_postings`, etc. Run
scripts/init_db.py once to create these two tables alongside the existing
ones (and enable the pgvector extension, on Postgres).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from rag import _pathlink  # noqa: F401
from app.core.db import Base, engine
from rag.embeddings import EMBEDDING_DIM

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pgvector package not installed (e.g. sqlite-only dev)
    Vector = None


def _embedding_type():
    """pgvector's Vector type on Postgres, so similarity search runs in the
    database; a plain JSON float array on sqlite (used in tests, which have
    no pgvector extension), where retriever.py falls back to ranking in
    Python."""
    if Vector is not None and engine.dialect.name == "postgresql":
        return Vector(EMBEDDING_DIM)
    return JSON


class ResumeBulletChunk(Base):
    """One bullet from one version of a user's master resume, embedded for
    retrieval. Re-ingesting a resume replaces its chunks (see rag.ingest)."""

    __tablename__ = "resume_bullet_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    master_resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("master_resumes.id"), nullable=False)
    section: Mapped[str] = mapped_column(String(32), nullable=False)  # "work" | "project"
    context: Mapped[str] = mapped_column(String(256), nullable=False)  # company/position or project name
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(_embedding_type(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class JobExampleChunk(Base):
    """A chunk of an example job posting — not necessarily one the user is
    applying to — used to retrieve realistic role phrasing/keywords that
    tailoring can borrow terminology from."""

    __tablename__ = "job_example_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(_embedding_type(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
