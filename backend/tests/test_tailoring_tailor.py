import pytest

from app.resume_parser.schema import Basics, JsonResume, WorkItem
from app.tailoring.tailor import tailor_resume
from app.tailoring.validate import FabricationError
from tests.test_resume_parser import FakeAnthropicClient


def _master() -> JsonResume:
    return JsonResume(
        basics=Basics(name="Jane Doe", email="jane@example.com", summary="Backend engineer"),
        work=[WorkItem(name="Acme", position="Engineer", highlights=["Built things"])],
    )


def test_tailor_resume_returns_tailored_output_and_cover_letter():
    master = _master()
    fake_input = {
        "resume": {
            "basics": {"name": "Jane Doe", "email": "jane@example.com", "summary": "Payments-focused backend engineer"},
            "work": [{"name": "Acme", "position": "Engineer", "highlights": ["Built payment systems at scale"]}],
        },
        "cover_letter": "Dear Hiring Team, ...",
    }
    client = FakeAnthropicClient(fake_input)

    result = tailor_resume(master, "We need a payments engineer", client=client)

    assert result.resume.basics.summary == "Payments-focused backend engineer"
    assert result.cover_letter == "Dear Hiring Team, ..."


def test_tailor_resume_raises_on_fabricated_content():
    master = _master()
    fake_input = {
        "resume": {
            "basics": {"name": "Jane Doe", "email": "jane@example.com"},
            "work": [
                {"name": "Acme", "position": "Engineer", "highlights": ["Built things"]},
                {"name": "FakeCorp", "position": "CTO", "highlights": ["Invented everything"]},
            ],
        },
        "cover_letter": "Dear Hiring Team, ...",
    }
    client = FakeAnthropicClient(fake_input)

    with pytest.raises(FabricationError):
        tailor_resume(master, "job description", client=client)
