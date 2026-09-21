"""Turns a master resume or an example job posting into embedded chunks in
the vector store."""
from sqlalchemy.orm import Session

from rag import _pathlink  # noqa: F401
from app.resume_parser.schema import JsonResume
from rag.embeddings import embed_texts
from rag.models import JobExampleChunk, ResumeBulletChunk


def _resume_bullets(resume: JsonResume) -> list[tuple[str, str, str]]:
    """Returns (section, context, text) triples for every bullet in the resume."""
    bullets = []
    for work in resume.work:
        context = f"{work.position} at {work.name}".strip()
        for highlight in work.highlights:
            bullets.append(("work", context, highlight))
    for project in resume.projects:
        for highlight in project.highlights:
            bullets.append(("project", project.name, highlight))
    return bullets


def ingest_master_resume(db: Session, master_resume_id: str, resume: JsonResume) -> int:
    """Embeds and stores every bullet in `resume`, replacing any chunks
    previously ingested for this master_resume_id. Returns the chunk count."""
    db.query(ResumeBulletChunk).filter(
        ResumeBulletChunk.master_resume_id == master_resume_id
    ).delete()

    bullets = _resume_bullets(resume)
    if not bullets:
        db.commit()
        return 0

    vectors = embed_texts([text for _, _, text in bullets])
    for (section, context, text), vector in zip(bullets, vectors):
        db.add(
            ResumeBulletChunk(
                master_resume_id=master_resume_id,
                section=section,
                context=context,
                text=text,
                embedding=vector,
            )
        )
    db.commit()
    return len(bullets)


def ingest_job_example(db: Session, source: str, title: str, text: str) -> int:
    """Chunks a job posting's description into paragraphs, embeds and
    stores each. Returns the chunk count."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        return 0

    vectors = embed_texts(paragraphs)
    for paragraph, vector in zip(paragraphs, vectors):
        db.add(JobExampleChunk(source=source, title=title, text=paragraph, embedding=vector))
    db.commit()
    return len(paragraphs)
