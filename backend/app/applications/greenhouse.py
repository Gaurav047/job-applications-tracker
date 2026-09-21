"""Greenhouse apply-form automation.

Greenhouse's hosted job page (the same URL app/job_sources/greenhouse.py
scrapes the description from) renders its "Apply" form directly below the
description on that same page — there's no separate apply URL to derive.
Common field ids on the hosted template: #first_name, #last_name, #email,
#phone, a resume dropzone, and #cover_letter when a posting enables it. Real
postings customize this per company (extra screening questions, renamed
fields), so every lookup degrades to `not_found` rather than raising — see
app/applications/fill_helpers.py.
"""
import re

from playwright.sync_api import Page

from app.applications.fill_helpers import (
    detect_unmapped_fields,
    first_success,
    try_fill_selector,
    try_upload_selector,
)
from app.applications.types import ApplyPageNotFoundError, FillResult
from app.resume_parser.schema import JsonResume

SOURCE = "greenhouse"

_URL_RE = re.compile(r"^https?://(?:boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)")

_HANDLED_KEYWORDS = ["first name", "last name", "name", "email", "phone", "resume", "cv", "cover letter"]


class GreenhouseApplyDriver:
    SOURCE = SOURCE

    def apply_url(self, job_url: str) -> str:
        if not _URL_RE.match(job_url):
            raise ApplyPageNotFoundError(f"Not a Greenhouse job URL: {job_url}")
        return job_url

    def fill(self, page: Page, resume: JsonResume, cover_letter: str, resume_pdf_path: str) -> FillResult:
        name_parts = resume.basics.name.split(None, 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        fields = [
            try_fill_selector(page, "#first_name", first_name, "first_name"),
            try_fill_selector(page, "#last_name", last_name, "last_name"),
            try_fill_selector(page, "#email", resume.basics.email, "email"),
            try_fill_selector(page, "#phone", resume.basics.phone, "phone"),
            first_success(
                [
                    lambda: try_upload_selector(page, "#resume", resume_pdf_path, "resume_upload"),
                    lambda: try_upload_selector(page, "input[type=file]", resume_pdf_path, "resume_upload"),
                ],
                "resume_upload",
            ),
            try_fill_selector(page, "#cover_letter", cover_letter, "cover_letter"),
        ]
        fields.extend(detect_unmapped_fields(page, _HANDLED_KEYWORDS))
        return FillResult(ok=True, fields=fields)

    def submit(self, page: Page) -> None:
        page.locator("#submit_app, button[type=submit]").first.click(timeout=5000)
