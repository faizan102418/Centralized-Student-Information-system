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
    from chatbot import llm_client

    response = Mock()
    response.status_code = 429
    error = requests.exceptions.HTTPError("rate limited", response=response)
    http_response = Mock()
    http_response.raise_for_status.side_effect = error
    post = Mock(return_value=http_response)
    monkeypatch.setattr(llm_client.requests, "post", post)
    monkeypatch.setattr(llm_client.time, "sleep", Mock())

    with pytest.raises(GroqAPIError, match="HTTP 429"):
        query_groq_api("prompt")

    assert post.call_count == llm_client.MAX_ATTEMPTS


def test_timeout_raises_typed_operational_error(monkeypatch):
    from chatbot import llm_client

    post = Mock(side_effect=requests.exceptions.Timeout("connection timed out"))
    monkeypatch.setattr(llm_client.requests, "post", post)
    monkeypatch.setattr(llm_client.time, "sleep", Mock())

    with pytest.raises(GroqAPIError, match="Timeout"):
        query_groq_api("prompt")

    assert post.call_count == llm_client.MAX_ATTEMPTS


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


def test_retries_http_429_then_succeeds(monkeypatch):
    from chatbot import llm_client

    success = Mock()
    success.json.return_value = {
        "choices": [{"message": {"content": "Computer Science"}}]
    }
    rate_limited = Mock()
    rate_limited.status_code = 429
    rate_limit_error = requests.exceptions.HTTPError(
        "rate limited", response=rate_limited
    )
    first_response = Mock()
    first_response.raise_for_status.side_effect = rate_limit_error
    post = Mock(side_effect=[first_response, success])
    sleep = Mock()

    monkeypatch.setattr(llm_client.requests, "post", post)
    monkeypatch.setattr(llm_client.time, "sleep", sleep)

    assert llm_client.query_groq_api("prompt") == "Computer Science"
    assert post.call_count == 2
    sleep.assert_called_once_with(llm_client.RETRY_BACKOFF_SECONDS)


def test_retries_timeout_until_max_attempts(monkeypatch):
    from chatbot import llm_client

    post = Mock(side_effect=requests.exceptions.Timeout("timed out"))
    sleep = Mock()
    monkeypatch.setattr(llm_client.requests, "post", post)
    monkeypatch.setattr(llm_client.time, "sleep", sleep)

    with pytest.raises(GroqAPIError, match="after 3 attempts"):
        llm_client.query_groq_api("prompt")

    assert post.call_count == 3
    assert sleep.call_count == 2


def test_does_not_retry_http_401(monkeypatch):
    from chatbot import llm_client

    unauthorized = Mock()
    unauthorized.status_code = 401
    error = requests.exceptions.HTTPError("unauthorized", response=unauthorized)
    response = Mock()
    response.raise_for_status.side_effect = error
    post = Mock(return_value=response)
    monkeypatch.setattr(llm_client.requests, "post", post)
    monkeypatch.setattr(llm_client.time, "sleep", Mock())

    with pytest.raises(GroqAPIError, match="HTTP 401"):
        llm_client.query_groq_api("prompt")

    post.assert_called_once()
