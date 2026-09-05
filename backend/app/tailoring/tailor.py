from app.core.llm import MODEL, get_anthropic_client
from app.resume_parser.schema import JsonResume
from app.tailoring.schema import TailoringOutput
from app.tailoring.validate import assert_no_fabrication

TAILOR_TOOL = {
    "name": "record_tailored_resume",
    "description": "Record the tailored resume and cover letter.",
    "input_schema": TailoringOutput.model_json_schema(),
}

SYSTEM_PROMPT = (
    "You tailor resumes to a specific job posting. You may reorder sections, "
    "reorder or rephrase bullet points, and rewrite the professional summary "
    "to emphasize experience relevant to the job description, using the "
    "job posting's own terminology where it genuinely matches the candidate's "
    "real experience. You must NOT invent, add, or imply any employer, job "
    "title, dates, degree, institution, project, skill, or accomplishment "
    "that is not already present in the candidate's resume. Every employer, "
    "job title, and institution in your output must appear, unchanged, "
    "somewhere in the input resume. Do not change the candidate's name, "
    "email, or phone number. Also write a concise, professional cover "
    "letter grounded only in the candidate's real experience from the "
    "resume, addressed to the hiring team for this role."
)


def tailor_resume(master: JsonResume, job_description: str, client=None) -> TailoringOutput:
    client = client or get_anthropic_client()
    user_message = (
        f"Candidate's master resume (JSON):\n{master.model_dump_json()}\n\n"
        f"Job posting description:\n{job_description}"
    )
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
