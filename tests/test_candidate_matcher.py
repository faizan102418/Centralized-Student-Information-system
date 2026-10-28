import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatbot.candidate_matcher import match_candidate, normalize_name

CANDIDATES = [
    {"student_id": "1", "name": "John Smith"},
    {"student_id": "2", "name": "Alice Smith"},
    {"student_id": "3", "name": "Alice Johnson"},
    {"student_id": "4", "name": "David Miller"},
    {"student_id": "5", "name": "David Miller Jr"},
]


def test_normalizes_case_punctuation_and_whitespace():
    assert normalize_name("  ALICE-SMITH ") == "alice smith"


def test_unique_full_name_matches():
    result = match_candidate("john smith", CANDIDATES)
    assert result.status == "MATCH"
    assert result.candidate["student_id"] == "1"


def test_partial_name_with_multiple_candidates_is_ambiguous():
    result = match_candidate("Alice", CANDIDATES)
    assert result.status == "AMBIGUOUS"
    assert {candidate["name"] for candidate in result.matches} == {"Alice Smith", "Alice Johnson"}


def test_exact_name_and_longer_name_is_ambiguous():
    assert match_candidate("David Miller", CANDIDATES).status == "AMBIGUOUS"


def test_unknown_and_empty_names_do_not_match():
    assert match_candidate("Unknown Person", CANDIDATES).status == "NO_MATCH"
    assert match_candidate("", CANDIDATES).status == "NO_MATCH"
