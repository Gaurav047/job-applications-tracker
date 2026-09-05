from types import SimpleNamespace

from app.resume_parser.parse import structure_resume_text
from app.resume_parser.schema import JsonResume


class FakeAnthropicClient:
    """Stands in for anthropic.Anthropic in tests so no real API call is made."""

    def __init__(self, tool_input):
        self._tool_input = tool_input
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        tool_use_block = SimpleNamespace(type="tool_use", input=self._tool_input)
        return SimpleNamespace(content=[tool_use_block])


def test_structure_resume_text_returns_json_resume():
    fake_input = {
        "basics": {"name": "Jane Doe", "email": "jane@example.com"},
        "work": [{"name": "Acme Corp", "position": "Engineer", "highlights": ["Built things"]}],
    }
    client = FakeAnthropicClient(fake_input)

    result = structure_resume_text("Jane Doe\nEngineer at Acme Corp\nBuilt things", client=client)

    assert isinstance(result, JsonResume)
    assert result.basics.name == "Jane Doe"
    assert result.work[0].name == "Acme Corp"
    assert result.work[0].highlights == ["Built things"]


def test_structure_resume_text_defaults_missing_fields():
    client = FakeAnthropicClient({"basics": {"name": "No Details"}})

    result = structure_resume_text("No Details", client=client)

    assert result.basics.name == "No Details"
    assert result.work == []
    assert result.skills == []
