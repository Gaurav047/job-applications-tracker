"""Interface every per-ATS apply automation implements. See app/applications/__init__.py
for the dispatch-by-source pattern (mirrors app/job_sources/) and for why `fill`
and `submit` run in two separate calls rather than one.
"""
from typing import Protocol

from playwright.sync_api import Page

from app.applications.types import FillResult
from app.resume_parser.schema import JsonResume


class ApplyDriver(Protocol):
    SOURCE: str

    def apply_url(self, job_url: str) -> str:
        """Derive the live apply-page URL from the JobPosting.url that was
        used to scrape the job description. Raise ApplyPageNotFoundError if
        it can't be derived."""
        ...

    def fill(
        self,
        page: Page,
        resume: JsonResume,
        cover_letter: str,
        resume_pdf_path: str,
    ) -> FillResult:
        """Navigate `page` to the apply form and fill whatever fields can be
        confidently mapped. MUST NOT click any submit/final button. Must not
        raise on a missing/renamed field on this company's form — record a
        FieldResult(status=not_found) instead. Only navigation-level failures
        (page didn't load, form structure is unrecognizable) should raise, and
        even those are expected to be caught by the caller and turned into
        FillResult(ok=False, error=...)."""
        ...

    def submit(self, page: Page) -> None:
        """Given a `page` already in the filled state (same session, see the
        module docstring in app/applications/__init__.py for why this is a
        fresh re-fill immediately before submit rather than a resumed
        session), click the real submit control. Raises on failure. Called
        ONLY from the confirm-submit endpoint, never from the initial fill."""
        ...
