import os
import asyncio

from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------- Setup ----------
load_dotenv(override=True)
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
MODEL = "claude-sonnet-5-5"
MAX_STEPS = 30
BASE_URL = "http://127.0.0.1:5000"

# Start Playwright's official MCP server (instead of our own server from step 6)
server_params = StdioServerParameters(
    command="npx",
    args=["@playwright/mcp@latest"],
)

SYSTEM_PROMPT = f"""You are a QA tester controlling a real browser through Playwright MCP tools.
The app under test runs at {BASE_URL}.
- Use the page snapshot to see the page and to get element references before clicking or typing.
- If a dialog (alert/confirm/prompt) appears, handle it with the dialog tool.
- Verify results after each action.
- End with a short report and PASS or FAIL."""


# ---------- The agent loop (same as step 6) ----------
async def run_agent(session, tools, task):
    print(f"\n🎯 TASK: {task}\n")
    messages = [{"role": "user", "content": task}]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        # Show any text Claude wrote
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"💬 Claude: {block.text}")

        # Done?
        if response.stop_reason != "tool_use":
            print(f"\n✅ Finished in {step} step(s).")
            return

        # Run every tool Claude asked for, via the Playwright MCP server
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"🎭 Step {step}: {block.name}({block.input})")
                result = await session.call_tool(block.name, block.input)
                text = "".join(c.text for c in result.content if c.type == "text")
                preview = text[:120].replace("\n", " ")
                print(f"   ↳ {preview}{'...' if len(text) > 120 else ''}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text or "(no text output)",
                    "is_error": bool(result.isError),
                })

        messages.append({"role": "user", "content": tool_results})

    print("\n⚠️ Stopped: reached MAX_STEPS.")


# ---------- Connect to the server and run tasks ----------
async def main():
    print("🎭 Starting Playwright MCP server (first time may take a minute)...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Ask the server which tools it has
            listed = await session.list_tools()
            print(f"🔌 Connected. Playwright MCP offers {len(listed.tools)} tools:")
            print("   " + ", ".join(t.name for t in listed.tools))

            # Convert MCP tools → Anthropic tool format
            tools = [
                {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                for t in listed.tools
            ]

            # Type tasks
            while True:
                task = input("\n📝 What should I test? (or 'quit'): ").strip()
                if task.lower() in ("quit", "exit", ""):
                    break
                await run_agent(session, tools, task)


if __name__ == "__main__":
    asyncio.run(main())
