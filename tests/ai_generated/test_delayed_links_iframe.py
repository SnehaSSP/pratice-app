import uuid
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:5000"


def test_delayed_message_loading_then_data(page: Page):
    """R10: Load message shows 'Loading...' and then 'Data loaded after 3 seconds!'."""
    page.goto(BASE_URL)
    page.get_by_test_id("delayed-btn").click()
    expect(page.get_by_test_id("delayed-text")).to_have_text("Loading...")
    expect(page.get_by_test_id("delayed-text")).to_have_text(
        "Data loaded after 3 seconds!", timeout=6000
    )


def test_internal_link_opens_frame_page(page: Page):
    """R11: The internal link opens the frame page."""
    page.goto(BASE_URL)
    page.get_by_test_id("internal-link").click()
    expect(page).to_have_url(f"{BASE_URL}/frame")
    expect(page.get_by_test_id("frame-title")).to_be_visible()


def test_external_link_opens_playwright_in_new_tab(page: Page):
    """R11: The external link opens playwright.dev in a new tab."""
    page.goto(BASE_URL)
    with page.context.expect_page() as new_page_info:
        page.get_by_test_id("external-link").click()
    new_page = new_page_info.value
    new_page.wait_for_load_state("domcontentloaded")
    assert "playwright.dev" in new_page.url


def test_broken_link_returns_404(page: Page):
    """R11: The broken link must return a 404 page."""
    page.goto(BASE_URL)
    with page.expect_navigation() as nav_info:
        page.get_by_test_id("broken-link").click()
    assert nav_info.value.status == 404


def test_iframe_shows_typed_text(page: Page):
    """R12: Clicking the frame button shows 'Frame says: <text>'."""
    page.goto(BASE_URL)
    text = f"Test{uuid.uuid4().hex[:6]}"
    frame = page.frame_locator("[data-testid='practice-frame']")
    frame.get_by_test_id("frame-input").fill(text)
    frame.get_by_test_id("frame-btn").click()
    expect(frame.get_by_test_id("frame-result")).to_have_text(f"Frame says: {text}")


def test_iframe_shows_empty_when_nothing_typed(page: Page):
    """R12: Clicking the frame button with no text shows 'Frame says: (empty)'."""
    page.goto(BASE_URL)
    frame = page.frame_locator("[data-testid='practice-frame']")
    frame.get_by_test_id("frame-btn").click()
    expect(frame.get_by_test_id("frame-result")).to_have_text("Frame says: (empty)")
