from dataclasses import dataclass


@dataclass
class FetchedJob:
    source: str
    url: str
    company: str
    title: str
    description_text: str
    raw_payload: dict


class UnsupportedJobBoardError(ValueError):
    """Raised when a job URL doesn't match any known job-board adapter."""


class JobNotFoundError(ValueError):
    """Raised when a job-board API can't locate the posting (e.g. it's closed)."""
