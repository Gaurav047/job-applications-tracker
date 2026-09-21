from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from app.applications.lever import LeverApplyDriver
from app.applications.types import ApplyPageNotFoundError, FieldStatus
from app.resume_parser.schema import Basics, JsonResume

FIXTURES = Path(__file__).parent / "fixtures" / "applications"


@pytest.fixture()
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        yield pg
        browser.close()


def _resume() -> JsonResume:
    return JsonResume(basics=Basics(name="Jane Doe", email="jane@example.com", phone="555-1234"))


def _by_field(fields, name):
    return next(f for f in fields if f.field == name)


def test_apply_url_appends_apply_and_rejects_others():
    driver = LeverApplyDriver()
    assert driver.apply_url("https://jobs.lever.co/acme/abc123") == "https://jobs.lever.co/acme/abc123/apply"
    with pytest.raises(ApplyPageNotFoundError):
        driver.apply_url("https://example.com/not-lever")


def test_fill_fills_known_fields(page, tmp_path):
    page.goto(f"file://{FIXTURES / 'lever_apply.html'}")
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    driver = LeverApplyDriver()
    result = driver.fill(page, _resume(), "Dear Hiring Team,", str(dummy_pdf))

    assert result.ok is True
    assert _by_field(result.fields, "name").status == FieldStatus.filled
    assert _by_field(result.fields, "email").status == FieldStatus.filled
    assert _by_field(result.fields, "phone").status == FieldStatus.filled
    assert _by_field(result.fields, "resume_upload").status == FieldStatus.filled
    assert _by_field(result.fields, "cover_letter").status == FieldStatus.filled
    assert page.input_value("#name") == "Jane Doe"


def test_fill_degrades_gracefully_when_resume_field_missing(page, tmp_path):
    page.set_content(
        """
        <form>
          <label for="name">Full Name</label>
          <input type="text" id="name" name="name">
          <label for="email">Email</label>
          <input type="email" id="email" name="email">
        </form>
        """
    )
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    driver = LeverApplyDriver()
    result = driver.fill(page, _resume(), "Dear Hiring Team,", str(dummy_pdf))

    assert result.ok is True
    assert _by_field(result.fields, "name").status == FieldStatus.filled
    assert _by_field(result.fields, "phone").status == FieldStatus.not_found
    assert _by_field(result.fields, "resume_upload").status == FieldStatus.not_found
    assert _by_field(result.fields, "cover_letter").status == FieldStatus.not_found


def test_submit_clicks_the_real_button(page):
    page.goto(f"file://{FIXTURES / 'lever_apply.html'}")
    driver = LeverApplyDriver()
    assert page.locator("#submitted").is_visible() is False
    driver.submit(page)
    assert page.locator("#submitted").is_visible() is True
