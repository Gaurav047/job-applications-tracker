"""Playwright lifecycle helper.

Every endpoint in this codebase is a sync `def`, which FastAPI runs on
Starlette's per-request threadpool — a fresh worker thread per request.
Playwright's sync API must be started and torn down on that same thread and
must not be shared/reused across threads or requests, so a new
sync_playwright() context is opened here on every call rather than once at
app startup. Never cache or share a Playwright/Browser instance across
requests.
"""
from contextlib import contextmanager

from playwright.sync_api import sync_playwright


@contextmanager
def new_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            yield browser.new_page()
        finally:
            browser.close()
