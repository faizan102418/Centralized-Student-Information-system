"""Validate benchmark expectations against the isolated research_eval MySQL snapshot.

Run after loading data/seed.sql and data/eval/seed_synthetic_eval.sql:
  DB_NAME=research_eval PYTHONPATH=src uv run python scripts/validate_research_benchmark.py
"""
from __future__ import annotations

import argparse
import json
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "eval" / "synthetic_eval.jsonl"
FIELD_SQL = {
    "discipline": ("SELECT discipline FROM student_general_data WHERE student_id=%s", "discipline"),
    "roll_number": ("SELECT roll_number FROM student_general_data WHERE student_id=%s", "roll_number"),
    "scholarship_name": ("SELECT scholarship_name FROM student_scholarship WHERE student_id=%s", "scholarship_name"),
    "enrollment_status": ("SELECT enrollment_status FROM student_scholarship WHERE student_id=%s", "enrollment_status"),
    "fee_status": ("SELECT fee_status FROM student_fee_submission WHERE student_id=%s", "fee_status"),
    "registration_number": ("SELECT registration_number FROM student_fee_submission WHERE student_id=%s", "registration_number"),
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(cases: list[dict[str, Any]], connection: Any) -> list[dict[str, Any]]:
    cursor = connection.cursor(dictionary=True)
    results = []
    for case in cases:
        status, value, detail = "valid", None, ""
        student_id = case.get("student_id")
        category = case["category"]
        if category == "ambiguous":
            # Bind candidate names as values; do not interpolate input into SQL.
            found = []
            for candidate_name in case["candidate_names"]:
                cursor.execute(
                    "SELECT student_id, name FROM student_general_data WHERE name=%s",
                    (candidate_name,),
                )
                found.extend(row["name"] for row in cursor.fetchall())
            found = sorted(found)
            expected = sorted(case["candidate_names"])
            if found != expected:
                status, detail = "invalid", f"candidate names mismatch: {found}"
            else:
                detail = "all listed candidates exist; clarification is warranted"
        elif category == "missing":
            if case.get("field") != "fee_status":
                status, detail = "invalid", "missing case must target recognized fee_status"
            elif case.get("source_state") == "null_value":
                cursor.execute(
                    "SELECT fee_status FROM student_fee_submission WHERE student_id=%s",
                    (student_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    status, detail = "invalid", "expected a fee-submission row with NULL fee_status, but no row exists"
                elif row["fee_status"] is not None:
                    status, detail = "invalid", f"expected SQL NULL fee_status, found {row['fee_status']!r}"
                else:
                    detail = "fee-submission row exists and fee_status is SQL NULL"
            elif case.get("source_state") == "related_record_absent":
                cursor.execute(
                    "SELECT COUNT(*) AS n FROM student_fee_submission WHERE student_id=%s",
                    (student_id,),
                )
                count = cursor.fetchone()["n"]
                if count != 0:
                    status, detail = "invalid", f"expected no fee-submission row, found {count}"
                else:
                    detail = "student exists and no fee-submission row exists"
            else:
                status, detail = "invalid", f"unsupported missing source_state: {case.get('source_state')!r}"
        elif category == "answerable":
            if case.get("field") not in FIELD_SQL:
                status, detail = "invalid", f"unsupported answerable field: {case.get('field')}"
            else:
                query, key = FIELD_SQL[case["field"]]
                cursor.execute(query, (student_id,))
                row = cursor.fetchone()
                value = row.get(key) if row else None
                expected = str(case.get("expected_answer", "")).strip()
                if value is None or str(value).strip().casefold() != expected.casefold():
                    status, detail = "invalid", f"database value {value!r} != expected {expected!r}"
                else:
                    detail = "database value matches expected answer"
        else:
            status, detail = "invalid", f"unknown category: {category}"
        results.append({
            "case_id": case["case_id"], "category": category, "student_id": student_id,
            "field": case.get("field"), "database_value": value,
            "validation_status": status, "validation_detail": detail,
        })
    cursor.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments" / "benchmark_validation.json")
    args = parser.parse_args()
    cases = load_cases(args.dataset)
    if len(cases) != 200 or len({case["case_id"] for case in cases}) != len(cases):
        raise ValueError("Expected exactly 200 unique benchmark cases.")
    if Counter(case["category"] for case in cases) != {"answerable": 100, "ambiguous": 50, "missing": 50}:
        raise ValueError("Expected 100 answerable, 50 ambiguous, and 50 missing cases.")
    from chatbot.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER
    if DB_NAME != "research_eval":
        raise RuntimeError(f"Refusing to validate against {DB_NAME!r}; DB_NAME must be research_eval.")
    connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    try:
        results = validate(cases, connection)
    finally:
        connection.close()
    summary = {
        "dataset": str(args.dataset.relative_to(ROOT)) if args.dataset.is_relative_to(ROOT) else str(args.dataset),
        "case_count": len(cases),
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "category_counts": dict(Counter(case["category"] for case in cases)),
        "valid_count": sum(row["validation_status"] == "valid" for row in results),
        "invalid_count": sum(row["validation_status"] != "valid" for row in results),
        "cases": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, indent=2))
    return 0 if summary["invalid_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
