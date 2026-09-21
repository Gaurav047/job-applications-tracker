"""Dispatches to a per-ATS ApplyDriver by JobPosting.source (same key space
app/job_sources/ already uses) and orchestrates the two-phase fill/submit
flow around it.

Two-phase session handling: Phase 1 (`run_fill`) and Phase 2 (`run_submit`)
are two separate HTTP requests, and a live Playwright browser session can't
be held open across them — there's no long-running browser process or
session-reconnect mechanism here. `run_submit` therefore re-launches a fresh
browser and re-runs the exact same fill immediately before clicking submit,
all within one uninterrupted session. This means the screenshot a user
reviews after Phase 1 is a preview of what *will* be filled, not a literal
live tab carried forward into Phase 2 — an acceptable tradeoff since a
company's form is very unlikely to change in the few minutes between a user
reviewing and confirming.
"""
from app.applications import ashby, greenhouse, lever
from app.applications.browser import new_page
from app.applications.storage import screenshot_path as _screenshot_path
from app.applications.types import FillResult, UnsupportedAtsError
from app.resume_parser.schema import JsonResume

_DRIVERS = {
    greenhouse.SOURCE: greenhouse.GreenhouseApplyDriver(),
    lever.SOURCE: lever.LeverApplyDriver(),
    ashby.SOURCE: ashby.AshbyApplyDriver(),
}

__all__ = ["get_apply_driver", "run_fill", "run_submit", "UnsupportedAtsError", "FillResult"]


def get_apply_driver(source: str):
    driver = _DRIVERS.get(source)
    if driver is None:
        raise UnsupportedAtsError(f"No apply driver for source: {source}")
    return driver


def run_fill(
    source: str,
    job_url: str,
    resume: JsonResume,
    cover_letter: str,
    resume_pdf_path: str,
    user_id: str,
    application_id: str,
) -> FillResult:
    """Phase 1: fills the real application form and stops — never clicks
    submit. Always returns a FillResult (never raises); a hard failure
    (navigation error, unrecognizable page) comes back as ok=False."""
    try:
        driver = get_apply_driver(source)
        with new_page() as page:
            page.goto(driver.apply_url(job_url), wait_until="load")
            result = driver.fill(page, resume, cover_letter, resume_pdf_path)
            path = _screenshot_path(user_id, application_id)
            page.screenshot(path=path, full_page=True)
            result.screenshot_path = path
            return result
    except Exception as exc:
        return FillResult(ok=False, error=str(exc))


def run_submit(
    source: str,
    job_url: str,
    resume: JsonResume,
    cover_letter: str,
    resume_pdf_path: str,
) -> None:
    """Phase 2: re-fills, then clicks the real submit control, in one fresh
    session. Raises on any failure — the caller (POST
    /applications/{id}/confirm) must catch this and keep the application in
    pending_review rather than marking it submitted."""
    driver = get_apply_driver(source)
    with new_page() as page:
        page.goto(driver.apply_url(job_url), wait_until="load")
        driver.fill(page, resume, cover_letter, resume_pdf_path)
        driver.submit(page)
