"""Lever job-board adapter.

Lever exposes a public, unauthenticated read API for job postings:
GET https://api.lever.co/v0/postings/{company}/{posting_id}?mode=json

Job posting URLs look like:
  https://jobs.lever.co/{company}/{posting_id}
"""
import re

import httpx

from app.job_sources.html_text import html_to_text
from app.job_sources.types import FetchedJob, JobNotFoundError

SOURCE = "lever"

_URL_RE = re.compile(r"^https?://jobs\.lever\.co/([^/]+)/([^/?#]+)")


def matches(url: str) -> bool:
    return bool(_URL_RE.match(url))


def fetch(url: str, client: httpx.Client) -> FetchedJob:
    match = _URL_RE.match(url)
    if not match:
        raise ValueError(f"URL is not a Lever job posting: {url}")
    company_token, posting_id = match.groups()

    api_url = f"https://api.lever.co/v0/postings/{company_token}/{posting_id}?mode=json"
    response = client.get(api_url)
    if response.status_code == 404:
        raise JobNotFoundError(f"Lever job not found: {url}")
    response.raise_for_status()
    payload = response.json()

    description_parts = [html_to_text(payload.get("description", ""))]
    for section in payload.get("lists", []):
        description_parts.append(section.get("text", ""))
        description_parts.append(html_to_text(section.get("content", "")))

    return FetchedJob(
        source=SOURCE,
        url=url,
        company=company_token,
        title=payload.get("text", ""),
        description_text="\n".join(part for part in description_parts if part),
        raw_payload=payload,
    )
