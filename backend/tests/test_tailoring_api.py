import io
from unittest.mock import patch

from app.resume_parser.schema import Basics, JsonResume, WorkItem
from app.tailoring.schema import TailoringOutput
from tests.test_resume_parser import FakeAnthropicClient


def _signup_and_headers(client, email="tailor-user@example.com"):
    resp = client.post("/auth/signup", json={"email": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _upload_master_resume(client, headers, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.resume_storage_dir", str(tmp_path))
    fake_client = FakeAnthropicClient(
        {"basics": {"name": "Jane Doe", "email": "jane@example.com"}, "work": [{"name": "Acme", "position": "Engineer"}]}
    )
    with patch("app.resume_parser.parse.get_anthropic_client", return_value=fake_client):
        client.post(
            "/resumes",
            files={"file": ("resume.md", io.BytesIO(b"# Jane Doe"), "text/markdown")},
            headers=headers,
        )


def _add_job(client, headers):
    from app.job_sources.types import FetchedJob

    fetched = FetchedJob(
        source="greenhouse",
        url="https://boards.greenhouse.io/acme/jobs/1",
        company="Acme",
        title="Engineer",
        description_text="We need an engineer.",
        raw_payload={},
    )
    with patch("app.api.jobs.fetch_job_posting", return_value=fetched):
        resp = client.post("/jobs", json={"url": "https://boards.greenhouse.io/acme/jobs/1"}, headers=headers)
    return resp.json()["id"]


def _fake_tailoring_result() -> TailoringOutput:
    return TailoringOutput(
        resume=JsonResume(
            basics=Basics(name="Jane Doe", email="jane@example.com", summary="Tailored summary"),
            work=[WorkItem(name="Acme", position="Engineer", highlights=["Tailored highlight"])],
        ),
        cover_letter="Dear Hiring Team, ...",
    )


def test_create_tailored_resume_requires_master_resume(client):
    headers = _signup_and_headers(client)
    job_id = _add_job(client, headers)
    resp = client.post("/tailoring", json={"job_posting_id": job_id}, headers=headers)
    assert resp.status_code == 404


def test_create_tailored_resume_requires_valid_job(client, tmp_path, monkeypatch):
    headers = _signup_and_headers(client, email="no-job@example.com")
    _upload_master_resume(client, headers, tmp_path, monkeypatch)
    resp = client.post("/tailoring", json={"job_posting_id": "does-not-exist"}, headers=headers)
    assert resp.status_code == 404


def test_create_and_fetch_tailored_resume(client, tmp_path, monkeypatch):
    headers = _signup_and_headers(client, email="happy-path@example.com")
    _upload_master_resume(client, headers, tmp_path, monkeypatch)
    job_id = _add_job(client, headers)

    with patch("app.api.tailoring.tailor_resume", return_value=_fake_tailoring_result()):
        resp = client.post("/tailoring", json={"job_posting_id": job_id}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["content"]["basics"]["summary"] == "Tailored summary"
    assert body["cover_letter"] == "Dear Hiring Team, ..."
    assert "diff" in body

    tailored_id = body["id"]

    list_resp = client.get("/tailoring", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = client.get(f"/tailoring/{tailored_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == tailored_id


def test_create_tailored_resume_with_rag(client, tmp_path, monkeypatch):
    headers = _signup_and_headers(client, email="rag-user@example.com")
    _upload_master_resume(client, headers, tmp_path, monkeypatch)
    job_id = _add_job(client, headers)

    with patch("app.api.tailoring.tailor_resume_rag", return_value=_fake_tailoring_result()) as mock_rag, \
        patch("app.api.tailoring.tailor_resume") as mock_plain:
        resp = client.post(
            "/tailoring", json={"job_posting_id": job_id, "use_rag": True}, headers=headers
        )
    assert resp.status_code == 201
    assert resp.json()["content"]["basics"]["summary"] == "Tailored summary"
    mock_rag.assert_called_once()
    mock_plain.assert_not_called()


def test_tailored_resume_not_visible_to_other_users(client, tmp_path, monkeypatch):
    headers_a = _signup_and_headers(client, email="user-a@example.com")
    _upload_master_resume(client, headers_a, tmp_path, monkeypatch)
    job_id = _add_job(client, headers_a)
    with patch("app.api.tailoring.tailor_resume", return_value=_fake_tailoring_result()):
        resp = client.post("/tailoring", json={"job_posting_id": job_id}, headers=headers_a)
    tailored_id = resp.json()["id"]

    headers_b = _signup_and_headers(client, email="user-b@example.com")
    get_resp = client.get(f"/tailoring/{tailored_id}", headers=headers_b)
    assert get_resp.status_code == 404


def test_tailoring_counts_against_usage_quota(client, tmp_path, monkeypatch):
    headers = _signup_and_headers(client, email="quota@example.com")
    _upload_master_resume(client, headers, tmp_path, monkeypatch)  # already used 1 unit
    job_id = _add_job(client, headers)

    with patch("app.api.tailoring.tailor_resume", return_value=_fake_tailoring_result()):
        client.post("/tailoring", json={"job_posting_id": job_id}, headers=headers)

    status_resp = client.get("/billing/status", headers=headers)
    assert status_resp.json()["usage_count"] == 2
