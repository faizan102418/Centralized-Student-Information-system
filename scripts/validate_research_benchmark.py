"""Validate benchmark expectations against the isolated synthetic MySQL database.

Example:
  DB_NAME=research_eval PYTHONPATH=src uv run python scripts/validate_research_benchmark.py
The script is read-only and writes a JSON audit report unless --output is omitted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "eval" / "synthetic_eval.jsonl"
DEFAULT_OUTPUT = ROOT / "experiments" / "benchmark_validation.json"

FIELD_SQL = {
    "discipline": ("student_general_data", "discipline"),
    "roll_number": ("student_general_data", "roll_number"),
    "scholarship_name": ("student_scholarship", "scholarship_name"),
    "enrollment_status": ("student_scholarship", "enrollment_status"),
    "fee_status": ("student_fee_submission", "fee_status"),
    "registration_number": ("student_fee_submission", "registration_number"),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate(dataset: list[dict[str, Any]], connection) -> dict[str, Any]:
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT student_id, name FROM student_general_data")
    students = {str(row["student_id"]): row["name"] for row in cursor.fetchall()}
    cursor.execute("SELECT student_id, name FROM student_general_data")
    names = [row["name"] for row in cursor.fetchall()]
    results = []
    for case in dataset:
        case_id = case["case_id"]
        category = case["category"]
        student_id = case.get("student_id")
        field = case.get("field")
        status = "valid"
        observed = None
        reason = None

        if category == "ambiguous":
            expected_names = set(case.get("candidate_names", []))
            prefix = str(case["query"]).split("'")[0].split()[-1]
            actual = {name for name in names if str(name).casefold().startswith(prefix.casefold())}
            if len(actual) < 2 or not expected_names.issubset(actual):
                status, reason = "invalid", "expected_ambiguous_candidates_not_in_database"
            observed = sorted(actual)
        else:
            if student_id not in students:
                status, reason = "invalid", "student_id_not_in_database"
            elif field not in FIELD_SQL:
                status, reason = "invalid", "field_not_supported_by_validation_schema"
            else:
                table, column = FIELD_SQL[field]
                cursor.execute(
                    f"SELECT {column} AS value FROM {table} WHERE student_id = %s LIMIT 1",
                    (student_id,),
                )
                row = cursor.fetchone()
                observed = None if row is None else row["value"]
                if category == "answerable":
                    if row is None or observed is None or str(observed).strip() != str(case.get("expected_answer", "")).strip():
                        status, reason = "invalid", "answerable_expected_value_does_not_match_source"
                elif category == "missing":
                    expected_state = case.get("source_state")
                    if expected_state == "null_value":
                        if row is None or observed is not None and str(observed).strip():
                            status, reason = "invalid", "expected_null_source_value_not_found"
                    elif expected_state == "missing_related_record":
                        if row is not None:
                            status, reason = "invalid", "expected_missing_related_record_but_row_exists"
                    else:
                        status, reason = "invalid", "missing_case_has_no_valid_source_state"
        results.append({
            "case_id": case_id,
            "category": category,
            "student_id": student_id,
            "field": field,
            "observed_source_value": observed,
            "validation_status": status,
            "validation_reason": reason,
        })
    cursor.close()
    counts = {}
    for row in results:
        counts[row["validation_status"]] = counts.get(row["validation_status"], 0) + 1
    return {
        "database_validation": True,
        "total_cases": len(results),
        "counts": counts,
        "valid": counts.get("invalid", 0) == 0,
        "cases": results,
        "interpretation": (
            "A valid report confirms labels against the connected database snapshot only. "
            "Record the database dump/hash and schema version with experimental results."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    from chatbot.config import DB_NAME
    from chatbot.database import get_db_connection

    if DB_NAME != "research_eval":
        raise RuntimeError("Refusing to validate against a non-isolated database; set DB_NAME=research_eval.")
    connection = get_db_connection()
    try:
        report = validate(read_jsonl(args.dataset), connection)
    finally:
        connection.close()
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
