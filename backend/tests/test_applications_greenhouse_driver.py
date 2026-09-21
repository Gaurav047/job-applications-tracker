from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from app.applications.greenhouse import GreenhouseApplyDriver
from app.applications.types import ApplyPageNotFoundError, FieldStatus
from app.resume_parser.schema import Basics, JsonResume

FIXTURES = Path(__file__).parent / "fixtures" / "applications"


@pytest.fixture()
def page(tmp_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        yield pg
        browser.close()


def _resume() -> JsonResume:
    return JsonResume(basics=Basics(name="Jane Doe", email="jane@example.com", phone="555-1234"))


def _by_field(fields, name):
    return next(f for f in fields if f.field == name)


def test_apply_url_rejects_non_greenhouse_urls():
    driver = GreenhouseApplyDriver()
    with pytest.raises(ApplyPageNotFoundError):
        driver.apply_url("https://example.com/not-greenhouse")


def test_fill_fills_known_fields_and_flags_unmapped(page, tmp_path):
    page.goto(f"file://{FIXTURES / 'greenhouse_apply.html'}")
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    driver = GreenhouseApplyDriver()
    result = driver.fill(page, _resume(), "Dear Hiring Team,", str(dummy_pdf))

    assert result.ok is True
    assert _by_field(result.fields, "first_name").status == FieldStatus.filled
    assert _by_field(result.fields, "last_name").status == FieldStatus.filled
    assert _by_field(result.fields, "email").status == FieldStatus.filled
    assert _by_field(result.fields, "phone").status == FieldStatus.filled
    assert _by_field(result.fields, "resume_upload").status == FieldStatus.filled
    assert _by_field(result.fields, "cover_letter").status == FieldStatus.filled
    assert page.input_value("#first_name") == "Jane"
    assert page.input_value("#last_name") == "Doe"

    unmapped = [f for f in result.fields if f.field.startswith("unmapped:")]
    assert any("hear about us" in f.field.lower() for f in unmapped)


def test_fill_degrades_gracefully_on_missing_fields(page, tmp_path):
    page.goto(f"file://{FIXTURES / 'greenhouse_apply_minimal.html'}")
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    driver = GreenhouseApplyDriver()
    result = driver.fill(page, _resume(), "Dear Hiring Team,", str(dummy_pdf))

    assert result.ok is True  # missing fields never raise
    assert _by_field(result.fields, "first_name").status == FieldStatus.filled
    assert _by_field(result.fields, "phone").status == FieldStatus.not_found
    assert _by_field(result.fields, "resume_upload").status == FieldStatus.not_found
    assert _by_field(result.fields, "cover_letter").status == FieldStatus.not_found


def test_submit_clicks_the_real_button(page):
    page.goto(f"file://{FIXTURES / 'greenhouse_apply.html'}")
    driver = GreenhouseApplyDriver()
    assert page.locator("#submitted").is_visible() is False
    driver.submit(page)
    assert page.locator("#submitted").is_visible() is True
