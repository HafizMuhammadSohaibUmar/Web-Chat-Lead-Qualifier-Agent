"""API tests."""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_widget_init_returns_token():
    response = client.post("/widget/init", json={"business_id": "test-business"})

    assert response.status_code == 200
    assert response.json()["token"]


def test_pii_blocking():
    token = client.post("/widget/init", json={"business_id": "test-business"}).json()["token"]
    response = client.post("/chat", json={"token": token, "message": "My card is 4111 1111 1111 1111"})

    assert response.status_code == 400


def test_widget_js_served():
    response = client.get("/static/widget.js")

    assert response.status_code == 200
    assert "EventSource" in response.text
