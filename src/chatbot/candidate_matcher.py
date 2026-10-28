"""Deterministic matching for names extracted from student queries.

This module deliberately abstains on partial names that could refer to more
than one record. An LLM score is never used to break an ambiguous match.
"""
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class CandidateMatch:
    status: str
    candidate: dict | None = None
    matches: tuple[dict, ...] = ()


def normalize_name(value: str) -> str:
    """Normalize case, accents, punctuation, and whitespace for comparison."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^\w\s]", " ", value.casefold())
    return " ".join(value.split())


def match_candidate(query_name: str, candidates: list[dict]) -> CandidateMatch:
    """Match a query name against {'student_id', 'name'} records.

    A query is considered a possible match when it equals a canonical name or
    is a complete leading phrase of it. More than one possible record is
    ambiguous, including an exact name plus a longer name (e.g. David Miller
    and David Miller Jr).
    """
    query = normalize_name(query_name)
    if not query:
        return CandidateMatch("NO_MATCH")

    possible = []
    for candidate in candidates:
        name = normalize_name(str(candidate.get("name") or ""))
        if name and (name == query or name.startswith(query + " ")):
            possible.append(candidate)

    if not possible:
        return CandidateMatch("NO_MATCH")
    if len(possible) > 1:
        return CandidateMatch("AMBIGUOUS", matches=tuple(possible))
    return CandidateMatch("MATCH", candidate=possible[0], matches=tuple(possible))
