"""Shared, defensive field-filling helpers used by every per-ATS driver.

Every helper here catches its own failures and returns a `not_found`
FieldResult instead of raising — real company apply forms vary in ways no
fixed selector list can fully anticipate, and the whole point of the
two-phase review design is that a missing field shows up in the review
report rather than crashing the fill.
"""
from typing import Callable, List

from playwright.sync_api import Page

from app.applications.types import FieldResult, FieldStatus

_TIMEOUT_MS = 3000


def try_fill_selector(page: Page, selector: str, value: str, field_name: str) -> FieldResult:
    if not value:
        return FieldResult(field=field_name, status=FieldStatus.not_found, detail="no value to fill")
    try:
        locator = page.locator(selector)
        if locator.count() == 0:
            return FieldResult(field=field_name, status=FieldStatus.not_found, detail=f"selector not present: {selector}")
        locator.first.fill(value, timeout=_TIMEOUT_MS)
        return FieldResult(field=field_name, status=FieldStatus.filled, detail=selector)
    except Exception as exc:
        return FieldResult(field=field_name, status=FieldStatus.not_found, detail=str(exc))


def try_fill_label(page: Page, label: str, value: str, field_name: str) -> FieldResult:
    if not value:
        return FieldResult(field=field_name, status=FieldStatus.not_found, detail="no value to fill")
    try:
        locator = page.get_by_label(label, exact=False)
        if locator.count() == 0:
            return FieldResult(field=field_name, status=FieldStatus.not_found, detail=f"label not found: {label}")
        locator.first.fill(value, timeout=_TIMEOUT_MS)
        return FieldResult(field=field_name, status=FieldStatus.filled, detail=label)
    except Exception as exc:
        return FieldResult(field=field_name, status=FieldStatus.not_found, detail=str(exc))


def try_upload_selector(page: Page, selector: str, file_path: str, field_name: str) -> FieldResult:
    try:
        locator = page.locator(selector)
        if locator.count() == 0:
            return FieldResult(field=field_name, status=FieldStatus.not_found, detail=f"selector not present: {selector}")
        locator.first.set_input_files(file_path, timeout=_TIMEOUT_MS)
        return FieldResult(field=field_name, status=FieldStatus.filled, detail=selector)
    except Exception as exc:
        return FieldResult(field=field_name, status=FieldStatus.not_found, detail=str(exc))


def first_success(attempts: List[Callable[[], FieldResult]], field_name: str) -> FieldResult:
    """Tries each attempt in order, returns the first that succeeds, else the
    last attempt's result (so the review report still shows *something*
    useful about why it failed)."""
    last = FieldResult(field=field_name, status=FieldStatus.not_found, detail="no attempts made")
    for attempt in attempts:
        result = attempt()
        if result.status == FieldStatus.filled:
            return result
        last = result
    return last


def detect_unmapped_fields(page: Page, handled_keywords: List[str]) -> List[FieldResult]:
    """Best-effort scan for form labels we didn't attempt to fill (e.g.
    company-specific screening questions), so the review report tells the
    user what still needs manual attention rather than just going quiet."""
    unmapped: List[FieldResult] = []
    try:
        labels = page.locator("label")
        count = min(labels.count(), 30)  # cap — some pages have huge/irrelevant label counts
        for i in range(count):
            try:
                text = labels.nth(i).inner_text(timeout=1000).strip()
            except Exception:
                continue
            if not text:
                continue
            lowered = text.lower()
            if any(keyword in lowered for keyword in handled_keywords):
                continue
            unmapped.append(
                FieldResult(field=f"unmapped:{text}", status=FieldStatus.not_found, detail="not attempted")
            )
    except Exception:
        pass
    return unmapped
