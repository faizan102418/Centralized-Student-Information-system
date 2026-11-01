"""Summarize repeated A/B/C outputs at query level (not run level).

  uv run python scripts/evaluate_repeated_research.py --predictions-dir experiments/repeated_abc
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "eval" / "synthetic_eval.jsonl"
SYSTEMS = ("A", "B", "C")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rate(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def majority(values: list[str]) -> str:
    counts = Counter(values)
    highest = max(counts.values())
    winners = {value for value, count in counts.items() if count == highest}
    # Conservative tie-break: abstain > clarify > answer.
    for choice in ("abstain", "clarify", "answer"):
        if choice in winners:
            return choice
    return "error"


def query_level(dataset: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in predictions:
        by_case[row["case_id"]].append(row)
    result = {}
    for case in dataset:
        rows = by_case.get(case["case_id"], [])
        if not rows:
            raise ValueError(f"Missing predictions for {case['case_id']}")
        decisions = [row["decision"] for row in rows]
        decision = majority(decisions)
        answer_values = [str(row.get("answer", "")).strip() for row in rows if row["decision"] == "answer"]
        answer = Counter(answer_values).most_common(1)[0][0] if answer_values else ""
        latencies = [float(row["total_latency_ms"]) for row in rows if row.get("total_latency_ms") is not None]
        result[case["case_id"]] = {
            **case, "decision": decision, "answer": answer,
            "run_count": len(rows), "latency_median_ms": statistics.median(latencies) if latencies else None,
            "decision_consistency": round(max(Counter(decisions).values()) / len(decisions), 4),
        }
    return result


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    decision_correct = sum(row["decision"] == row["expected_decision"] for row in rows)
    answerable = [row for row in rows if row["category"] == "answerable"]
    ambiguous = [row for row in rows if row["category"] == "ambiguous"]
    missing = [row for row in rows if row["category"] == "missing"]
    answered = [row for row in answerable if row["decision"] == "answer"]
    exact = sum(" ".join(row["answer"].casefold().split()) ==
                " ".join(str(row.get("expected_answer", "")).casefold().split()) for row in answered)
    clarify_tp = sum(row["decision"] == "clarify" and row["expected_decision"] == "clarify" for row in rows)
    clarify_fp = sum(row["decision"] == "clarify" and row["expected_decision"] != "clarify" for row in rows)
    clarify_fn = sum(row["decision"] != "clarify" and row["expected_decision"] == "clarify" for row in rows)
    abstain_tp = sum(row["decision"] == "abstain" and row["expected_decision"] == "abstain" for row in rows)
    abstain_fp = sum(row["decision"] == "abstain" and row["expected_decision"] != "abstain" for row in rows)
    abstain_fn = sum(row["decision"] != "abstain" and row["expected_decision"] == "abstain" for row in rows)
    latencies = [row["latency_median_ms"] for row in rows if row["latency_median_ms"] is not None]
    return {
        "query_count": n,
        "decision_accuracy": rate(decision_correct, n),
        "answer_coverage_on_answerable": rate(len(answered), len(answerable)),
        "exact_answer_accuracy_when_answered": rate(exact, len(answered)),
        "correct_answer_rate_on_all_answerable": rate(exact, len(answerable)),
        "unsafe_answer_rate_on_non_answerable": rate(sum(row["decision"] == "answer" for row in rows if row["category"] != "answerable"), len(ambiguous) + len(missing)),
        "clarification_precision": rate(clarify_tp, clarify_tp + clarify_fp),
        "clarification_recall": rate(clarify_tp, clarify_tp + clarify_fn),
        "missing_abstention_precision": rate(abstain_tp, abstain_tp + abstain_fp),
        "missing_abstention_recall": rate(abstain_tp, abstain_tp + abstain_fn),
        "missing_abstention_rate": rate(sum(row["decision"] == "abstain" for row in missing), len(missing)),
        "median_of_query_median_latency_ms": round(statistics.median(latencies), 2) if latencies else None,
        "mean_query_median_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
        "mean_decision_consistency": round(statistics.mean(row["decision_consistency"] for row in rows), 4),
    }


def bootstrap_difference(left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]],
                         seed: int = 2026, samples: int = 4000, confidence_level: float = 0.9833333333) -> dict[str, float]:
    ids = sorted(set(left) & set(right))
    deltas = [int(left[key]["decision"] == left[key]["expected_decision"]) -
              int(right[key]["decision"] == right[key]["expected_decision"]) for key in ids]
    if not deltas:
        raise ValueError("No paired queries for bootstrap.")
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        draw = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        estimates.append(sum(draw) / len(draw))
    estimates.sort()
    tail = (1.0 - confidence_level) / 2.0
    low = max(0, min(samples - 1, int(tail * samples)))
    high = max(0, min(samples - 1, int((1.0 - tail) * samples) - 1))
    return {
        "observed_accuracy_difference": round(statistics.mean(deltas), 4),
        "bonferroni_adjusted_bootstrap_ci_low": round(estimates[low], 4),
        "bonferroni_adjusted_bootstrap_ci_high": round(estimates[high], 4),
        "familywise_confidence_level": round(confidence_level, 4),
        "bootstrap_samples": samples,
        "query_resamples": len(ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--predictions-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dataset = read_jsonl(args.dataset)
    aggregate = {}
    attempt_summaries = {}
    for system in SYSTEMS:
        path = args.predictions_dir / f"system_{system.lower()}_predictions.jsonl"
        if not path.exists():
            continue
        attempts = read_jsonl(path)
        keys = [(row["case_id"], int(row["run_number"])) for row in attempts]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate case_id/run_number rows in {path}")
        if any(row.get("system") != system for row in attempts):
            raise ValueError(f"System labels in {path} do not match {system}")
        by_case = defaultdict(list)
        for row in attempts:
            by_case[row["case_id"]].append(row)
        for case_id, rows in by_case.items():
            run_numbers = {int(row["run_number"]) for row in rows}
            if len(run_numbers) != len(rows):
                raise ValueError(f"Duplicate run numbers for {system}/{case_id}")
        # Join raw latency logs by (case_id, run_number), retaining all attempts.
        raw_path = args.predictions_dir / f"system_{system.lower()}_raw.jsonl"
        raw = read_jsonl(raw_path) if raw_path.exists() else []
        latency = {(row["case_id"], int(row["run_number"])): row.get("total_latency_ms") for row in raw}
        for row in attempts:
            row["total_latency_ms"] = latency.get((row["case_id"], int(row["run_number"])))
        expected_ids = {row["case_id"] for row in dataset}
        if set(by_case) != expected_ids:
            raise ValueError(f"{system}: predictions do not cover exactly the selected benchmark cases.")
        run_counts = {len(rows) for rows in by_case.values()}
        if len(run_counts) != 1:
            raise ValueError(f"{system}: inconsistent repeat counts across queries.")
        aggregate[system] = query_level(dataset, attempts)
        attempt_summaries[system] = {"attempt_count": len(attempts), "repeats_per_query": next(iter(run_counts))}
    report = {
        "analysis_unit": "query; repeated attempts are nested within query",
        "query_level_aggregation": "majority decision across runs; conservative tie-break abstain > clarify > answer; modal answer among answer decisions",
        "attempts": attempt_summaries,
        "systems": {system: metrics(list(rows.values())) for system, rows in aggregate.items()},
        "paired_query_bootstrap_decision_accuracy_differences": {},
        "multiple_comparison_adjustment": "Bonferroni-adjusted 98.33% intervals for the three planned pairwise contrasts (A-B, B-C, C-A).",
        "limitations": [
            "This evaluator does not score evidence faithfulness; use the human-validation protocol.",
            "Majority aggregation is the primary query-level summary; also report run-level variability and decision consistency.",
            "Bootstrap resamples queries, retaining paired system outcomes; do not treat repeated attempts as independent sample units.",
            "Latency summaries are descriptive and use each query's median across its repeats.",
        ],
    }
    for left, right in (("B", "A"), ("C", "B"), ("C", "A")):
        if left in aggregate and right in aggregate:
            report["paired_query_bootstrap_decision_accuracy_differences"][f"{left}_minus_{right}"] = bootstrap_difference(
                aggregate[left], aggregate[right], seed=2026 + ord(left) + ord(right)
            )
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
