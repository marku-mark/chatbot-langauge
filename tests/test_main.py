import json
import platform
from io import BytesIO
from urllib.error import URLError
from urllib.request import Request

import fastapi
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app import main
from app.main import app

client = TestClient(app)


def test_the_welcome_page_responds() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Your FastAPI app is up and running on Laravel Cloud." in response.text
    assert f"FastAPI {fastapi.__version__} · Python {platform.python_version()}" in response.text


def test_the_api_responds() -> None:
    response = client.get("/api")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Laravel Cloud"}


def test_chatbot_forwards_the_message_and_context_as_a_guest(monkeypatch: MonkeyPatch) -> None:
    payload = {"message": "Asa ang tindahan?", "context_token": "previous-token"}
    reply = {
        "data": {
            "message": "Visit our Sagay branch.",
            "source": "deterministic",
            "context_token": "next-token",
            "language": "ceb",
        }
    }

    def capstone(request: Request, timeout: int) -> BytesIO:
        assert request.full_url == "http://capstone.test/api/v1/chatbot"
        assert request.get_method() == "POST"
        assert request.data is not None
        assert json.loads(request.data) == payload
        assert request.get_header("Authorization") is None
        assert timeout == 35
        return BytesIO(json.dumps(reply).encode())

    monkeypatch.setenv("CAPSTONE_BASE_URL", "http://capstone.test/")
    monkeypatch.setattr(main, "urlopen", capstone)
    response = client.post("/api/chatbot", json=payload, headers={"Authorization": "Bearer client-token"})

    assert response.status_code == 200
    assert response.json() == reply


def test_chatbot_reports_unavailable_capstone(monkeypatch: MonkeyPatch) -> None:
    def unavailable(request: Request, timeout: int) -> BytesIO:
        raise URLError("connection refused")

    monkeypatch.setattr(main, "urlopen", unavailable)
    response = client.post("/api/chatbot", json={"message": "Hello"})

    assert response.status_code == 503
    assert response.json() == {"detail": "The Capstone chatbot is temporarily unavailable."}


def test_chatbot_rejects_a_blank_message() -> None:
    response = client.post("/api/chatbot", json={"message": "   "})

    assert response.status_code == 422
