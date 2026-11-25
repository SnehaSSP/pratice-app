from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:5000"


def test_add_user_successfully(page: Page):
    page.goto(BASE_URL)

    # Text boxes
    page.get_by_test_id("name-input").fill("Alex")
    page.get_by_test_id("city-input").fill("Paris")
    page.get_by_test_id("comments-input").fill("Testing the form")
    page.get_by_test_id("role-select").select_option("Manager")
    page.locator("#exp-senior").check()
    page.get_by_test_id("terms-checkbox").check()
    page.get_by_test_id("submit-btn").click()
    expect(page.get_by_test_id("form-message")).to_have_text('User "Alex" added successfully!')


def test_error_when_terms_not_accepted(page: Page):
    page.goto(BASE_URL)
    page.get_by_test_id("name-input").fill("Alex")
    page.get_by_test_id("city-input").fill("Paris")
    page.get_by_test_id("role-select").select_option("Developer")
    # terms checkbox NOT checked
    page.get_by_test_id("submit-btn").click()
    expect(page.get_by_test_id("form-message")).to_have_text("Please accept the terms.")
