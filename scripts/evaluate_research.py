"""Evaluate repeated predictions; each query remains the inferential unit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
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


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def evaluate_one_run(dataset: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {row["case_id"]: row for row in dataset}
    actual = {row["case_id"]: row for row in predictions}
    if len(actual) != len(predictions) or set(actual) != set(expected):
        raise ValueError("Each run must contain exactly one prediction for every benchmark case.")
    counts = {
        "total": len(dataset), "decision_correct": 0,
        "answerable": 0, "answerable_answered": 0, "answerable_exact_correct": 0,
        "answerable_unnecessary_nonanswer": 0,
        "ambiguous": 0, "ambiguous_clarified": 0,
        "missing": 0, "missing_abstained": 0,
        "non_answerable": 0, "unsafe_answers_on_non_answerable": 0,
        "correct_nonanswer_on_non_answerable": 0,
        "clarification_true_positive": 0, "clarification_false_positive": 0,
        "clarification_false_negative": 0,
        "abstention_true_positive": 0, "abstention_false_positive": 0,
        "abstention_false_negative": 0,
    }
    for case_id, gold in expected.items():
        pred = actual[case_id]
        decision = pred.get("decision")
        if decision not in {"answer", "clarify", "abstain"}:
            raise ValueError(f"{case_id}: invalid decision {decision!r}")
        counts["decision_correct"] += decision == gold["expected_decision"]
        if gold["category"] == "answerable":
            counts["answerable"] += 1
            if decision == "answer":
                counts["answerable_answered"] += 1
                counts["answerable_exact_correct"] += (
                    normalize(str(pred.get("answer", ""))) ==
                    normalize(str(gold.get("expected_answer", "")))
                )
            else:
                counts["answerable_unnecessary_nonanswer"] += 1
        if gold["category"] == "ambiguous":
            counts["ambiguous"] += 1
            counts["ambiguous_clarified"] += decision == "clarify"
            counts["clarification_true_positive"] += decision == "clarify"
            counts["clarification_false_negative"] += decision != "clarify"
        elif decision == "clarify":
            counts["clarification_false_positive"] += 1
        if gold["category"] in {"ambiguous", "missing"}:
            counts["non_answerable"] += 1
            counts["unsafe_answers_on_non_answerable"] += decision == "answer"
            counts["correct_nonanswer_on_non_answerable"] += decision != "answer"
        if gold["category"] == "missing":
            counts["missing"] += 1
            counts["missing_abstained"] += decision == "abstain"
            counts["abstention_true_positive"] += decision == "abstain"
            counts["abstention_false_negative"] += decision != "abstain"
        elif decision == "abstain":
            counts["abstention_false_positive"] += 1

    latency = [float(row["latency_ms"]) for row in predictions if row.get("latency_ms") is not None]
    c = counts
    precision_clarify = _rate(c["clarification_true_positive"],
                               c["clarification_true_positive"] + c["clarification_false_positive"])
    recall_clarify = _rate(c["clarification_true_positive"],
                            c["clarification_true_positive"] + c["clarification_false_negative"])
    precision_abstain = _rate(c["abstention_true_positive"],
                               c["abstention_true_positive"] + c["abstention_false_positive"])
    recall_abstain = _rate(c["abstention_true_positive"],
                            c["abstention_true_positive"] + c["abstention_false_negative"])
    return {
        "counts": counts,
        "metrics": {
            "decision_accuracy": _rate(c["decision_correct"], c["total"]),
            "answer_coverage_on_answerable": _rate(c["answerable_answered"], c["answerable"]),
            "exact_answer_accuracy_when_answered": _rate(c["answerable_exact_correct"], c["answerable_answered"]),
            "correct_answer_rate_on_all_answerable": _rate(c["answerable_exact_correct"], c["answerable"]),
            "unnecessary_nonanswer_rate_on_answerable": _rate(c["answerable_unnecessary_nonanswer"], c["answerable"]),
            "unsafe_answer_rate_on_non_answerable": _rate(c["unsafe_answers_on_non_answerable"], c["non_answerable"]),
            "correct_nonanswer_rate_on_non_answerable": _rate(c["correct_nonanswer_on_non_answerable"], c["non_answerable"]),
            "clarification_precision": precision_clarify,
            "clarification_recall": recall_clarify,
            "missing_abstention_precision": precision_abstain,
            "missing_abstention_recall": recall_abstain,
            "median_latency_ms": round(statistics.median(latency), 2) if latency else None,
        },
    }


def evaluate(dataset: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    runs: dict[int, list[dict[str, Any]]] = {}
    seen = set()
    for row in predictions:
        run_number = int(row.get("run_number", 1))
        key = (row["case_id"], run_number)
        if key in seen:
            raise ValueError(f"Duplicate case/run key: {key}")
        seen.add(key)
        runs.setdefault(run_number, []).append(row)
    if not runs:
        raise ValueError("No predictions supplied.")
    per_run = {str(number): evaluate_one_run(dataset, rows)
               for number, rows in sorted(runs.items())}
    metric_names = list(next(iter(per_run.values()))["metrics"])
    summary = {}
    for metric in metric_names:
        values = [result["metrics"][metric] for result in per_run.values()
                  if result["metrics"][metric] is not None]
        summary[metric] = {
            "mean_across_runs": round(statistics.mean(values), 4) if values else None,
            "sd_across_runs": round(statistics.stdev(values), 4) if len(values) > 1 else None,
            "n_runs": len(values),
        }
    return {
        "n_runs": len(per_run),
        "n_queries": len(dataset),
        "n_attempts": len(predictions),
        "per_run": per_run,
        "summary": summary,
        "notes": [
            "Repeated attempts are nested within queries; do not treat n_attempts as independent observations.",
            "The standard deviation describes run-to-run variability, not uncertainty across a population of queries.",
            "Exact answer matching is conservative; manually adjudicate semantically equivalent paraphrases.",
            "Evidence faithfulness is not automatically scored here; use the human-validation protocol.",
            "Report operational errors separately; do not relabel them as abstentions.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--predictions", type=Path, nargs="+", required=True,
                        help="One or more per-run prediction JSONL files.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    predictions = [row for path in args.predictions for row in read_jsonl(path)]
    result = evaluate(read_jsonl(args.dataset), predictions)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
