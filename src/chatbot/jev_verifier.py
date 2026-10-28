"""Fail-closed client for the Jev AI candidate-resolution signal.

A high score is not identity proof and never grants authorization. This client
sends only the query and names needed for resolution, never student records.
"""
from dataclasses import dataclass
import os
from typing import Any

import requests

JEV_ENDPOINT = "https://jev-ai.pro/api/v1/systemone"
JEV_MODEL = os.getenv("JEV_MODEL", "jev-latest")
DEFAULT_THRESHOLD = 0.80
TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class VerificationResult:
    probability_yes: float | None
    decision: str
    reason: str
    model: str = JEV_MODEL


def _find_noul(value: Any) -> float | None:
    """Find a numeric 'noul' field in common response envelopes."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() == "noul" and isinstance(item, (int, float)) and not isinstance(item, bool):
                return float(item)
        for item in value.values():
            found = _find_noul(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_noul(item)
            if found is not None:
                return found
    return None


class JevVerifier:
    """Request a provisional candidate-resolution score from Jev AI."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key if api_key is not None else os.getenv("JEV_AI_API_KEY")
        self.model = model or JEV_MODEL

    def verify(
        self,
        query: str,
        candidate: str,
        database_candidates: list[str],
        threshold: float = DEFAULT_THRESHOLD,
    ) -> VerificationResult:
        if not self.api_key:
            return VerificationResult(None, "ABSTAIN", "Jev API key is not configured.", self.model)
        if not query.strip() or not candidate.strip():
            return VerificationResult(None, "ABSTAIN", "Query or candidate is empty.", self.model)
        if not 0.0 <= threshold <= 1.0:
            return VerificationResult(None, "ABSTAIN", "Threshold must be between 0 and 1.", self.model)

        payload = {
            "model": self.model,
            "state": {
                "user_query": query,
                "selected_candidate": candidate,
                "candidate_names": database_candidates,
            },
            "questions": {
                "candidate_match": {
                    "type": "noul",
                    "instructions": (
                        "Estimate whether the user query refers to the selected candidate name. "
                        "Use only the supplied query and names. Return a numeric noul score from "
                        "0 to 1. This is a text-resolution signal, not identity verification."
                    ),
                }
            },
        }
        try:
            response = requests.post(
                JEV_ENDPOINT,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            score = _find_noul(response.json())
            if score is None or not 0.0 <= score <= 1.0:
                return VerificationResult(None, "ABSTAIN", "Missing or invalid Jev score.", self.model)
        except (requests.RequestException, ValueError, TypeError) as exc:
            # Avoid leaking request details, response bodies, or secrets in UI errors.
            return VerificationResult(None, "ABSTAIN", f"Jev verification unavailable ({type(exc).__name__}).", self.model)

        if score >= threshold:
            return VerificationResult(
                score,
                "ACCEPT",
                "Provisional text-resolution signal only; not identity proof or authorization.",
                self.model,
            )
        return VerificationResult(
            score,
            "ABSTAIN",
            "Jev score is below the configured threshold.",
            self.model,
        )
