"""RAG-augmented resume tailoring.

Same contract as backend's app.tailoring.tailor.tailor_resume (same call
signature plus a master_resume_id, same TailoringOutput return, same
fabrication guard), but first (re-)ingests the master resume's bullets so
retrieval always reflects its current content, then retrieves the
candidate's most relevant past bullets (across resume history) and
phrasing/keywords from similar real job postings, and folds both into the
prompt as context Claude may use to prioritize and phrase — never as facts
it's allowed to add.
"""
from sqlalchemy.orm import Session

from rag import _pathlink  # noqa: F401
from app.core.llm import MODEL, get_anthropic_client
from app.resume_parser.schema import JsonResume
from app.tailoring.schema import TailoringOutput
from app.tailoring.tailor import SYSTEM_PROMPT, TAILOR_TOOL
from app.tailoring.validate import assert_no_fabrication
from rag.ingest import ingest_master_resume
from rag.retriever import retrieve_relevant_bullets, retrieve_similar_job_examples


def tailor_resume_rag(
    db: Session,
    master: JsonResume,
    master_resume_id: str,
    job_description: str,
    client=None,
) -> TailoringOutput:
    client = client or get_anthropic_client()

    ingest_master_resume(db, master_resume_id, master)

    relevant_bullets = retrieve_relevant_bullets(
        db, job_description, master_resume_id=master_resume_id, top_k=8
    )
    similar_examples = retrieve_similar_job_examples(db, job_description, top_k=4)

    context_parts = []
    if relevant_bullets:
        lines = "\n".join(f"- ({b.context}) {b.text}" for b in relevant_bullets)
        context_parts.append(
            f"Most relevant bullets from the candidate's resume history:\n{lines}"
        )
    if similar_examples:
        lines = "\n".join(f"- [{e.title}] {e.text}" for e in similar_examples)
        context_parts.append(
            "Phrasing/keywords from similar real job postings (for terminology "
            f"only, never a source of facts about the candidate):\n{lines}"
        )

    user_message = (
        f"Candidate's master resume (JSON):\n{master.model_dump_json()}\n\n"
        f"Job posting description:\n{job_description}"
    )
    if context_parts:
        retrieved_context = "\n\n".join(context_parts)
        user_message += f"\n\nRetrieved context:\n{retrieved_context}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        tools=[TAILOR_TOOL],
        tool_choice={"type": "tool", "name": "record_tailored_resume"},
        messages=[{"role": "user", "content": user_message}],
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    result = TailoringOutput.model_validate(tool_use.input)
    assert_no_fabrication(master, result.resume)
    return result
