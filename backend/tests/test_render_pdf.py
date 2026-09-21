from app.resume_parser.schema import Basics, JsonResume, WorkItem
from app.tailoring.render_pdf import render_resume_html, render_tailored_resume_pdf


def _sample_resume() -> JsonResume:
    return JsonResume(
        basics=Basics(name="Jane Doe", email="jane@example.com", phone="555-1234", summary="Engineer."),
        work=[WorkItem(name="Acme", position="Engineer", highlights=["Built things"])],
    )


def test_render_resume_html_includes_key_fields():
    html = render_resume_html(_sample_resume(), "Dear Hiring Team, ...")
    assert "Jane Doe" in html
    assert "jane@example.com" in html
    assert "Acme" in html
    assert "Built things" in html
    assert "Dear Hiring Team" in html


def test_render_resume_html_escapes_content():
    resume = _sample_resume()
    resume.basics.summary = "<script>alert(1)</script>"
    html = render_resume_html(resume, "")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_tailored_resume_pdf_writes_valid_pdf(tmp_path):
    dest = tmp_path / "nested" / "resume.pdf"
    render_tailored_resume_pdf(_sample_resume(), "Dear Hiring Team, ...", str(dest))
    assert dest.exists()
    assert dest.read_bytes()[:4] == b"%PDF"
