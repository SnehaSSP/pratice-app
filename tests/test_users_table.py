from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:5000"


def test_delete_user_john(page: Page):
    page.goto(BASE_URL)

    rows = page.get_by_test_id("users-table").locator("tbody tr")
    john_row = rows.filter(has_text="John")
    expect(john_row).to_be_visible()
    count_before = rows.count()
    john_row.get_by_role("button", name="Delete").click()
    expect(john_row).to_have_count(0)
    expect(rows).to_have_count(count_before - 1)
    expect(page.get_by_test_id("user-count")).to_have_text(str(count_before - 1))

