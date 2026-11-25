import re
import uuid
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:5000"


def add_user(page: Page, name: str, city: str = "Berlin", role: str = "Developer"):
    page.get_by_test_id("name-input").fill(name)
    page.get_by_test_id("city-input").fill(city)
    page.get_by_test_id("role-select").select_option(role)
    page.get_by_test_id("exp-junior").check()
    page.get_by_test_id("terms-checkbox").check()
    page.get_by_test_id("submit-btn").click()
    expect(row_for(page, name)).to_have_count(1)


def row_for(page: Page, name: str):
    return page.get_by_test_id("users-table").locator("tbody tr").filter(has_text=name)


def rows(page: Page):
    return page.get_by_test_id("users-table").locator("tbody tr")


def test_table_has_expected_columns(page: Page):
    """R7: the users table shows ID, Name, City and Role columns."""
    page.goto(BASE_URL)
    headers = page.get_by_test_id("users-table").locator("thead th")
    expect(headers.nth(0)).to_have_text("ID")
    expect(headers.nth(1)).to_have_text("Name")
    expect(headers.nth(2)).to_have_text("City")
    expect(headers.nth(3)).to_have_text("Role")


def test_new_user_row_shows_all_fields_and_delete_button(page: Page):
    """R7: a user row shows ID, Name, City, Role and a Delete button."""
    page.goto(BASE_URL)
    name = f"Test{uuid.uuid4().hex[:6]}"
    add_user(page, name, city="Paris", role="Manager")
    row = row_for(page, name)
    cells = row.locator("td")
    expect(cells.nth(0)).to_have_text(re.compile(r"^\d+$"))
    expect(cells.nth(1)).to_have_text(name)
    expect(cells.nth(2)).to_have_text("Paris")
    expect(cells.nth(3)).to_have_text("Manager")
    expect(row.get_by_role("button", name="Delete")).to_have_count(1)


def test_every_row_has_delete_button(page: Page):
    """R7: every row in the users table has a Delete button."""
    page.goto(BASE_URL)
    add_user(page, f"Test{uuid.uuid4().hex[:6]}")
    count = rows(page).count()
    assert count >= 1
    expect(page.get_by_test_id("users-table").get_by_role("button", name="Delete")).to_have_count(count)


def test_total_counter_equals_number_of_rows(page: Page):
    """R7: the Total users counter equals the number of table rows."""
    page.goto(BASE_URL)
    add_user(page, f"Test{uuid.uuid4().hex[:6]}")
    expect(page.get_by_test_id("user-count")).to_have_text(str(rows(page).count()))


def test_delete_removes_user_and_decrements_counter(page: Page):
    """R8: clicking Delete removes the user immediately and decreases the counter by 1."""
    page.goto(BASE_URL)
    name = f"Test{uuid.uuid4().hex[:6]}"
    add_user(page, name)
    before = rows(page).count()
    expect(page.get_by_test_id("user-count")).to_have_text(str(before))

    row_for(page, name).get_by_role("button", name="Delete").click()

    expect(row_for(page, name)).to_have_count(0)
    expect(rows(page)).to_have_count(before - 1)
    expect(page.get_by_test_id("user-count")).to_have_text(str(before - 1))


def test_delete_only_removes_selected_user(page: Page):
    """R8: deleting one user leaves other users in the table."""
    page.goto(BASE_URL)
    keep = f"Test{uuid.uuid4().hex[:6]}"
    remove = f"Test{uuid.uuid4().hex[:6]}"
    add_user(page, keep)
    add_user(page, remove)

    row_for(page, remove).get_by_role("button", name="Delete").click()

    expect(row_for(page, remove)).to_have_count(0)
    expect(row_for(page, keep)).to_have_count(1)
    expect(page.get_by_test_id("user-count")).to_have_text(str(rows(page).count()))


def test_deleted_user_stays_deleted_after_reload(page: Page):
    """R8: a deleted user does not reappear after reloading the page."""
    page.goto(BASE_URL)
    name = f"Test{uuid.uuid4().hex[:6]}"
    add_user(page, name)
    row_for(page, name).get_by_role("button", name="Delete").click()
    expect(row_for(page, name)).to_have_count(0)

    page.reload()

    expect(row_for(page, name)).to_have_count(0)
    expect(page.get_by_test_id("user-count")).to_have_text(str(rows(page).count()))
