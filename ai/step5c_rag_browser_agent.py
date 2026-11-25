import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import re
import json
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from anthropic import Anthropic
from playwright.sync_api import sync_playwright
from sentence_transformers import SentenceTransformer

# ---------- Setup ----------
load_dotenv(override=True)
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())

MODEL = "claude-sonnet-5-5"
BASE_URL = "http://127.0.0.1:5000"
DOC_PATH = Path(__file__).parent.parent / "docs" / "requirements.md"
MAX_STEPS = 40
MIN_SCORE = 0.25


# =====================================================================
# PART A: RAG (from step 5b)
# =====================================================================
def load_chunks(path):
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n(?=## )", text)
    return [p.strip() for p in parts if p.strip().startswith("## ")]


CHUNKS = load_chunks(DOC_PATH)
print("🧠 Loading embedding model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
CHUNK_VECTORS = embedder.encode(CHUNKS, normalize_embeddings=True)
print(f"📚 Embedded {len(CHUNKS)} requirement chunks")


def search_requirements(query, top_k=4):
    q_vector = embedder.encode(query, normalize_embeddings=True)
    scores = CHUNK_VECTORS @ q_vector
    best = np.argsort(scores)[::-1][:top_k]
    results = [{"score": round(float(scores[i]), 2), "requirement": CHUNKS[i]}
               for i in best if scores[i] >= MIN_SCORE]
    return results or "No matching requirements found."


# =====================================================================
# PART B: Browser (from step 4)
# =====================================================================
pw = sync_playwright().start()
browser = pw.chromium.launch(headless=False, slow_mo=400)
page = browser.new_page()
page.set_default_timeout(5000)

dialog_log = []
def handle_dialog(dialog):
    dialog_log.append(f"{dialog.type}: {dialog.message}")
    dialog.accept()
page.on("dialog", handle_dialog)


def open_page(path="/"):
    page.goto(BASE_URL + path)
    return {"url": page.url, "title": page.title()}


def get_page_elements():
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('[data-testid]')).map(el => ({
            test_id: el.dataset.testid,
            tag: el.tagName.toLowerCase(),
            type: el.type || null,
            text: (el.innerText || el.value || el.placeholder || '').trim().slice(0, 80),
            visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
            disabled: el.disabled || false,
            checked: el.checked ?? null
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
    page.wait_for_timeout(500)
    return f"Clicked '{test_id}'"


def get_text(test_id):
    return page.get_by_test_id(test_id).inner_text()


def get_dialog_messages():
    return dialog_log


# =====================================================================
# PART C: Tools (browser tools + the NEW search_requirements tool)
# =====================================================================
TOOL_FUNCTIONS = {
    "search_requirements": search_requirements,
    "open_page": open_page,
    "get_page_elements": get_page_elements,
    "fill": fill,
    "select_option": select_option,
    "check": check,
    "click": click,
    "get_text": get_text,
    "get_dialog_messages": get_dialog_messages,
}

def test_id_param():
    return {"type": "string", "description": "The element's data-testid"}

tools = [
    {
        "name": "search_requirements",
        "description": "Search the app's requirements document by meaning. Returns the most relevant requirements (with IDs like R3). Use this BEFORE testing to learn what the correct behaviour is.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look for, e.g. 'add user form'"}},
            "required": ["query"],
        },
    },
    {
        "name": "open_page",
        "description": "Open a page of the practice app. Use '/' for the home page.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "get_page_elements",
        "description": "List all elements with a data-testid: tag, type, text, visible, disabled, checked. Call this to 'see' the page.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "fill",
        "description": "Type text into an input or textarea (clears it first). Use an empty string to clear it.",
        "input_schema": {"type": "object", "properties": {"test_id": test_id_param(), "text": {"type": "string"}}, "required": ["test_id", "text"]},
    },
    {
        "name": "select_option",
        "description": "Choose an option in a <select> by its value. Use '' for the empty option.",
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

SYSTEM_PROMPT = """You are a QA tester. You test a web app against its written requirements.

How to work:
1. FIRST call search_requirements to find the requirements related to the task.
2. Open the page and call get_page_elements to see it. Use exact test_ids; never guess.
3. Test each relevant requirement with real actions, including negative cases
   (e.g. missing fields, unticked checkbox). Reload the page ('/') between tests for a clean start.
4. Compare what actually happened with what the requirement says.

Final report format:
| Requirement | Result | Evidence |
|-------------|--------|----------|
| R2 | PASS / FAIL / CANNOT VERIFY | what you saw |

Only judge against the requirements you found. Be honest: if something can't be checked from the page, say CANNOT VERIFY."""


# =====================================================================
# PART D: The agent loop (same as step 4)
# =====================================================================
def run_agent(task):
    print(f"\n🎯 TASK: {task}\n")
    messages = [{"role": "user", "content": task}]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=3000,
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
                icon = "📚" if block.name == "search_requirements" else "🔧"
                print(f"{icon} Step {step}: {block.name}({block.input})")
                try:
                    result = TOOL_FUNCTIONS[block.name](**block.input)
                except Exception as e:
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


# =====================================================================
# PART E: Type tasks
# =====================================================================
try:
    print("\nExample: Test the Add User feature against the requirements.")
    while True:
        task = input("\n📝 What should I test? (or 'quit'): ").strip()
        if task.lower() in ("quit", "exit", ""):
            break
        run_agent(task)
finally:
    browser.close()
    pw.stop()
