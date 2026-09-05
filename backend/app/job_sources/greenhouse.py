"""Greenhouse job-board adapter.

Greenhouse exposes a public, unauthenticated read API for job boards:
GET https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}?content=true

Job posting URLs look like:
  https://boards.greenhouse.io/{company}/jobs/{job_id}
  https://job-boards.greenhouse.io/{company}/jobs/{job_id}
"""
import re

import httpx

from app.job_sources.html_text import html_to_text
from app.job_sources.types import FetchedJob, JobNotFoundError

SOURCE = "greenhouse"

_URL_RE = re.compile(
    r"^https?://(?:boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)"
)


def matches(url: str) -> bool:
    return bool(_URL_RE.match(url))


def fetch(url: str, client: httpx.Client) -> FetchedJob:
    match = _URL_RE.match(url)
    if not match:
        raise ValueError(f"URL is not a Greenhouse job posting: {url}")
    company_token, job_id = match.groups()

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs/{job_id}?content=true"
    response = client.get(api_url)
    if response.status_code == 404:
        raise JobNotFoundError(f"Greenhouse job not found: {url}")
    response.raise_for_status()
    payload = response.json()

    return FetchedJob(
        source=SOURCE,
        url=url,
        company=payload.get("company_name") or company_token,
        title=payload.get("title", ""),
        description_text=html_to_text(payload.get("content", "")),
        raw_payload=payload,
    )
