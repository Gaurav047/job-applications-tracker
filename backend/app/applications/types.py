import enum
from dataclasses import dataclass, field
from typing import List


class FieldStatus(str, enum.Enum):
    filled = "filled"
    not_found = "not_found"  # the selector didn't match anything on this company's form
    ambiguous = "ambiguous"  # matched, but with low confidence (e.g. multiple candidates)


@dataclass
class FieldResult:
    # logical name: "name", "email", "phone", "resume_upload", "cover_letter",
    # or "unmapped:<label text>" for a screening question we didn't attempt.
    field: str
    status: FieldStatus
    detail: str = ""


@dataclass
class FillResult:
    ok: bool  # False only on a hard failure (nav error, page crash) — never for a missing field
    fields: List[FieldResult] = field(default_factory=list)
    screenshot_path: str = ""
    error: str = ""


class UnsupportedAtsError(ValueError):
    """Raised when there's no ApplyDriver for a JobPosting.source."""


class ApplyPageNotFoundError(ValueError):
    """Raised when the live apply-page URL can't be derived/reached for a job."""
