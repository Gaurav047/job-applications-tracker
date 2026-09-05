import io
from unittest.mock import patch

from tests.test_resume_parser import FakeAnthropicClient


def _signup_and_token(client, email="resume-user@example.com"):
    resp = client.post("/auth/signup", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def test_upload_resume_requires_auth(client):
    resp = client.post("/resumes", files={"file": ("resume.md", b"# Jane Doe", "text/markdown")})
    assert resp.status_code == 401


def test_upload_and_fetch_latest_resume(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.resume_storage_dir", str(tmp_path))
    token = _signup_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    fake_client = FakeAnthropicClient({"basics": {"name": "Jane Doe", "email": "jane@example.com"}})
    with patch("app.resume_parser.parse.get_anthropic_client", return_value=fake_client):
        resp = client.post(
            "/resumes",
            files={"file": ("resume.md", io.BytesIO(b"# Jane Doe\nEmail: jane@example.com"), "text/markdown")},
            headers=headers,
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["version"] == 1
    assert body["content"]["basics"]["name"] == "Jane Doe"

    resp = client.get("/resumes/latest", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["content"]["basics"]["email"] == "jane@example.com"


def test_upload_rejects_unsupported_file_type(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.resume_storage_dir", str(tmp_path))
    token = _signup_and_token(client, email="badfile@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/resumes",
        files={"file": ("resume.exe", io.BytesIO(b"binary"), "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_upload_rejected_file_does_not_consume_quota(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.resume_storage_dir", str(tmp_path))
    token = _signup_and_token(client, email="badfile-quota@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/resumes",
        files={"file": ("resume.exe", io.BytesIO(b"binary"), "application/octet-stream")},
        headers=headers,
    )
    resp = client.get("/billing/status", headers=headers)
    assert resp.json()["usage_count"] == 0


def test_upload_blocked_once_free_tier_limit_reached(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.resume_storage_dir", str(tmp_path))
    token = _signup_and_token(client, email="over-limit@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    fake_client = FakeAnthropicClient({"basics": {"name": "Jane Doe"}})
    with patch("app.resume_parser.parse.get_anthropic_client", return_value=fake_client):
        for _ in range(5):  # free tier monthly_limit == 5
            resp = client.post(
                "/resumes",
                files={"file": ("resume.md", io.BytesIO(b"# Jane Doe"), "text/markdown")},
                headers=headers,
            )
            assert resp.status_code == 201

        resp = client.post(
            "/resumes",
            files={"file": ("resume.md", io.BytesIO(b"# Jane Doe"), "text/markdown")},
            headers=headers,
        )
    assert resp.status_code == 402
