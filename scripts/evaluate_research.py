"""Evaluate saved System A/System B predictions against the frozen synthetic benchmark.

No model or database calls are made. Example:
  uv run python scripts/evaluate_research.py --predictions experiments/results/system_a.jsonl
"""
import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "eval" / "synthetic_eval.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on {path}:{line_number}: {exc}") from exc
    return rows


def normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def evaluate(dataset: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    expected_ids = [row["case_id"] for row in dataset]
    predicted_ids = [row["case_id"] for row in predictions]
    if len(expected_ids) != len(set(expected_ids)) or len(predicted_ids) != len(set(predicted_ids)):
        raise ValueError("case_id values must be unique in both files.")
    if set(expected_ids) != set(predicted_ids):
        raise ValueError("Prediction case IDs do not match the benchmark case IDs.")
    by_id = {row["case_id"]: row for row in predictions}
    c = {key: 0 for key in (
        "total", "decision_correct", "answerable", "answerable_answered",
        "answerable_exact_correct", "answerable_unnecessary_nonanswer",
        "non_answerable", "non_answerable_correct_nonanswer",
        "unsafe_answers_on_non_answerable", "ambiguous", "ambiguous_clarified",
        "missing", "missing_abstained"
    )}
    c["total"] = len(dataset)
    for expected in dataset:
        actual = by_id[expected["case_id"]]
        decision = actual.get("decision")
        if decision not in {"answer", "clarify", "abstain"}:
            raise ValueError(f"{expected['case_id']}: invalid decision {decision!r}")
        c["decision_correct"] += decision == expected["expected_decision"]
        if expected["category"] == "answerable":
            c["answerable"] += 1
            if decision == "answer":
                c["answerable_answered"] += 1
                c["answerable_exact_correct"] += normalize(str(actual.get("answer", ""))) == normalize(str(expected.get("expected_answer", "")))
            else:
                c["answerable_unnecessary_nonanswer"] += 1
        else:
            c["non_answerable"] += 1
            if decision == "answer":
                c["unsafe_answers_on_non_answerable"] += 1
            else:
                c["non_answerable_correct_nonanswer"] += 1
        if expected["category"] == "ambiguous":
            c["ambiguous"] += 1
            c["ambiguous_clarified"] += decision == "clarify"
        if expected["category"] == "missing":
            c["missing"] += 1
            c["missing_abstained"] += decision == "abstain"

    def rate(n: int, d: int) -> float | None:
        return round(n / d, 4) if d else None

    return {
        "counts": c,
        "metrics": {
            "decision_accuracy": rate(c["decision_correct"], c["total"]),
            "answer_coverage_on_answerable": rate(c["answerable_answered"], c["answerable"]),
            "exact_answer_accuracy_when_answered": rate(c["answerable_exact_correct"], c["answerable_answered"]),
            "correct_answer_rate_on_all_answerable": rate(c["answerable_exact_correct"], c["answerable"]),
            "unnecessary_nonanswer_rate_on_answerable": rate(c["answerable_unnecessary_nonanswer"], c["answerable"]),
            "correct_nonanswer_rate_on_non_answerable": rate(c["non_answerable_correct_nonanswer"], c["non_answerable"]),
            "unsafe_answer_rate_on_non_answerable": rate(c["unsafe_answers_on_non_answerable"], c["non_answerable"]),
            "ambiguous_clarification_rate": rate(c["ambiguous_clarified"], c["ambiguous"]),
            "missing_information_abstention_rate": rate(c["missing_abstained"], c["missing"]),
        },
        "notes": [
            "Exact matching is conservative; manually adjudicate semantic paraphrases.",
            "This scores expected decisions and answers, not general semantic faithfulness.",
            "Always report counts and denominators alongside rates."
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(read_jsonl(args.dataset), read_jsonl(args.predictions))
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
