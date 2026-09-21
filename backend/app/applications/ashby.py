"""Ashby apply-form automation.

Unlike Greenhouse, Ashby's apply form does NOT live on the same page as the
job description (https://jobs.ashbyhq.com/{board}/{id}) — it's a separate
route at .../application, reached in the real UI by clicking an "Apply"
link. Confirmed directly navigable without needing that click-through.

The form itself is a heavily componentized React form with
generated/unstable DOM ids, so fields are located by their visible <label>
text rather than guessed selectors. The resume upload is a
drag-and-drop-styled control backed by a hidden `input[type=file]`.

The application tab also fetches its form fields asynchronously after the
page's `load` event fires (it shows "Fetching application form" first) —
confirmed against a real live posting, where filling immediately after
`page.goto(..., wait_until="load")` found nothing at all. `fill()` below
waits for a `label` to actually appear first; if the form never loads within
that window, every field degrades to `not_found` as usual rather than
raising.
"""
import re

from playwright.sync_api import Page

from app.applications.fill_helpers import (
    detect_unmapped_fields,
    first_success,
    try_fill_label,
    try_upload_selector,
)
from app.applications.types import ApplyPageNotFoundError, FillResult
from app.resume_parser.schema import JsonResume

SOURCE = "ashby"

_URL_RE = re.compile(r"^https?://jobs\.ashbyhq\.com/([^/]+)/([^/?#]+)")

_HANDLED_KEYWORDS = ["name", "email", "phone", "resume", "cv"]


class AshbyApplyDriver:
    SOURCE = SOURCE

    def apply_url(self, job_url: str) -> str:
        if not _URL_RE.match(job_url):
            raise ApplyPageNotFoundError(f"Not an Ashby job URL: {job_url}")
        base = job_url.split("?")[0].rstrip("/")
        return base if base.endswith("/application") else base + "/application"

    def fill(self, page: Page, resume: JsonResume, cover_letter: str, resume_pdf_path: str) -> FillResult:
        try:
            page.wait_for_selector("label", timeout=5000)
        except Exception:
            pass  # form never loaded — every lookup below will report not_found

        fields = [
            first_success(
                [
                    lambda: try_fill_label(page, "Full Name", resume.basics.name, "name"),
                    lambda: try_fill_label(page, "Name", resume.basics.name, "name"),
                ],
                "name",
            ),
            try_fill_label(page, "Email", resume.basics.email, "email"),
            try_fill_label(page, "Phone", resume.basics.phone, "phone"),
            first_success(
                [
                    lambda: try_upload_selector(page, "input[type=file]", resume_pdf_path, "resume_upload"),
                ],
                "resume_upload",
            ),
            first_success(
                [
                    lambda: try_fill_label(page, "Cover Letter", cover_letter, "cover_letter"),
                ],
                "cover_letter",
            ),
        ]
        fields.extend(detect_unmapped_fields(page, _HANDLED_KEYWORDS))
        return FillResult(ok=True, fields=fields)

    def submit(self, page: Page) -> None:
        page.get_by_role("button", name=re.compile("submit", re.I)).first.click(timeout=5000)
