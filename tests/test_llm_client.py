import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatbot.llm_client import GroqAPIError, query_groq_api


def test_returns_model_text_on_success(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "choices": [{"message": {"content": "Computer Science"}}]
    }
    monkeypatch.setattr("chatbot.llm_client.requests.post", Mock(return_value=response))

    assert query_groq_api("prompt") == "Computer Science"
    response.raise_for_status.assert_called_once()


def test_http_error_raises_typed_error_without_returning_text(monkeypatch):
    response = Mock()
    response.status_code = 429
    error = requests.exceptions.HTTPError("rate limited", response=response)
    http_response = Mock()
    http_response.raise_for_status.side_effect = error
    monkeypatch.setattr(
        "chatbot.llm_client.requests.post", Mock(return_value=http_response)
    )

    with pytest.raises(GroqAPIError, match="HTTP 429"):
        query_groq_api("prompt")


def test_timeout_raises_typed_operational_error(monkeypatch):
    monkeypatch.setattr(
        "chatbot.llm_client.requests.post",
        Mock(side_effect=requests.exceptions.Timeout("connection timed out")),
    )

    with pytest.raises(GroqAPIError, match="Timeout"):
        query_groq_api("prompt")


def test_invalid_json_raises_typed_error(monkeypatch):
    response = Mock()
    response.json.side_effect = ValueError("invalid JSON")
    monkeypatch.setattr("chatbot.llm_client.requests.post", Mock(return_value=response))

    with pytest.raises(GroqAPIError, match="invalid JSON"):
        query_groq_api("prompt")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": None}}]},
    ],
)
def test_malformed_or_empty_completion_raises_typed_error(monkeypatch, body):
    response = Mock()
    response.json.return_value = body
    monkeypatch.setattr("chatbot.llm_client.requests.post", Mock(return_value=response))

    with pytest.raises(GroqAPIError, match="model answer"):
        query_groq_api("prompt")
