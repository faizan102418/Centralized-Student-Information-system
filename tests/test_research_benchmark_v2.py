import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chatbot.rag_pipeline import extract_student_name


def test_v2_benchmark_has_three_balanced_categories_and_real_missing_field_cases():
    path = ROOT / "data" / "eval" / "synthetic_eval.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    counts = {
        category: sum(row["category"] == category for row in rows)
        for category in ("answerable", "ambiguous", "missing")
    }

    assert len(rows) == 200
    assert counts == {"answerable": 100, "ambiguous": 50, "missing": 50}

    missing = [row for row in rows if row["category"] == "missing"]
    assert all(row["field"] == "fee_status" for row in missing)
    assert Counter(row["source_state"] for row in missing) == {
        "null_value": 25,
        "related_record_absent": 25,
    }
    assert all(row["database_table"] == "student_fee_submission" for row in missing)
    assert len({row["student_id"] for row in missing}) == 20

    null_value_ids = {
        row["student_id"]
        for row in missing
        if row["source_state"] == "null_value"
    }
    absent_record_ids = {
        row["student_id"]
        for row in missing
        if row["source_state"] == "related_record_absent"
    }

    assert len(null_value_ids) == 10
    assert len(absent_record_ids) == 10
    assert null_value_ids.isdisjoint(absent_record_ids)


def test_all_v2_queries_are_parseable_by_the_student_name_extractor():
    path = ROOT / "data" / "eval" / "synthetic_eval.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert all(extract_student_name(row["query"]) for row in rows)
