"""Renders a tailored resume + cover letter to PDF.

Uses Playwright's own headless Chromium to print HTML to PDF instead of
adding a dedicated PDF library — Playwright is already a (previously unused)
dependency, and app/applications/ needs it anyway for apply-form automation,
so this reuses that one browser-automation stack for both.

A fresh sync_playwright() context is opened per call rather than shared
across requests: Playwright's sync API is thread-affine (must start/stop on
the same OS thread), and FastAPI runs each sync `def` endpoint on its own
threadpool worker thread, so a per-call context is the correct usage here,
not a workaround.
"""
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.resume_parser.schema import JsonResume


def render_resume_html(resume: JsonResume, cover_letter: str) -> str:
    basics = resume.basics
    parts = [
        "<html><head><style>",
        "body { font-family: Helvetica, Arial, sans-serif; color: #222; margin: 2em; }",
        "h1 { margin-bottom: 0; } h2 { border-bottom: 1px solid #ccc; margin-top: 1.5em; }",
        ".contact { color: #555; margin-top: 0.2em; }",
        ".entry { margin-bottom: 1em; } .entry-title { font-weight: bold; }",
        ".entry-sub { color: #555; font-style: italic; }",
        "ul { margin-top: 0.3em; } .cover-letter { white-space: pre-wrap; }",
        "</style></head><body>",
        f"<h1>{escape(basics.name)}</h1>",
        f"<div class='contact'>{escape(basics.email)} &middot; {escape(basics.phone)}</div>",
    ]
    if basics.summary:
        parts.append(f"<p>{escape(basics.summary)}</p>")

    if resume.work:
        parts.append("<h2>Experience</h2>")
        for w in resume.work:
            date_range = " - ".join(d for d in [w.startDate, w.endDate] if d)
            parts.append("<div class='entry'>")
            parts.append(
                f"<div class='entry-title'>{escape(w.position)}, {escape(w.name)}</div>"
            )
            if date_range:
                parts.append(f"<div class='entry-sub'>{escape(date_range)}</div>")
            if w.summary:
                parts.append(f"<p>{escape(w.summary)}</p>")
            if w.highlights:
                parts.append("<ul>" + "".join(f"<li>{escape(h)}</li>" for h in w.highlights) + "</ul>")
            parts.append("</div>")

    if resume.education:
        parts.append("<h2>Education</h2>")
        for e in resume.education:
            parts.append("<div class='entry'>")
            parts.append(f"<div class='entry-title'>{escape(e.studyType)}, {escape(e.institution)}</div>")
            if e.area:
                parts.append(f"<div class='entry-sub'>{escape(e.area)}</div>")
            parts.append("</div>")

    if resume.skills:
        parts.append("<h2>Skills</h2>")
        parts.append("<p>" + ", ".join(escape(s.name) for s in resume.skills if s.name) + "</p>")

    if resume.projects:
        parts.append("<h2>Projects</h2>")
        for proj in resume.projects:
            parts.append("<div class='entry'>")
            parts.append(f"<div class='entry-title'>{escape(proj.name)}</div>")
            if proj.description:
                parts.append(f"<p>{escape(proj.description)}</p>")
            if proj.highlights:
                parts.append(
                    "<ul>" + "".join(f"<li>{escape(h)}</li>" for h in proj.highlights) + "</ul>"
                )
            parts.append("</div>")

    if cover_letter:
        parts.append("<h2>Cover Letter</h2>")
        parts.append(f"<div class='cover-letter'>{escape(cover_letter)}</div>")

    parts.append("</body></html>")
    return "".join(parts)


def render_tailored_resume_pdf(resume: JsonResume, cover_letter: str, dest_path: str) -> None:
    html = render_resume_html(resume, cover_letter)
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(path=dest_path, format="Letter", print_background=True)
        finally:
            browser.close()
