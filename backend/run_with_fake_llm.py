"""Runs the app with Claude stubbed out, for local testing without Anthropic
API credits. See README.md's "Testing without Anthropic credits" section.

    source .venv/bin/activate
    python run_with_fake_llm.py

Resume parsing and tailoring will return synthetic-but-plausible data instead
of calling the real API. Everything else (auth, Postgres, Stripe billing,
the Jev fit-score call) behaves exactly as it does with `uvicorn` directly.
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

import uvicorn


def _fake_resume_client():
    def create(**kwargs):
        raw_text = kwargs["messages"][0]["content"]
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        name = lines[0] if lines else "Uploaded Candidate"
        tool_input = {
            "basics": {
                "name": name,
                "email": "candidate@example.com",
                "phone": "555-123-4567",
                "summary": raw_text[:500],
            },
            "work": [
                {
                    "name": "Previous Employer",
                    "position": "Software Engineer",
                    "highlights": ["Worked on the experience described in the uploaded resume."],
                }
            ],
            "skills": [{"name": "Communication"}],
        }
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=tool_input)])

    return SimpleNamespace(messages=SimpleNamespace(create=create))


def _fake_tailoring_client():
    def create(**kwargs):
        user_content = kwargs["messages"][0]["content"]
        master_json = user_content.split("Candidate's master resume (JSON):\n", 1)[1].split(
            "\n\nJob posting description:"
        )[0]
        job_description = user_content.split("Job posting description:\n", 1)[1]
        master = json.loads(master_json)

        tailored = json.loads(json.dumps(master))  # deep copy
        tailored["basics"]["summary"] = (
            f"{master['basics'].get('summary', '')} Tailored for this role.".strip()
        )
        for work in tailored.get("work", []):
            work.setdefault("highlights", []).append(
                f"Relevant to: {job_description[:120]}"
            )

        tool_input = {
            "resume": tailored,
            "cover_letter": (
                f"Dear Hiring Team,\n\nI'm excited to apply for this role. My background "
                f"aligns well with what you're looking for.\n\nSincerely,\n"
                f"{master['basics'].get('name', 'The Candidate')}"
            ),
        }
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=tool_input)])

    return SimpleNamespace(messages=SimpleNamespace(create=create))


if __name__ == "__main__":
    with patch("app.resume_parser.parse.get_anthropic_client", return_value=_fake_resume_client()), \
         patch("app.tailoring.tailor.get_anthropic_client", return_value=_fake_tailoring_client()):
        from app.main import app

        uvicorn.run(app, host="127.0.0.1", port=8000)
