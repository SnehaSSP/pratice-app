import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import re
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from contextlib import AsyncExitStack

import numpy as np
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sentence_transformers import SentenceTransformer

# ---------- Setup ----------
load_dotenv(override=True)
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())

MODEL = "claude-sonnet-5-5"
MAX_STEPS = 60
MAX_RESULT_CHARS = 10000          # cap very long tool outputs (page snapshots) to save tokens
BASE_URL = "http://127.0.0.1:5000"

PROJECT_DIR = Path(__file__).parent.parent
DOC_PATH = PROJECT_DIR / "docs" / "requirements.md"
GENERATED_DIR = PROJECT_DIR / "tests" / "ai_generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# The MCP servers this agent connects to
MCP_SERVERS = {
    "playwright": StdioServerParameters(command="npx", args=["@playwright/mcp@latest"]),
    "users": StdioServerParameters(command=sys.executable,
                                   args=[str(Path(__file__).parent / "step6_mcp_server.py")]),
}


# =====================================================================
# PART A: Local tools (run inside this script)
# =====================================================================

# --- A1. RAG search (from step 5c) ---
def load_chunks(path):
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n(?=## )", text)
    return [p.strip() for p in parts if p.strip().startswith("## ")]


CHUNKS = load_chunks(DOC_PATH)
print("🧠 Loading embedding model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
CHUNK_VECTORS = embedder.encode(CHUNKS, normalize_embeddings=True)


def search_requirements(query, top_k=5):
    q_vector = embedder.encode(query, normalize_embeddings=True)
    scores = CHUNK_VECTORS @ q_vector
    best = np.argsort(scores)[::-1][:top_k]
    results = [{"score": round(float(scores[i]), 2), "requirement": CHUNKS[i]}
               for i in best if scores[i] >= 0.2]
    return results or "No matching requirements found."


# --- A2. Write a test file (safely) ---
SAFE_NAME = re.compile(r"test_[a-z0-9_]+\.py")

def write_test_file(filename, code):
    if not SAFE_NAME.fullmatch(filename):
        return "ERROR: filename must look like test_something.py (lowercase, no folders)."
    path = GENERATED_DIR / filename
    path.write_text(code, encoding="utf-8")
    return f"Saved {path.relative_to(PROJECT_DIR)} ({len(code.splitlines())} lines)"


# --- A3. Run pytest on that file ---
def run_pytest(filename):
    if not SAFE_NAME.fullmatch(filename):
        return "ERROR: invalid filename."
    path = GENERATED_DIR / filename
    if not path.exists():
        return f"ERROR: {filename} does not exist. Write it first."
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(path), "-q", "-rxXs", "-o", "addopts="],  # addopts= → headless & fast
        cwd=PROJECT_DIR, capture_output=True, text=True, timeout=300,
    )
    output = proc.stdout + proc.stderr
    return {"exit_code": proc.returncode, "output_tail": output[-4000:]}


LOCAL_FUNCTIONS = {
    "search_requirements": search_requirements,
    "write_test_file": write_test_file,
    "run_pytest": run_pytest,
}

LOCAL_TOOLS = [
    {
        "name": "search_requirements",
        "description": "Search the app's requirements document by meaning. Returns requirements with IDs like R3. Use this FIRST to learn the expected behaviour.",
        "input_schema": {"type": "object",
                         "properties": {"query": {"type": "string"}},
                         "required": ["query"]},
    },
    {
        "name": "write_test_file",
        "description": "Save (or overwrite) a pytest Playwright test file in tests/ai_generated/. Filename like test_add_user.py.",
        "input_schema": {"type": "object",
                         "properties": {"filename": {"type": "string"},
                                        "code": {"type": "string", "description": "Full Python file content"}},
                         "required": ["filename", "code"]},
    },
    {
        "name": "run_pytest",
        "description": "Run pytest on a file in tests/ai_generated/ and return the exit code and the end of the output.",
        "input_schema": {"type": "object",
                         "properties": {"filename": {"type": "string"}},
                         "required": ["filename"]},
    },
]


# =====================================================================
# PART B: Instructions for the agent
# =====================================================================
SYSTEM_PROMPT = f"""You are a senior QA automation engineer. The app under test runs at {BASE_URL}.
You write pytest + Playwright (Python, sync API) tests based on written requirements.

WORKFLOW
1. Call search_requirements to find the requirements for the feature.
2. Explore the real page with the Playwright MCP browser tools (navigate, snapshot, try the feature).
   Elements have data-testid attributes. If a browser_evaluate tool is available, you can list them with:
   () => [...document.querySelectorAll('[data-testid]')].map(e => e.dataset.testid)
   You may use the users tools (get_users etc.) to check data through the API.
3. Write ONE test file with write_test_file. One test function per requirement/scenario.
4. Run it with run_pytest.
5. If a test fails, decide WHY:
   - Test bug (wrong locator, timing, wrong expected text) -> fix the test and run again (max 3 rounds).
   - App bug (the app really behaves differently from the requirement) -> keep the test and add
     @pytest.mark.xfail(reason="App bug: R<id> - <short explanation>", strict=True)
6. Finish with a short report.

TEST STYLE (follow exactly)
- Start with:
    import uuid
    import pytest
    from playwright.sync_api import Page, expect
    BASE_URL = "{BASE_URL}"
- Each test takes `page: Page` and starts with page.goto(BASE_URL).
- Prefer page.get_by_test_id("..."); otherwise get_by_role / get_by_label.
- Assert with expect(...) (it auto-waits). Never use time.sleep.
- Tests must be independent and must not rely on existing users (e.g. John may be deleted).
  When creating users, use unique names like f"Test{{uuid.uuid4().hex[:6]}}".
- For alerts/confirms/prompts register a handler BEFORE clicking: page.once("dialog", lambda d: d.accept()).
- Add a one-line docstring per test that mentions the requirement ID.

FINAL REPORT FORMAT
File: tests/ai_generated/<name>.py
| Test | Requirement | Result (PASS / XFAIL app bug) |
App bugs found: <list with requirement IDs, or "none">"""


# =====================================================================
# PART C: Agent loop with tool routing
# =====================================================================
TOOL_TO_SESSION = {}     # MCP tool name -> the server session that owns it


def short(value, n=120):
    s = str(value).replace("\n", " ")
    return s[:n] + ("..." if len(s) > n else "")


async def call_tool(name, args):
    """Route a tool call to a local function or to the right MCP server."""
    if name in LOCAL_FUNCTIONS:
        try:
            result = LOCAL_FUNCTIONS[name](**args)
            text = result if isinstance(result, str) else json.dumps(result)
            return text, text.startswith("ERROR")
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {str(e)[:300]}", True

    session = TOOL_TO_SESSION.get(name)
    if session is None:
        return f"ERROR: unknown tool {name}", True
    result = await session.call_tool(name, args)
    text = "".join(c.text for c in result.content if c.type == "text") or "(no text output)"
    return text, bool(result.isError)


async def run_agent(tools, task):
    print(f"\n🎯 TASK: {task}\n")
    messages = [{"role": "user", "content": task}]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=8000,                 # room to write a whole test file
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
            if block.type != "tool_use":
                continue

            icon = {"search_requirements": "📚", "write_test_file": "📝", "run_pytest": "🧪"}.get(
                block.name, "🎭" if block.name.startswith("browser_") else "🔌")
            shown_args = {"filename": block.input.get("filename")} if block.name == "write_test_file" else block.input
            print(f"{icon} Step {step}: {block.name}({short(shown_args, 100)})")

            text, is_error = await call_tool(block.name, block.input)
            print(f"   ↳ {short(text)}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": text[:MAX_RESULT_CHARS],
                "is_error": is_error,
            })

        messages.append({"role": "user", "content": tool_results})

    print("\n⚠️ Stopped: reached MAX_STEPS.")


# =====================================================================
# PART D: Connect to all MCP servers, then take tasks
# =====================================================================
async def main():
    async with AsyncExitStack() as stack:
        tools = []
        for server_name, params in MCP_SERVERS.items():
            print(f"🔌 Starting MCP server '{server_name}'...")
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            listed = await session.list_tools()
            for t in listed.tools:
                TOOL_TO_SESSION[t.name] = session
                tools.append({"name": t.name, "description": t.description or "",
                              "input_schema": t.inputSchema})
            print(f"   ✓ {len(listed.tools)} tools from '{server_name}'")

        tools += LOCAL_TOOLS
        print(f"🧰 Total tools available to Claude: {len(tools)}")

        print("\nExample: Write tests for the Add User feature.")
        while True:
            task = input("\n📝 What should I write tests for? (or 'quit'): ").strip()
            if task.lower() in ("quit", "exit", ""):
                break
            await run_agent(tools, task)


if __name__ == "__main__":
    asyncio.run(main())
