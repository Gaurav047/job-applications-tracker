from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from app.applications.ashby import AshbyApplyDriver
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


def test_apply_url_appends_application_and_rejects_others():
    driver = AshbyApplyDriver()
    assert (
        driver.apply_url("https://jobs.ashbyhq.com/acme/abc123")
        == "https://jobs.ashbyhq.com/acme/abc123/application"
    )
    with pytest.raises(ApplyPageNotFoundError):
        driver.apply_url("https://example.com/not-ashby")


def test_fill_fills_known_fields_by_label(page, tmp_path):
    page.goto(f"file://{FIXTURES / 'ashby_apply.html'}")
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    driver = AshbyApplyDriver()
    result = driver.fill(page, _resume(), "Dear Hiring Team,", str(dummy_pdf))

    assert result.ok is True
    assert _by_field(result.fields, "name").status == FieldStatus.filled
    assert _by_field(result.fields, "email").status == FieldStatus.filled
    assert _by_field(result.fields, "phone").status == FieldStatus.filled
    assert _by_field(result.fields, "resume_upload").status == FieldStatus.filled
    assert _by_field(result.fields, "cover_letter").status == FieldStatus.filled
    assert page.input_value("#name") == "Jane Doe"


def test_fill_waits_for_labels_that_render_after_a_delay(page, tmp_path):
    # Regression test: a real Ashby posting fetches its application form
    # asynchronously after the page's `load` event fires (it briefly shows
    # "Fetching application form"), so filling immediately after navigation
    # found nothing. This simulates that by injecting the label/input pair
    # slightly after the initial page content loads.
    page.set_content("<div>Fetching application form</div>")
    page.evaluate(
        """
        setTimeout(() => {
          document.body.innerHTML = `
            <label for="name">Full Name</label>
            <input type="text" id="name">
            <label for="email">Email</label>
            <input type="email" id="email">
          `;
        }, 500);
        """
    )
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    driver = AshbyApplyDriver()
    result = driver.fill(page, _resume(), "Dear Hiring Team,", str(dummy_pdf))

    assert _by_field(result.fields, "name").status == FieldStatus.filled
    assert page.input_value("#name") == "Jane Doe"


def test_fill_degrades_gracefully_when_form_never_loads(page, tmp_path):
    page.set_content("<div>Fetching application form</div>")
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    driver = AshbyApplyDriver()
    result = driver.fill(page, _resume(), "Dear Hiring Team,", str(dummy_pdf))

    assert result.ok is True  # a form that never renders still isn't a crash
    assert _by_field(result.fields, "name").status == FieldStatus.not_found


def test_fill_degrades_gracefully_when_labels_missing(page, tmp_path):
    page.set_content(
        """
        <label for="name">Full Name</label>
        <input type="text" id="name">
        <label for="email">Email</label>
        <input type="email" id="email">
        """
    )
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    driver = AshbyApplyDriver()
    result = driver.fill(page, _resume(), "Dear Hiring Team,", str(dummy_pdf))

    assert result.ok is True
    assert _by_field(result.fields, "name").status == FieldStatus.filled
    assert _by_field(result.fields, "phone").status == FieldStatus.not_found
    assert _by_field(result.fields, "resume_upload").status == FieldStatus.not_found
    assert _by_field(result.fields, "cover_letter").status == FieldStatus.not_found


def test_submit_clicks_the_real_button(page):
    page.goto(f"file://{FIXTURES / 'ashby_apply.html'}")
    driver = AshbyApplyDriver()
    assert page.locator("#submitted").is_visible() is False
    driver.submit(page)
    assert page.locator("#submitted").is_visible() is True
