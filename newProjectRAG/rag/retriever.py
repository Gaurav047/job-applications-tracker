"""Similarity search over resume bullets and job posting examples.

On Postgres this pushes the search into pgvector (cosine distance via its
SQLAlchemy comparator). On sqlite — tests, or local dev without the
pgvector extension — it falls back to pulling all rows and ranking them in
Python, which is fine at prototype scale but not meant to scale past a few
thousand rows.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from rag import _pathlink  # noqa: F401
from app.core.db import engine
from rag.embeddings import embed_query
from rag.models import JobExampleChunk, ResumeBulletChunk


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


def retrieve_relevant_bullets(
    db: Session, query_text: str, master_resume_id: Optional[str] = None, top_k: int = 8
) -> list[ResumeBulletChunk]:
    query_vector = embed_query(query_text)
    stmt = select(ResumeBulletChunk)
    if master_resume_id is not None:
        stmt = stmt.where(ResumeBulletChunk.master_resume_id == master_resume_id)

    if _is_postgres():
        stmt = stmt.order_by(ResumeBulletChunk.embedding.cosine_distance(query_vector)).limit(top_k)
        return list(db.scalars(stmt))

    rows = list(db.scalars(stmt))
    rows.sort(key=lambda r: _cosine_similarity(r.embedding, query_vector), reverse=True)
    return rows[:top_k]


def retrieve_similar_job_examples(db: Session, query_text: str, top_k: int = 4) -> list[JobExampleChunk]:
    query_vector = embed_query(query_text)
    stmt = select(JobExampleChunk)

    if _is_postgres():
        stmt = stmt.order_by(JobExampleChunk.embedding.cosine_distance(query_vector)).limit(top_k)
        return list(db.scalars(stmt))

    rows = list(db.scalars(stmt))
    rows.sort(key=lambda r: _cosine_similarity(r.embedding, query_vector), reverse=True)
    return rows[:top_k]
