import httpx
import pytest

from app.job_sources import ashby, greenhouse, lever
from app.job_sources.types import JobNotFoundError


def _client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_greenhouse_matches_url():
    assert greenhouse.matches("https://boards.greenhouse.io/acme/jobs/12345")
    assert greenhouse.matches("https://job-boards.greenhouse.io/acme/jobs/12345")
    assert not greenhouse.matches("https://jobs.lever.co/acme/abc")


def test_greenhouse_fetch_parses_job():
    def handler(request):
        assert request.url.path == "/v1/boards/acme/jobs/12345"
        return httpx.Response(
            200,
            json={
                "title": "Senior Engineer",
                "company_name": "Acme Corp",
                "content": "<p>Build <b>things</b>.</p>",
            },
        )

    job = greenhouse.fetch("https://boards.greenhouse.io/acme/jobs/12345", _client_for(handler))

    assert job.source == "greenhouse"
    assert job.company == "Acme Corp"
    assert job.title == "Senior Engineer"
    assert "Build" in job.description_text
    assert "things" in job.description_text


def test_greenhouse_fetch_404_raises_job_not_found():
    def handler(request):
        return httpx.Response(404)

    with pytest.raises(JobNotFoundError):
        greenhouse.fetch("https://boards.greenhouse.io/acme/jobs/99999", _client_for(handler))


def test_lever_fetch_parses_job():
    def handler(request):
        assert request.url.path == "/v0/postings/acme/abc-123"
        return httpx.Response(
            200,
            json={
                "text": "Product Manager",
                "description": "<p>Own the roadmap.</p>",
                "lists": [{"text": "Requirements", "content": "<ul><li>5 years exp</li></ul>"}],
            },
        )

    job = lever.fetch("https://jobs.lever.co/acme/abc-123", _client_for(handler))

    assert job.source == "lever"
    assert job.title == "Product Manager"
    assert "Own the roadmap" in job.description_text
    assert "5 years exp" in job.description_text


def test_ashby_fetch_finds_job_by_id_in_board_listing():
    def handler(request):
        assert request.url.path == "/posting-api/job-board/acme"
        return httpx.Response(
            200,
            json={
                "organizationName": "Acme Corp",
                "jobs": [
                    {"id": "job-1", "title": "Designer", "descriptionHtml": "<p>Design stuff.</p>"},
                    {"id": "job-2", "title": "Recruiter", "descriptionHtml": "<p>Hire people.</p>"},
                ],
            },
        )

    job = ashby.fetch("https://jobs.ashbyhq.com/acme/job-2", _client_for(handler))

    assert job.company == "Acme Corp"
    assert job.title == "Recruiter"
    assert "Hire people" in job.description_text


def test_ashby_fetch_missing_job_raises_job_not_found():
    def handler(request):
        return httpx.Response(200, json={"organizationName": "Acme Corp", "jobs": []})

    with pytest.raises(JobNotFoundError):
        ashby.fetch("https://jobs.ashbyhq.com/acme/does-not-exist", _client_for(handler))
