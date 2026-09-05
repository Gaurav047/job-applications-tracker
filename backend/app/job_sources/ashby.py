"""Ashby job-board adapter.

Ashby exposes a public, unauthenticated read API that lists every open
posting for a board (there's no single-job-by-id endpoint):
GET https://api.ashbyhq.com/posting-api/job-board/{board_name}

Job posting URLs look like:
  https://jobs.ashbyhq.com/{board_name}/{job_id}
"""
import re

import httpx

from app.job_sources.html_text import html_to_text
from app.job_sources.types import FetchedJob, JobNotFoundError

SOURCE = "ashby"

_URL_RE = re.compile(r"^https?://jobs\.ashbyhq\.com/([^/]+)/([^/?#]+)")


def matches(url: str) -> bool:
    return bool(_URL_RE.match(url))


def fetch(url: str, client: httpx.Client) -> FetchedJob:
    match = _URL_RE.match(url)
    if not match:
        raise ValueError(f"URL is not an Ashby job posting: {url}")
    board_name, job_id = match.groups()

    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"
    response = client.get(api_url)
    if response.status_code == 404:
        raise JobNotFoundError(f"Ashby board not found: {board_name}")
    response.raise_for_status()
    payload = response.json()

    job = next((j for j in payload.get("jobs", []) if j.get("id") == job_id), None)
    if job is None:
        raise JobNotFoundError(f"Ashby job not found on board {board_name}: {job_id}")

    return FetchedJob(
        source=SOURCE,
        url=url,
        company=payload.get("organizationName") or board_name,
        title=job.get("title", ""),
        description_text=html_to_text(job.get("descriptionHtml", "")),
        raw_payload=job,
    )
