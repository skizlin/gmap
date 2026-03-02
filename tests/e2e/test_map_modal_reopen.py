"""
E2E test: Map Event modal works after Cancel and reopening (Map -> Cancel -> Map).

Run with: pytest tests/e2e/test_map_modal_reopen.py -v -s
Requires: pip install playwright && playwright install chromium
Server must be running at http://127.0.0.1:8000 (e.g. python -m backend.main)
"""

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8000"


def _open_map_modal(page: Page) -> None:
    """Open the Map Event modal: click first row's action menu, then 'Map Event'."""
    # Wait for feeder table to load (#feeder-events-body is the tbody, it contains tr)
    page.wait_for_selector("#feeder-events-body tr", timeout=15000)
    page.wait_for_timeout(300)
    # Open action menu (kebab) on first row
    page.locator("button[aria-haspopup='true'][title='Actions']").first.click()
    page.wait_for_timeout(250)
    # Click "Map Event"
    page.get_by_role("button", name="Map Event").first.click()


def _modal_content_visible(page: Page) -> bool:
    """Return True if modal is visible and has content (not just placeholder)."""
    modal = page.locator("#modal-content")
    if not modal.is_visible():
        return False
    # Modal content should have at least the header or sport row
    return (
        modal.locator("#select-sport").count() > 0
        or modal.locator("#input-sport").count() > 0
        or modal.locator("button:has-text('Cancel')").count() > 0
    )


def _modal_sport_usable(page: Page) -> bool:
    """
    Return True if the modal's sport control is usable (scripts ran and wired the UI).
    Strict: we require either #select-sport or #input-sport to be present and NOT disabled
    (when scripts run, sport row is interactive; when broken, they stay disabled).
    """
    modal = page.locator("#modal-content")
    select_sport = modal.locator("#select-sport")
    input_sport = modal.locator("#input-sport")
    if select_sport.count() > 0:
        return not select_sport.first.is_disabled()
    if input_sport.count() > 0:
        return not input_sport.first.is_disabled()
    return False


def _click_cancel(page: Page) -> None:
    """Close modal via Cancel button."""
    page.locator("#modal-content button:has-text('Cancel')").click()
    page.wait_for_timeout(300)


@pytest.fixture(scope="module")
def browser_context_args(browser_context_args):
    """Enable console log capture and allow viewing console in test output."""
    return {
        **browser_context_args,
        "ignore_https_errors": True,
    }


def test_map_modal_first_open_has_sport_control(page: Page):
    """First open: modal content loads and sport control is present."""
    page.goto(f"{BASE_URL}/feeder-events", wait_until="networkidle")
    page.wait_for_timeout(500)
    _open_map_modal(page)
    page.wait_for_timeout(1500)  # Allow HTMX to fetch and swap
    assert _modal_content_visible(page), "Modal content should be visible after first open"
    # Sport control should exist (select or input)
    modal = page.locator("#modal-content")
    has_sport = modal.locator("#select-sport").count() > 0 or modal.locator("#input-sport").count() > 0
    assert has_sport, "Modal should have sport select or input"


def test_map_modal_after_cancel_reopen_is_usable(page: Page):
    """
    Map -> Cancel -> Map: modal should be usable the second time (sport control not stuck disabled).
    This test fails when the bug is present (scripts not re-run after second load).
    """
    page.goto(f"{BASE_URL}/feeder-events", wait_until="networkidle")
    page.wait_for_timeout(500)

    # First open
    _open_map_modal(page)
    page.wait_for_timeout(1500)
    assert _modal_content_visible(page), "First open: modal content should be visible"
    _click_cancel(page)
    page.wait_for_timeout(400)

    # Second open (same or another row)
    _open_map_modal(page)
    page.wait_for_timeout(1500)

    assert _modal_content_visible(page), "Second open: modal content should be visible"
    init_count = page.evaluate("window.__mapModalInitCount || 0")
    assert init_count >= 2, (
        "Second open: modal init should have run twice (got %s). "
        "Inline scripts must run on each load (Map -> Cancel -> Map)." % init_count
    )
    assert _modal_sport_usable(page), (
        "Second open: sport control should be usable (modal scripts should have run)."
    )


def test_map_modal_console_no_errors(page: Page):
    """Capture console messages during Map -> Cancel -> Map; print [MapModal] logs and assert no JS errors."""
    logs = []
    page.on("console", lambda msg: logs.append({"type": msg.type, "text": msg.text}))

    page.goto(f"{BASE_URL}/feeder-events", wait_until="networkidle")
    page.wait_for_timeout(500)
    # Ensure debug logging is on so we see [MapModal] in console
    page.evaluate("window.__mapModalDebug = true")
    _open_map_modal(page)
    page.wait_for_timeout(1500)
    _click_cancel(page)
    page.wait_for_timeout(400)
    _open_map_modal(page)
    page.wait_for_timeout(1500)

    errors = [l for l in logs if l["type"] == "error"]
    map_modal_logs = [l for l in logs if "[MapModal]" in l.get("text", "")]
    print("\n--- [MapModal] console logs ---")
    for l in map_modal_logs:
        print(l["text"])
    print("--- End MapModal logs ---")
    if errors:
        print("\n--- Console errors ---")
        for e in errors:
            print(e["text"])
    assert not errors, f"Console had errors: {[e['text'] for e in errors]}"
