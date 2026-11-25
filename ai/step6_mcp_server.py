"""MCP server that exposes the practice app's user API as tools.

It is started automatically by the client (step6_mcp_client.py).
You don't run it yourself.
"""
import requests
from mcp.server.fastmcp import FastMCP

BASE_URL = "http://127.0.0.1:5000"

mcp = FastMCP("practice-app", log_level="ERROR")   # the server's name


@mcp.tool()
def get_users() -> list[dict]:
    """Get all users. Each user has id, name, city and role."""
    return requests.get(f"{BASE_URL}/api/users").json()


@mcp.tool()
def get_user_by_id(user_id: int) -> dict:
    """Get one user by their numeric id."""
    return requests.get(f"{BASE_URL}/api/users/{user_id}").json()


@mcp.tool()
def create_user(name: str, city: str, role: str) -> dict:
    """Create a new user. Role must be one of: QA Engineer, Developer, Manager."""
    r = requests.post(f"{BASE_URL}/api/users", json={"name": name, "city": city, "role": role})
    return r.json()


@mcp.tool()
def delete_user(user_id: int) -> dict:
    """Delete a user by numeric id. Look up the id first if you only know the name."""
    return requests.delete(f"{BASE_URL}/api/users/{user_id}").json()


if __name__ == "__main__":
    mcp.run()   # talks over stdin/stdout ("stdio" transport)
