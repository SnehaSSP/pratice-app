from playwright.sync_api import sync_playwright, expect, Page

BASE_URL = "http://127.0.0.1:5000"

def test_page_title(page: Page):
    page.goto(BASE_URL)
    page.wait_for_selector("h1")
    expect(page).to_have_title("Playwright Practice Page")
    expect(page.get_by_test_id("page-title")).to_have_text("Playwright Practice Page")

