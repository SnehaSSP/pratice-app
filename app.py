"""Practice app for learning Playwright.

Run:   python app.py
Open:  http://127.0.0.1:5000
"""
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# In-memory "database" (resets every time you restart the app)
import copy

DEFAULT_USERS = [
    {"id": 1, "name": "Sneha", "city": "Bangalore", "role": "QA Engineer"},
    {"id": 2, "name": "John", "city": "London", "role": "Developer"},
    {"id": 3, "name": "Maria", "city": "New York", "role": "Manager"},
]
USERS = copy.deepcopy(DEFAULT_USERS)

# ---------- Pages ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/frame")
def frame():
    return render_template("frame.html")


@app.post("/api/reset")
def reset_data():
    """Test helper: put the demo users back."""
    USERS.clear()
    USERS.extend(copy.deepcopy(DEFAULT_USERS))
    return jsonify({"status": "reset", "users": len(USERS)})

# ---------- API ----------
@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/users")
def list_users():
    return jsonify(USERS)


@app.get("/api/users/<int:user_id>")
def get_user(user_id):
    user = next((u for u in USERS if u["id"] == user_id), None)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@app.post("/api/users")
def create_user():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    city = (data.get("city") or "").strip()
    role = (data.get("role") or "").strip()

    if not name or not city or not role:
        return jsonify({"error": "name, city and role are required"}), 400

    new_user = {
        "id": max((u["id"] for u in USERS), default=0) + 1,
        "name": name,
        "city": city,
        "role": role,
    }
    USERS.append(new_user)
    return jsonify(new_user), 201


@app.delete("/api/users/<int:user_id>")
def delete_user(user_id):
    for u in USERS:
        if u["id"] == user_id:
            USERS.remove(u)
            return jsonify({"deleted": user_id})
    return jsonify({"error": "User not found"}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
