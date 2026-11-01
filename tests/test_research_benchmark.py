import json
from pathlib import Path

from chatbot.candidate_matcher import match_candidate
from chatbot.evidence_verifier import requested_field

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "eval" / "synthetic_eval.jsonl"


def load_dataset():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]


def test_benchmark_has_expected_stratification():
    rows = load_dataset()
    counts = {category: sum(row["category"] == category for row in rows)
              for category in ("answerable", "ambiguous", "missing")}
    assert len(rows) == 200
    assert counts == {"answerable": 100, "ambiguous": 50, "missing": 50}


def test_every_missing_case_uses_a_recognized_field_and_source_state():
    missing = [row for row in load_dataset() if row["category"] == "missing"]
    assert all(requested_field(row["query"]) == row["field"] for row in missing)
    assert {row["source_state"] for row in missing} == {
        "null_value", "missing_related_record"
    }
    assert all(row["field"] != "cgpa" for row in missing)


def test_ambiguous_cases_match_multiple_synthetic_candidates():
    for row in (item for item in load_dataset() if item["category"] == "ambiguous"):
        prefix = row["candidate_names"][0].split()[0]
        candidates = [{"student_id": str(i), "name": name}
                      for i, name in enumerate(row["candidate_names"])]
        assert match_candidate(prefix, candidates).status == "AMBIGUOUS"


def test_missing_case_groups_are_disjoint_and_use_added_students():
    missing = [row for row in load_dataset() if row["category"] == "missing"]
    discipline_ids = {row["student_id"] for row in missing if row["field"] == "discipline"}
    scholarship_ids = {row["student_id"] for row in missing if row["field"] == "scholarship_name"}
    assert len(discipline_ids) == 5
    assert len(scholarship_ids) == 5
    assert discipline_ids.isdisjoint(scholarship_ids)
