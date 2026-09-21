from types import SimpleNamespace

from app.resume_parser.schema import JsonResume, WorkItem
from app.tailoring.validate import FabricationError
from rag.tailor_rag import tailor_resume_rag


class FakeAnthropicClient:
    """Stands in for anthropic.Anthropic in tests so no real API call is made."""

    def __init__(self, tool_input):
        self._tool_input = tool_input
        self.messages = SimpleNamespace(create=self._create)
        self.last_call = None

    def _create(self, **kwargs):
        self.last_call = kwargs
        tool_use_block = SimpleNamespace(type="tool_use", input=self._tool_input)
        return SimpleNamespace(content=[tool_use_block])


def _master_resume():
    return JsonResume(
        work=[
            WorkItem(
                name="Acme",
                position="Engineer",
                highlights=["Built a distributed caching layer that cut API latency by 40 percent"],
            )
        ]
    )


def test_tailor_resume_rag_ingests_and_retrieves_context(db_session):
    master = _master_resume()
    fake_output = {
        "resume": master.model_dump(),
        "cover_letter": "Dear Hiring Team, ...",
    }
    client = FakeAnthropicClient(fake_output)

    result = tailor_resume_rag(db_session, master, "resume-1", "Looking for distributed caching experience", client=client)

    assert result.cover_letter == "Dear Hiring Team, ..."
    user_message = client.last_call["messages"][0]["content"]
    assert "Retrieved context" in user_message
    assert "caching" in user_message


def test_tailor_resume_rag_still_rejects_fabrication(db_session):
    master = _master_resume()
    fabricated = master.model_dump()
    fabricated["work"].append({"name": "Fake Corp", "position": "CEO", "highlights": []})
    client = FakeAnthropicClient({"resume": fabricated, "cover_letter": "..."})

    try:
        tailor_resume_rag(db_session, master, "resume-1", "job description", client=client)
        assert False, "expected FabricationError"
    except FabricationError:
        pass
