"""Thin client for calling the Groq chat completions API."""

import time

import requests

from chatbot.config import GROQ_API_KEY, GROQ_MODEL

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT = (
    "You are an intelligent assistant that extracts and synthesizes "
    "student records from provided text."
)
MAX_ATTEMPTS = 3
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
RETRY_BACKOFF_SECONDS = 1


class GroqAPIError(RuntimeError):
    """Raised when Groq cannot provide a valid model response.

    This is an operational failure, not an answer or an abstention. Callers
    should handle it at the application boundary or let experiment runners
    record and retry the failed case.
    """


def query_groq_api(prompt: str, timeout: int = 30) -> str:
    """Send a prompt to Groq, retry transient failures, or raise GroqAPIError."""
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

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                GROQ_API_URL, headers=headers, json=payload, timeout=timeout
            )
            response.raise_for_status()
            break
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None

            if status not in RETRYABLE_HTTP_STATUSES:
                raise GroqAPIError(
                    f"Groq API request failed (HTTP {status or 'unknown'})."
                ) from exc

            if attempt == MAX_ATTEMPTS:
                raise GroqAPIError(
                    f"Groq API request failed (HTTP {status}) after "
                    f"{MAX_ATTEMPTS} attempts."
                ) from exc
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as exc:
            if attempt == MAX_ATTEMPTS:
                raise GroqAPIError(
                    f"Groq API request failed ({type(exc).__name__}) after "
                    f"{MAX_ATTEMPTS} attempts."
                ) from exc
        except requests.exceptions.RequestException as exc:
            raise GroqAPIError(
                f"Groq API request failed ({type(exc).__name__})."
            ) from exc

        time.sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))

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
