from app.resume_parser.schema import JsonResume, WorkItem
from rag.ingest import ingest_job_example, ingest_master_resume
from rag.retriever import retrieve_relevant_bullets, retrieve_similar_job_examples


def _resume_with_bullets(*highlights_by_work):
    work_items = [
        WorkItem(name=f"Company {i}", position=f"Engineer {i}", highlights=list(highlights))
        for i, highlights in enumerate(highlights_by_work)
    ]
    return JsonResume(work=work_items)


def test_ingest_and_retrieve_bullets(db_session):
    resume = _resume_with_bullets(
        ["Built a distributed caching layer that cut API latency by 40 percent"],
        ["Led quarterly performance reviews for a team of five designers"],
    )
    ingest_master_resume(db_session, "resume-1", resume)

    results = retrieve_relevant_bullets(
        db_session, "distributed caching latency", master_resume_id="resume-1", top_k=1
    )

    assert len(results) == 1
    assert "caching" in results[0].text


def test_reingest_replaces_chunks(db_session):
    resume_a = _resume_with_bullets(["Shipped feature A"])
    resume_b = _resume_with_bullets(["Shipped feature A", "Shipped feature B"])

    ingest_master_resume(db_session, "resume-1", resume_a)
    count = ingest_master_resume(db_session, "resume-1", resume_b)

    assert count == 2
    all_bullets = retrieve_relevant_bullets(db_session, "feature", master_resume_id="resume-1", top_k=10)
    assert len(all_bullets) == 2


def test_ingest_and_retrieve_job_examples(db_session):
    ingest_job_example(
        db_session,
        source="test",
        title="Backend Engineer",
        text=(
            "We need someone strong in PostgreSQL and distributed systems.\n"
            "Bonus: Kubernetes experience."
        ),
    )

    results = retrieve_similar_job_examples(db_session, "distributed systems PostgreSQL", top_k=1)

    assert len(results) == 1
    assert "PostgreSQL" in results[0].text
