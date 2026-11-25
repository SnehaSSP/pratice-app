import os
import json
import requests
from dotenv import load_dotenv
from anthropic import Anthropic

# ---------- Setup ----------
load_dotenv(override=True)          # .env wins over any old key in your shell
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())

MODEL = "claude-sonnet-5-5"
BASE_URL = "http://127.0.0.1:5000"


# ---------- 1. Real Python functions ----------
def get_users():
    return requests.get(f"{BASE_URL}/api/users").json()


def get_user_by_id(user_id):
    return requests.get(f"{BASE_URL}/api/users/{user_id}").json()


TOOL_FUNCTIONS = {
    "get_users": get_users,
    "get_user_by_id": get_user_by_id,
}


# ---------- 2. Tool descriptions (what Claude sees) ----------
tools = [
    {
        "name": "get_users",
        "description": "Get all users from the practice app. Each user has id, name, city and role.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_user_by_id",
        "description": "Get one user by their numeric id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "The user's id, e.g. 2"}
            },
            "required": ["user_id"],
        },
    },
]


# ---------- 3. Ask the question ----------
messages = [{"role": "user", "content": "Which users work in London? Also, who is user 3?"}]

response = client.messages.create(
    model=MODEL, max_tokens=1000, tools=tools, messages=messages
)
print("1st stop reason:", response.stop_reason)

if response.stop_reason != "tool_use":
    print(response.content[0].text)
    raise SystemExit


# ---------- 4. Run every tool Claude asked for ----------
tool_results = []
for block in response.content:
    if block.type == "tool_use":
        print(f"Claude wants: {block.name}({block.input})")
        func = TOOL_FUNCTIONS[block.name]
        result = func(**block.input)
        print("   result:", result)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(result),
        })


# ---------- 5. Send results back ----------
messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": tool_results})

final = client.messages.create(
    model=MODEL, max_tokens=1000, tools=tools, messages=messages
)
print("\n2nd stop reason:", final.stop_reason)
print("Claude says:\n", "".join(b.text for b in final.content if b.type == "text"))
