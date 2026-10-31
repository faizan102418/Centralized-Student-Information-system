"""Thin client for calling the Groq chat completions API."""

import requests

from chatbot.config import GROQ_API_KEY, GROQ_MODEL

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT = (
    "You are an intelligent assistant that extracts and synthesizes "
    "student records from provided text."
)


class GroqAPIError(RuntimeError):
    """Raised when Groq cannot provide a valid model response.

    This is an operational failure, not an answer or an abstention. Callers
    should handle it at the application boundary or let experiment runners
    record and retry the failed case.
    """


def query_groq_api(prompt: str, timeout: int = 30) -> str:
    """Send a prompt to Groq and return model text, or raise GroqAPIError."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        response = requests.post(
            GROQ_API_URL, headers=headers, json=payload, timeout=timeout
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise GroqAPIError(f"Groq API request failed (HTTP {status}).") from exc
    except requests.exceptions.RequestException as exc:
        raise GroqAPIError(
            f"Groq API request failed ({type(exc).__name__})."
        ) from exc

    try:
        body = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError) as exc:
        raise GroqAPIError("Groq API returned invalid JSON.") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GroqAPIError("Groq API response did not contain a model answer.") from exc

    if not isinstance(content, str) or not content.strip():
        raise GroqAPIError("Groq API response contained an empty model answer.")
    return content
