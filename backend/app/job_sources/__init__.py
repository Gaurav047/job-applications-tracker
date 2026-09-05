from functools import lru_cache

import httpx

from app.job_sources import ashby, greenhouse, lever
from app.job_sources.types import FetchedJob, JobNotFoundError, UnsupportedJobBoardError

_ADAPTERS = [greenhouse, lever, ashby]

__all__ = ["FetchedJob", "JobNotFoundError", "UnsupportedJobBoardError", "fetch_job_posting"]


@lru_cache
def _default_client() -> httpx.Client:
    return httpx.Client(timeout=10.0)


def fetch_job_posting(url: str, client: httpx.Client = None) -> FetchedJob:
    client = client or _default_client()
    for adapter in _ADAPTERS:
        if adapter.matches(url):
            return adapter.fetch(url, client)
    raise UnsupportedJobBoardError(
        f"No adapter for URL (supported: Greenhouse, Lever, Ashby): {url}"
    )
