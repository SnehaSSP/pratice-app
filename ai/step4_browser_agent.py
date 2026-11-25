import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from playwright.sync_api import sync_playwright

# ---------- Setup ----------
load_dotenv(override=True)
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())

MODEL = "claude-sonnet-5-5"
BASE_URL = "http://127.0.0.1:5000"
MAX_STEPS = 25


# ---------- Start the browser (you will see it) ----------
pw = sync_playwright().start()
browser = pw.chromium.launch(headless=False, slow_mo=500)
page = browser.new_page()
page.set_default_timeout(5000)   # fail fast (5s) instead of waiting 30s

# Auto-handle alert/confirm/prompt and remember their messages
dialog_log = []
def handle_dialog(dialog):
    dialog_log.append(f"{dialog.type}: {dialog.message}")
    dialog.accept()
page.on("dialog", handle_dialog)



# ---------- 1. Browser functions (the "hands" and "eyes") ----------
def open_page(path="/"):
    page.goto(BASE_URL + path)
    return {"url": page.url, "title": page.title()}


def get_page_elements():
    """Return every element that has a data-testid, so Claude can 'see' the page."""
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('[data-testid]')).map(el => ({
            test_id: el.dataset.testid,
            tag: el.tagName.toLowerCase(),
            type: el.type || null,
            text: (el.innerText || el.value || el.placeholder || '').trim().slice(0, 80),
            visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
            disabled: el.disabled || false
        }))
    """)


def fill(test_id, text):
    page.get_by_test_id(test_id).fill(text)
    return f"Filled '{test_id}' with '{text}'"


def select_option(test_id, value):
    page.get_by_test_id(test_id).select_option(value)
    return f"Selected '{value}' in '{test_id}'"


def check(test_id):
    page.get_by_test_id(test_id).check()
    return f"Checked '{test_id}'"


def click(test_id):
    page.get_by_test_id(test_id).click()
    page.wait_for_timeout(500)   # give the page a moment to react (API calls, messages)
    return f"Clicked '{test_id}'"


def get_text(test_id):
    return page.get_by_test_id(test_id).inner_text()


def get_dialog_messages():
    return dialog_log


TOOL_FUNCTIONS = {
    "open_page": open_page,
    "get_page_elements": get_page_elements,
    "fill": fill,
    "select_option": select_option,
    "check": check,
    "click": click,
    "get_text": get_text,
    "get_dialog_messages": get_dialog_messages,
}


# ---------- 2. Tool descriptions (what Claude sees) ----------
def test_id_param(desc="The element's data-testid"):
    return {"type": "string", "description": desc}

tools = [
    {
        "name": "open_page",
        "description": "Open a page of the practice app. Use '/' for the home page.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "get_page_elements",
        "description": "List all elements on the current page that have a data-testid, with their tag, type, text, visibility and disabled state. Call this to 'see' the page before acting.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "fill",
        "description": "Type text into an input or textarea (clears it first).",
        "input_schema": {"type": "object", "properties": {"test_id": test_id_param(), "text": {"type": "string"}}, "required": ["test_id", "text"]},
    },
    {
        "name": "select_option",
        "description": "Choose an option in a <select> dropdown by its value.",
        "input_schema": {"type": "object", "properties": {"test_id": test_id_param(), "value": {"type": "string"}}, "required": ["test_id", "value"]},
    },
    {
        "name": "check",
        "description": "Tick a checkbox or radio button.",
        "input_schema": {"type": "object", "properties": {"test_id": test_id_param()}, "required": ["test_id"]},
    },
    {
        "name": "click",
        "description": "Click a button or link. Alerts/confirms/prompts are accepted automatically.",
        "input_schema": {"type": "object", "properties": {"test_id": test_id_param()}, "required": ["test_id"]},
    },
    {
        "name": "get_text",
        "description": "Read the visible text of one element.",
        "input_schema": {"type": "object", "properties": {"test_id": test_id_param()}, "required": ["test_id"]},
    },
    {
        "name": "get_dialog_messages",
        "description": "Get the messages of all alert/confirm/prompt dialogs shown so far.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


SYSTEM_PROMPT = """You are a QA tester controlling a real browser with the tools provided.
- Always call get_page_elements first to see what is on the page.
- Use the exact test_id values you see; never guess them.
- After an action, verify the result (read the text or look at the elements again).
- At the end, give a short report and say PASS or FAIL for the task."""


# ---------- 3. The agent loop (same as step 3) ----------
def run_agent(task):
    print(f"\n🎯 TASK: {task}\n")
    messages = [{"role": "user", "content": task}]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"💬 Claude: {block.text}")

        if response.stop_reason != "tool_use":
            print(f"\n✅ Finished in {step} step(s).")
            return

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"🔧 Step {step}: {block.name}({block.input})")
                try:
                    result = TOOL_FUNCTIONS[block.name](**block.input)
                except Exception as e:
                    # Send the error back so Claude can try something else
                    result = f"ERROR: {type(e).__name__}: {str(e)[:300]}"
                short = str(result)
                print(f"   ↳ {short[:150]}{'...' if len(short) > 150 else ''}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        messages.append({"role": "user", "content": tool_results})

    print("\n⚠️ Stopped: reached MAX_STEPS.")



# ---------- 4. Run a task ----------
try:
    run_agent(
        "Open the home page. Add a new user named Priya from Mumbai, role QA Engineer, "
        "experience Senior, and accept the terms. Submit the form. "
        "Then verify the success message and that Priya appears in the users table."
    )
finally:
    input("\nPress Enter to close the browser...")
    browser.close()
    pw.stop()



