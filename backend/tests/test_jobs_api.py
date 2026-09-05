from unittest.mock import patch

from app.job_sources.types import FetchedJob, UnsupportedJobBoardError


def _auth_headers(client, email="jobs-user@example.com"):
    resp = client.post("/auth/signup", json={"email": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_add_job_requires_auth(client):
    resp = client.post("/jobs", json={"url": "https://boards.greenhouse.io/acme/jobs/1"})
    assert resp.status_code == 401


def test_add_job_success(client):
    headers = _auth_headers(client)
    fetched = FetchedJob(
        source="greenhouse",
        url="https://boards.greenhouse.io/acme/jobs/1",
        company="Acme Corp",
        title="Engineer",
        description_text="Build things.",
        raw_payload={"title": "Engineer"},
    )
    with patch("app.api.jobs.fetch_job_posting", return_value=fetched):
        resp = client.post(
            "/jobs", json={"url": "https://boards.greenhouse.io/acme/jobs/1"}, headers=headers
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["company"] == "Acme Corp"
    assert body["title"] == "Engineer"

    resp = client.get("/jobs", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_add_job_unsupported_board_returns_400(client):
    headers = _auth_headers(client, email="jobs-user2@example.com")
    with patch("app.api.jobs.fetch_job_posting", side_effect=UnsupportedJobBoardError("nope")):
        resp = client.post("/jobs", json={"url": "https://example.com/job/1"}, headers=headers)
    assert resp.status_code == 400
