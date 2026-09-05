from pydantic import BaseModel

from app.resume_parser.schema import JsonResume


class TailoringOutput(BaseModel):
    resume: JsonResume
    cover_letter: str
