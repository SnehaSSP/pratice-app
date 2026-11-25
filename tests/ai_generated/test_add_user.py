import uuid
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:5000"


def unique_name():
    return f"Test{uuid.uuid4().hex[:6]}"


def fill_form(page: Page, name=None, city=None, role=None, experience=None, terms=True):
    if name:
        page.get_by_test_id("name-input").fill(name)
    if city:
        page.get_by_test_id("city-input").fill(city)
    if role:
        page.get_by_test_id("role-select").select_option(role)
    if experience:
        page.get_by_test_id(f"exp-{experience}").check()
    if terms:
        page.get_by_test_id("terms-checkbox").check()


def test_add_user_success(page: Page):
    """R6: valid submit shows success message, clears form and adds user to table."""
    page.goto(BASE_URL)
    name = unique_name()
    fill_form(page, name, "Paris", "Developer", "junior")
    page.get_by_test_id("submit-btn").click()
    expect(page.get_by_test_id("form-message")).to_have_text(f'User "{name}" added successfully!')
    expect(page.get_by_test_id("name-input")).to_have_value("")
    expect(page.get_by_test_id("city-input")).to_have_value("")
    expect(page.get_by_test_id("role-select")).to_have_value("")
    expect(page.get_by_test_id("terms-checkbox")).not_to_be_checked()
    row = page.get_by_test_id("users-table").locator("tr", has_text=name)
    expect(row).to_have_count(1)
    expect(row).to_contain_text("Paris")
    expect(row).to_contain_text("Developer")


@pytest.mark.parametrize("missing", ["name", "city", "role"])
def test_required_fields_missing(page: Page, missing):
    """R2: missing Name, City or Role shows an error and creates no user."""
    page.goto(BASE_URL)
    name = unique_name()
    values = {"name": name, "city": "Berlin", "role": "Manager"}
    values[missing] = None
    fill_form(page, values["name"], values["city"], values["role"], "senior")
    count_before = page.get_by_test_id("user-count").inner_text()
    page.get_by_test_id("submit-btn").click()
    expect(page.get_by_test_id("form-message")).to_contain_text("required")
    expect(page.get_by_test_id("form-message")).not_to_contain_text("added successfully")
    expect(page.get_by_test_id("user-count")).to_have_text(count_before)
    expect(page.get_by_test_id("users-table").locator("tr", has_text=name)).to_have_count(0)


@pytest.mark.xfail(
    reason="App bug: R3 - user can be added without choosing an experience level (Junior/Senior)",
    strict=True,
)
def test_experience_required(page: Page):
    """R3: user must choose an experience level; submit without one must not create a user."""
    page.goto(BASE_URL)
    name = unique_name()
    fill_form(page, name, "Madrid", "Manager", experience=None)
    page.get_by_test_id("submit-btn").click()
    # some feedback must appear (success or error) before checking the outcome
    expect(page.get_by_test_id("form-message")).not_to_be_empty()
    expect(page.get_by_test_id("form-message")).not_to_contain_text("added successfully")
    expect(page.get_by_test_id("users-table").locator("tr", has_text=name)).to_have_count(0)


def test_experience_options(page: Page):
    """R3: Junior and Senior are offered, and they are mutually exclusive."""
    page.goto(BASE_URL)
    junior = page.get_by_test_id("exp-junior")
    senior = page.get_by_test_id("exp-senior")
    junior.check()
    expect(junior).to_be_checked()
    senior.check()
    expect(senior).to_be_checked()
    expect(junior).not_to_be_checked()


def test_terms_not_accepted(page: Page):
    """R4: unticked terms shows 'Please accept the terms.' and creates no user."""
    page.goto(BASE_URL)
    name = unique_name()
    fill_form(page, name, "Oslo", "QA Engineer", "senior", terms=False)
    count_before = page.get_by_test_id("user-count").inner_text()
    page.get_by_test_id("submit-btn").click()
    expect(page.get_by_test_id("form-message")).to_have_text("Please accept the terms.")
    expect(page.get_by_test_id("user-count")).to_have_text(count_before)
    expect(page.get_by_test_id("users-table").locator("tr", has_text=name)).to_have_count(0)


def test_allowed_roles_only(page: Page):
    """R5: role dropdown offers only QA Engineer, Developer and Manager."""
    page.goto(BASE_URL)
    options = page.get_by_test_id("role-select").locator("option")
    texts = [t.strip() for t in options.all_inner_texts()]
    real_roles = [t for t in texts if not t.startswith("--")]
    assert real_roles == ["QA Engineer", "Developer", "Manager"]


@pytest.mark.parametrize("role", ["QA Engineer", "Developer", "Manager"])
def test_each_allowed_role_can_be_saved(page: Page, role):
    """R5: each allowed role can be selected and is shown in the users table."""
    page.goto(BASE_URL)
    name = unique_name()
    fill_form(page, name, "Rome", role, "junior")
    page.get_by_test_id("submit-btn").click()
    expect(page.get_by_test_id("form-message")).to_have_text(f'User "{name}" added successfully!')
    expect(page.get_by_test_id("users-table").locator("tr", has_text=name)).to_contain_text(role)
