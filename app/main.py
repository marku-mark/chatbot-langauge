import json
import os
import platform
from pathlib import Path
from typing import Annotated, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import fastapi
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, StringConstraints

app = FastAPI()

welcome = (
    (Path(__file__).parent / "welcome.html")
    .read_text(encoding="utf-8")
    .replace("{{version}}", fastapi.__version__)
    .replace("{{python_version}}", platform.python_version())
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    return welcome


@app.get("/api")
def api() -> dict[str, str]:
    return {"message": "Hello from Laravel Cloud"}


class ChatbotMessage(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    context_token: str | None = Field(default=None, max_length=16384)


class ChatbotReply(BaseModel):
    message: str
    source: str
    context_token: str | None
    language: str
    presentation: dict[str, Any] | None = None


class ChatbotResponse(BaseModel):
    data: ChatbotReply


@app.post("/api/chatbot", response_model_exclude_unset=True)
def chatbot(message: ChatbotMessage) -> ChatbotResponse:
    capstone_url = os.environ.get("CAPSTONE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    request = Request(
        f"{capstone_url}/api/v1/chatbot",
        data=message.model_dump_json(exclude_none=True).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=35) as response:
            return ChatbotResponse.model_validate(json.load(response))
    except HTTPError as error:
        if error.code == 429:
            retry_after = error.headers.get("Retry-After")
            headers = {"Retry-After": retry_after} if retry_after else None
            raise HTTPException(429, "Too many chatbot requests. Try again shortly.", headers=headers) from None
        raise HTTPException(502, "Capstone could not answer the chatbot request.") from None
    except TimeoutError, URLError:
        raise HTTPException(503, "The Capstone chatbot is temporarily unavailable.") from None
    except ValueError:
        raise HTTPException(502, "Capstone returned an invalid chatbot response.") from None
