import uuid
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:5000"


def test_show_alert(page: Page):
    """R9: Show Alert displays the alert 'Hello! This is an alert.'"""
    page.goto(BASE_URL)
    messages = []

    def handle(dialog):
        messages.append((dialog.type, dialog.message))
        dialog.accept()

    page.once("dialog", handle)
    page.get_by_test_id("alert-btn").click()
    assert messages == [("alert", "Hello! This is an alert.")]


def test_show_confirm_ok(page: Page):
    """R9: Show Confirm asks 'Do you want to continue?' and OK shows 'You clicked OK.'"""
    page.goto(BASE_URL)
    messages = []

    def handle(dialog):
        messages.append((dialog.type, dialog.message))
        dialog.accept()

    page.once("dialog", handle)
    page.get_by_test_id("confirm-btn").click()
    assert messages == [("confirm", "Do you want to continue?")]
    expect(page.get_by_test_id("dialog-result")).to_have_text("You clicked OK.")


def test_show_confirm_cancel(page: Page):
    """R9: Show Confirm asks the question and Cancel shows 'You clicked Cancel.'"""
    page.goto(BASE_URL)
    messages = []

    def handle(dialog):
        messages.append((dialog.type, dialog.message))
        dialog.dismiss()

    page.once("dialog", handle)
    page.get_by_test_id("confirm-btn").click()
    assert messages == [("confirm", "Do you want to continue?")]
    expect(page.get_by_test_id("dialog-result")).to_have_text("You clicked Cancel.")


def test_show_prompt_greets_user(page: Page):
    """R9: Show Prompt asks for a name and greets 'Hello, <name>!'"""
    page.goto(BASE_URL)
    name = f"Test{uuid.uuid4().hex[:6]}"
    types = []

    def handle(dialog):
        types.append(dialog.type)
        dialog.accept(name)

    page.once("dialog", handle)
    page.get_by_test_id("prompt-btn").click()
    expect(page.get_by_test_id("dialog-result")).to_have_text(f"Hello, {name}!")
    assert types == ["prompt"]
