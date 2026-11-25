import os
import json
import requests
from dotenv import load_dotenv
from anthropic import Anthropic

# ---------- Setup ----------
load_dotenv(override=True)
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())

MODEL = "claude-sonnet-5-5"
BASE_URL = "http://127.0.0.1:5000"
MAX_STEPS = 10   # safety limit so the agent can't loop forever


# ---------- 1. Real Python functions ----------
def get_users():
    return requests.get(f"{BASE_URL}/api/users").json()


def get_user_by_id(user_id):
    return requests.get(f"{BASE_URL}/api/users/{user_id}").json()


def create_user(name, city, role):
    r = requests.post(f"{BASE_URL}/api/users", json={"name": name, "city": city, "role": role})
    return r.json()


def delete_user(user_id):
    r = requests.delete(f"{BASE_URL}/api/users/{user_id}")
    return r.json()


TOOL_FUNCTIONS = {
    "get_users": get_users,
    "get_user_by_id": get_user_by_id,
    "create_user": create_user,
    "delete_user": delete_user,
}


# ---------- 2. Tool descriptions ----------
tools = [
    {
        "name": "get_users",
        "description": "Get all users. Each user has id, name, city and role.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_user_by_id",
        "description": "Get one user by numeric id.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "create_user",
        "description": "Create a new user. Role must be one of: QA Engineer, Developer, Manager.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "city": {"type": "string"},
                "role": {"type": "string"},
            },
            "required": ["name", "city", "role"],
        },
    },
    {
        "name": "delete_user",
        "description": "Delete a user by numeric id. You need the id, so look it up first if you only know the name.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
]


# ---------- 3. The agent loop ----------
def run_agent(task):
    print(f"\n🎯 TASK: {task}\n")
    messages = [{"role": "user", "content": task}]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system="You are a helpful assistant that manages users in the practice app using the tools provided.",
            tools=tools,
            messages=messages,
        )

        # Save Claude's reply in the history (always)
        messages.append({"role": "assistant", "content": response.content})

        # Show any thinking text Claude wrote
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"💬 Claude: {block.text}")

        # Done?
        if response.stop_reason != "tool_use":
            print(f"\n✅ Finished in {step} step(s).")
            return

        # Run every tool Claude asked for
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"🔧 Step {step}: {block.name}({block.input})")
                result = TOOL_FUNCTIONS[block.name](**block.input)
                print(f"   ↳ {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        # Send results back, then loop again
        messages.append({"role": "user", "content": tool_results})

    print("\n⚠️ Stopped: reached MAX_STEPS.")


# ---------- 4. Give it a multi-step task ----------
run_agent(
    "Add a new user Priya from Mumbai as a QA Engineer. "
    "Then delete John. "
    "Finally, show me the full list of users as a table."
)
