"""Lever apply-form automation.

Lever posting pages (https://jobs.lever.co/{company}/{id}) link to a
separate apply form at the same URL with "/apply" appended. Fields are
typically plain `input[name=...]` (name/email/phone), a custom dropzone for
the resume, and an "Additional Information" textarea used as a stand-in for
a cover letter when the posting has one enabled.
"""
import re

from playwright.sync_api import Page

from app.applications.fill_helpers import (
    detect_unmapped_fields,
    first_success,
    try_fill_label,
    try_fill_selector,
    try_upload_selector,
)
from app.applications.types import ApplyPageNotFoundError, FillResult
from app.resume_parser.schema import JsonResume

SOURCE = "lever"

_URL_RE = re.compile(r"^https?://jobs\.lever\.co/([^/]+)/([^/?#]+)")

_HANDLED_KEYWORDS = ["name", "email", "phone", "resume", "cv", "additional information"]


class LeverApplyDriver:
    SOURCE = SOURCE

    def apply_url(self, job_url: str) -> str:
        if not _URL_RE.match(job_url):
            raise ApplyPageNotFoundError(f"Not a Lever job URL: {job_url}")
        base = job_url.rstrip("/")
        return base if base.endswith("/apply") else base + "/apply"

    def fill(self, page: Page, resume: JsonResume, cover_letter: str, resume_pdf_path: str) -> FillResult:
        fields = [
            try_fill_selector(page, 'input[name="name"]', resume.basics.name, "name"),
            try_fill_selector(page, 'input[name="email"]', resume.basics.email, "email"),
            try_fill_selector(page, 'input[name="phone"]', resume.basics.phone, "phone"),
            first_success(
                [
                    lambda: try_upload_selector(page, 'input[name="resume"]', resume_pdf_path, "resume_upload"),
                    lambda: try_upload_selector(page, "input[type=file]", resume_pdf_path, "resume_upload"),
                ],
                "resume_upload",
            ),
            try_fill_label(page, "Additional Information", cover_letter, "cover_letter"),
        ]
        fields.extend(detect_unmapped_fields(page, _HANDLED_KEYWORDS))
        return FillResult(ok=True, fields=fields)

    def submit(self, page: Page) -> None:
        page.locator('button[type=submit], .postings-btn-submit').first.click(timeout=5000)
