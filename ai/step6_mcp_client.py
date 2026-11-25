import os
import sys
import json
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------- Setup ----------
load_dotenv(override=True)
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
MODEL = "claude-sonnet-5-5"
MAX_STEPS = 10

SERVER_PATH = Path(__file__).parent / "step6_mcp_server.py"

# How to start the server: "python step6_mcp_server.py"
server_params = StdioServerParameters(
    command=sys.executable,          # the same Python you're using now
    args=[str(SERVER_PATH)],
)


async def run_agent(session, tools, task):
    print(f"\n🎯 TASK: {task}\n")
    messages = [{"role": "user", "content": task}]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system="You manage users in the practice app using the tools provided.",
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
                print(f"🔌 Step {step}: MCP call → {block.name}({block.input})")

                # ⭐ THE KEY DIFFERENCE: ask the MCP server to run the tool
                result = await session.call_tool(block.name, block.input)
                text = "".join(c.text for c in result.content if c.type == "text")

                print(f"   ↳ {text[:150]}{'...' if len(text) > 150 else ''}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text,
                    "is_error": bool(result.isError),
                })

        messages.append({"role": "user", "content": tool_results})

    print("\n⚠️ Stopped: reached MAX_STEPS.")


async def main():
    # 1. Start the server and connect to it
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2. Ask the server which tools it has
            listed = await session.list_tools()
            print("🔌 Connected to MCP server. Tools found:")
            for t in listed.tools:
                print(f"   • {t.name}: {t.description}")

            # 3. Convert MCP tools → Anthropic tool format
            tools = [
                {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                for t in listed.tools
            ]

            # 4. Run tasks
            while True:
                task = input("\n📝 Task (or 'quit'): ").strip()
                if task.lower() in ("quit", "exit", ""):
                    break
                await run_agent(session, tools, task)


if __name__ == "__main__":
    asyncio.run(main())
