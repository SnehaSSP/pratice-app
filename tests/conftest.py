import pytest
import requests

BASE_URL = "http://127.0.0.1:5000"


@pytest.fixture(autouse=True)
def reset_app_data():
    """Runs automatically before EVERY test: reset users to Sneha, John, Maria."""
    requests.post(f"{BASE_URL}/api/reset", timeout=5)
    yield
