"""Turns a raw resume file into a JsonResume. Layout varies too much across
real resumes for a rules-based parser to be reliable, so we extract raw text
per file type and then ask Claude to structure it — with an explicit
instruction to transcribe faithfully rather than invent or embellish content,
since this structured resume becomes the ground truth the tailoring step is
allowed to draw from.
"""
import json

from app.core.llm import MODEL, get_anthropic_client
from app.resume_parser.extract_text import extract_text
from app.resume_parser.schema import JsonResume

STRUCTURE_TOOL = {
    "name": "record_resume",
    "description": "Record the resume content structured as JSON Resume fields.",
    "input_schema": JsonResume.model_json_schema(),
}

SYSTEM_PROMPT = (
    "You transcribe resumes into structured data. Extract only what is "
    "explicitly present in the source text. Do not invent, infer, embellish, "
    "or add any employer, title, date, skill, or accomplishment that is not "
    "stated in the text. If a field is not present, leave it empty."
)


def parse_resume_file(file_path: str, client=None) -> JsonResume:
    raw_text = extract_text(file_path)
    return structure_resume_text(raw_text, client=client)


def structure_resume_text(raw_text: str, client=None) -> JsonResume:
    client = client or get_anthropic_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[STRUCTURE_TOOL],
        tool_choice={"type": "tool", "name": "record_resume"},
        messages=[{"role": "user", "content": raw_text}],
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return JsonResume.model_validate(tool_use.input)
