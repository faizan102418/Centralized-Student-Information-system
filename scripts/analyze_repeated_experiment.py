"""Paired, query-level bootstrap comparisons for repeated A/B/C runs.

Example:
  uv run python scripts/analyze_repeated_experiment.py --results-dir experiments/results
Bootstrap resampling is stratified by benchmark category and samples queries,
retaining all repeated observations for each sampled query.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import statistics
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "eval" / "synthetic_eval.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def load_system(results_dir: Path, system: str) -> dict[str, list[dict[str, Any]]]:
    files = sorted(results_dir.glob(f"system_{system.lower()}_run_*_predictions.jsonl"))
    if not files:
        raise FileNotFoundError(f"No repeated prediction files found for System {system} in {results_dir}")
    rows: dict[str, list[dict[str, Any]]] = {}
    seen = set()
    for path in files:
        for row in read_jsonl(path):
            key = (row["case_id"], int(row.get("run_number", 1)))
            if key in seen:
                raise ValueError(f"{system}: duplicate case/run output {key}")
            seen.add(key)
            rows.setdefault(row["case_id"], []).append(row)
    run_counts = {len(attempts) for attempts in rows.values()}
    if len(run_counts) != 1:
        raise ValueError(f"{system}: queries do not all have the same number of repeated runs")
    return rows


def query_outcomes(dataset: list[dict[str, Any]], by_system: dict[str, dict[str, list[dict[str, Any]]]]) -> dict[str, dict[str, dict[str, float]]]:
    outcomes = {}
    for gold in dataset:
        cid = gold["case_id"]
        outcomes[cid] = {}
        for system, rows_by_case in by_system.items():
            attempts = rows_by_case.get(cid, [])
            if not attempts:
                raise ValueError(f"{system}: missing attempts for {cid}")
            decisions_correct = []
            answer_correct = []
            for row in attempts:
                decisions_correct.append(float(row.get("decision") == gold["expected_decision"]))
                if gold["category"] == "answerable":
                    answer_correct.append(float(
                        row.get("decision") == "answer" and
                        norm(row.get("answer")) == norm(gold.get("expected_answer"))
                    ))
            latencies = [float(row["latency_ms"]) for row in attempts if row.get("latency_ms") is not None]
            outcomes[cid][system] = {
                "decision_correct": statistics.mean(decisions_correct),
                "answer_correct": statistics.mean(answer_correct) if answer_correct else 0.0,
                "latency_ms": statistics.median(latencies) if latencies else float("nan"),
            }
    return outcomes


def stratified_bootstrap(values: dict[str, float], categories: dict[str, str],
                         samples: int, seed: int) -> dict[str, float]:
    rng = random.Random(seed)
    grouped: dict[str, list[str]] = {}
    for case_id, category in categories.items():
        if case_id in values:
            grouped.setdefault(category, []).append(case_id)
    estimates = []
    for _ in range(samples):
        sampled_ids = []
        for ids in grouped.values():
            sampled_ids.extend(rng.choices(ids, k=len(ids)))
        estimates.append(statistics.mean(values[cid] for cid in sampled_ids))
    estimates.sort()
    low = estimates[int(0.025 * (samples - 1))]
    high = estimates[int(0.975 * (samples - 1))]
    return {
        "mean_difference": round(statistics.mean(values.values()), 4),
        "ci95_low": round(low, 4),
        "ci95_high": round(high, 4),
        "n_queries": len(values),
        "bootstrap_samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "experiments" / "results")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    if args.bootstrap_samples < 100:
        raise ValueError("--bootstrap-samples must be at least 100")
    dataset = read_jsonl(args.dataset)
    systems = {name: load_system(args.results_dir, name) for name in ("A", "B", "C")}
    run_counts = {system: min(len(rows) for rows in by_case.values())
                  for system, by_case in systems.items()}
    if len(set(run_counts.values())) != 1:
        raise ValueError(f"Systems have different repeat counts: {run_counts}")
    outcomes = query_outcomes(dataset, systems)
    categories = {row["case_id"]: row["category"] for row in dataset}
    comparisons = {}
    for left, right in (("A", "B"), ("B", "C"), ("A", "C")):
        comparisons[f"{left}-{right}"] = {}
        for metric in ("decision_correct", "answer_correct", "latency_ms"):
            selected = {
                cid: outcomes[cid][right][metric] - outcomes[cid][left][metric]
                for cid in outcomes
                if metric != "answer_correct" or categories[cid] == "answerable"
            }
            if metric == "latency_ms":
                selected = {cid: value for cid, value in selected.items() if value == value}
            comparisons[f"{left}-{right}"][metric] = stratified_bootstrap(
                selected, categories, args.bootstrap_samples, args.seed
            )
    report = {
        "inferential_unit": "query/case_id",
        "repeated_runs_per_query": run_counts,
        "comparisons": comparisons,
        "interpretation": [
            "Differences are right minus left; positive latency means the right-hand system is slower.",
            "Confidence intervals use a paired, category-stratified bootstrap over queries.",
            "Repeated runs are averaged within query before resampling; attempts are not treated as independent.",
            "These intervals do not replace human adjudication of answer semantics or evidence support.",
            "Do not infer causality beyond the specified system interventions and controlled setup.",
        ],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
