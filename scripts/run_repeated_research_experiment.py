"""Run repeated paired A/B/C experiments; query remains the analysis unit.

Example:
  DB_NAME=research_eval PYTHONPATH=src uv run python scripts/run_repeated_research_experiment.py --repeats 5 --system both
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "eval" / "synthetic_eval.jsonl"
DEFAULT_OUTPUT = ROOT / "experiments" / "repeated_abc"
ERROR_MARKERS = ("could not reach the groq api", "unexpected response from the groq api",
                 "jev verification unavailable", "jev api key is not configured",
                 "student lookup is temporarily unavailable")
CLARIFY_MARKERS = ("multiple possible students", "multiple student names",
                   "please provide the exact full name", "please include the student's full name",
                   "couldn't safely identify one student")
ABSTAIN_MARKERS = ("couldn't verify", "could not verify", "verification:", "not available",
                   "could not be retrieved", "no answer was generated",
                   "haven't retrieved any student data", "couldn't safely confirm",
                   "couldn't find that student", "don't have permission", "please sign in")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected object at {path}:{line_no}")
            rows.append(row)
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def classify(output: str) -> str:
    text = " ".join(output.casefold().split())
    if any(marker in text for marker in ERROR_MARKERS):
        return "error"
    if any(marker in text for marker in CLARIFY_MARKERS):
        return "clarify"
    if any(marker in text for marker in ABSTAIN_MARKERS):
        return "abstain"
    return "answer"


def clean_answer(output: str) -> str:
    cleaned = re.sub(r"[*_]", "", " ".join(output.split())).strip()
    match = re.search(r"\bis\s+(.+)$", cleaned, flags=re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    return cleaned.strip(" \t\r\n.,;:!?")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--system", choices=("A", "B", "C", "all"), default="all")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--disable-jev", action="store_true",
                        help="Run a separately labelled no-Jev ablation; never pool with Jev-enabled runs.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed", type=int, default=20261101)
    args = parser.parse_args()
    if args.repeats < 1:
        raise ValueError("--repeats must be at least one")
    cases = read_jsonl(args.dataset)
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        cases = cases[:args.limit]
    if not cases:
        raise ValueError("No cases selected.")

    from chatbot.auth import get_user
    from chatbot.config import DB_NAME, GROQ_MODEL
    from chatbot.jev_verifier import DEFAULT_THRESHOLD, JEV_MODEL, JevVerifier
    from chatbot.rag_pipeline import answer_question, setup_vector_db

    if DB_NAME != "research_eval":
        raise RuntimeError("Research runner refuses to use a database other than research_eval.")
    if any(case.get("student_id") and not str(case["student_id"]).startswith("SYN-") for case in cases):
        raise RuntimeError("Only synthetic SYN- student IDs are permitted.")
    systems = ("A", "B", "C") if args.system == "all" else (args.system,)
    predictions = {system: args.output_dir / f"system_{system.lower()}_predictions.jsonl" for system in systems}
    raw_paths = {system: args.output_dir / f"system_{system.lower()}_raw.jsonl" for system in systems}
    metadata_path = args.output_dir / "metadata.json"
    dataset_hash = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    case_ids = [case["case_id"] for case in cases]
    validation_path = ROOT / "experiments" / "benchmark_validation.json"
    if not validation_path.exists():
        raise RuntimeError("Run scripts/validate_research_benchmark.py successfully before starting the experiment.")
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if (validation.get("dataset_sha256") != dataset_hash
            or validation.get("invalid_count") != 0
            or validation.get("case_count") != 200):
        raise RuntimeError("Benchmark validation is missing, failed, or belongs to a different dataset.")
    config = {
        "dataset_sha256": dataset_hash,
        "benchmark_validation_sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
        "schema_seed_sha256": hashlib.sha256((ROOT / "data" / "seed.sql").read_bytes()).hexdigest(),
        "synthetic_seed_sha256": hashlib.sha256((ROOT / "data" / "eval" / "seed_synthetic_eval.sql").read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "embedding_model": "sentence-transformers/all-mpnet-base-v2",
        "retrieval_k": 4, "selected_case_ids": case_ids,
        "repeats": args.repeats, "systems": list(systems), "jev_enabled": not args.disable_jev,
        "seed": args.seed, "database_name": DB_NAME, "groq_model": GROQ_MODEL,
        "jev_model": JEV_MODEL if not args.disable_jev else None,
        "jev_threshold": DEFAULT_THRESHOLD if not args.disable_jev else None,
        "conditions": {
            "A": "RAG + local candidate matching + RBAC; no post-generation evidence check",
            "B": "A + deterministic post-generation requested-field evidence verification",
            "C": "B + pre-generation abstention gate when a recognized requested field is absent from retrieved evidence",
        },
        "shared_controls": ["same synthetic DB snapshot", "same local candidate matcher",
                            "same ambiguity clarification", "same RBAC", "same retrieval k and model settings"],
        "analysis_unit": "query; repeated executions are nested observations, not independent samples",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if metadata_path.exists():
        if not args.resume:
            raise FileExistsError(f"{metadata_path} exists; choose a new directory or --resume")
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))
        if previous != config:
            raise ValueError("Resume refused: dataset, conditions, model settings, or run design differ.")
    else:
        metadata_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    completed: dict[str, set[tuple[str, int]]] = {}
    for system in systems:
        path = predictions[system]
        rows = read_jsonl(path) if path.exists() else []
        keys = [(row["case_id"], int(row["run_number"])) for row in rows]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate case_id/run_number rows in {path}")
        completed[system] = set(keys)
    user = get_user("faculty1")
    if not user or user.get("role") not in {"admin", "faculty"}:
        raise RuntimeError("Research identity faculty1 is missing or lacks faculty access.")
    vectorstore = setup_vector_db()
    jev = JevVerifier() if not args.disable_jev else None

    for run_number in range(1, args.repeats + 1):
        order = list(systems)
        random.Random(args.seed + run_number).shuffle(order)
        print(f"Run {run_number}/{args.repeats}; condition order: {','.join(order)}", flush=True)
        for system in order:
            for index, case in enumerate(cases, 1):
                key = (case["case_id"], run_number)
                if key in completed[system]:
                    continue
                started = time.perf_counter()
                calls: list[dict[str, Any]] = []
                diagnostics: list[dict[str, Any]] = []
                class TimedVerifier:
                    def verify(self, *a: Any, **kw: Any) -> Any:
                        t0 = time.perf_counter()
                        result = jev.verify(*a, **kw)
                        calls.append({
                            "model": getattr(result, "model", None),
                            "score": getattr(result, "probability_yes", None),
                            "decision": getattr(result, "decision", None),
                            "reason": str(getattr(result, "reason", "")),
                            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                        })
                        return result
                error_type = None
                try:
                    output = answer_question(
                        vectorstore, case["query"], user=user,
                        verifier=TimedVerifier() if jev else None,
                        evidence_verification=system in {"B", "C"},
                        pre_generation_abstention=system == "C",
                        use_jev=not args.disable_jev,
                        diagnostic_callback=diagnostics.append,
                    )
                    decision = classify(str(output))
                except Exception as exc:
                    error_type = type(exc).__name__
                    output = f"EXPERIMENT_RUNNER_ERROR: {error_type}"
                    decision = "error"
                latency = round((time.perf_counter() - started) * 1000, 2)
                append_jsonl(raw_paths[system], {
                    "case_id": case["case_id"], "run_number": run_number, "system": system,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "raw_output": str(output), "decision": decision, "error_type": error_type,
                    "total_latency_ms": latency, "jev_calls": calls, "diagnostics": diagnostics,
                })
                if decision == "error":
                    raise RuntimeError(f"Stopped at {system}/{case['case_id']}/run-{run_number}; raw output retained.")
                append_jsonl(predictions[system], {
                    "case_id": case["case_id"], "run_number": run_number, "system": system,
                    "decision": decision,
                    "answer": clean_answer(str(output)) if decision == "answer" else "",
                })
                completed[system].add(key)
            print(f"  System {system}: {index}/{len(cases)} cases for run {run_number}", flush=True)
    print(f"Completed repeated experiment. Results: {args.output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
