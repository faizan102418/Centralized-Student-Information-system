"""Run paired System A/System B evaluations on the frozen synthetic benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "eval" / "synthetic_eval.jsonl"
DEFAULT_OUTPUT_DIR = ROOT / "experiments" / "results"

ERROR_MARKERS = (
    "could not reach the groq api", "unexpected response from the groq api",
    "jev verification unavailable", "jev api key is not configured",
    "missing or invalid jev score", "threshold must be between",
    "student lookup is temporarily unavailable",
)
CLARIFY_MARKERS = (
    "multiple possible students", "multiple student names",
    "couldn't safely identify one student", "please provide the exact full name",
    "please include the student's full name",
)
ABSTAIN_MARKERS = (
    "couldn't verify the requested answer", "verification:",
    "not available in the provided record", "could not be retrieved",
    "no answer was generated", "haven't retrieved any student data",
    "couldn't safely confirm which record", "couldn't find that student",
    "don't have permission", "please sign in",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on {path}:{line_number}: {exc}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"Expected JSON object on {path}:{line_number}")
                rows.append(row)
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def classify_output(output: str) -> str:
    """Classify observable response text, not hidden model reasoning."""
    text = " ".join(output.casefold().split())
    if any(marker in text for marker in ERROR_MARKERS):
        return "error"
    if any(marker in text for marker in CLARIFY_MARKERS):
        return "clarify"
    if any(marker in text for marker in ABSTAIN_MARKERS):
        return "abstain"
    return "answer"


def scoring_answer(output: str) -> str:
    """Strip common answer framing; preserve the untouched response in the raw log."""
    cleaned = re.sub(r"[*_]", "", output)
    cleaned = " ".join(cleaned.split()).strip()
    match = re.search(r"\bis\s+(.+)$", cleaned, flags=re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    return cleaned.strip(" \t\r\n.,;:!?")


def select_cases(dataset: list[dict[str, Any]], limit: int | None = None,
                 pilot: bool = False) -> list[dict[str, Any]]:
    if limit is not None and pilot:
        raise ValueError("--limit and --pilot cannot be used together")
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be at least 1")
        return dataset[:limit]
    if not pilot:
        return dataset
    selected = []
    for category in ("answerable", "ambiguous", "missing"):
        matches = [row for row in dataset if row.get("category") == category]
        if len(matches) < 2:
            raise ValueError(f"Pilot requires at least two {category} cases")
        selected.extend(matches[:2])
    return selected


class TimedJevVerifier:
    """Adapter recording Jev latency, score, decision and reason."""

    def __init__(self, verifier: Any):
        self.verifier = verifier
        self.calls: list[dict[str, Any]] = []

    def verify(self, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        result = self.verifier.verify(*args, **kwargs)
        reason = str(getattr(result, "reason", ""))
        self.calls.append({
            "jev_model": getattr(result, "model", None),
            "jev_score": getattr(result, "probability_yes", None),
            "jev_decision": getattr(result, "decision", None),
            "jev_reason": reason,
            "jev_latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "jev_call_error": any(word in reason.casefold() for word in
                                  ("unavailable", "not configured", "missing or invalid",
                                   "threshold must")),
        })
        return result


def paths_for(output_dir: Path, system: str) -> tuple[Path, Path]:
    suffix = system.lower()
    return (output_dir / f"system_{suffix}_predictions.jsonl",
            output_dir / f"system_{suffix}_raw.jsonl")


def run_condition(system: str, cases: list[dict[str, Any]], output_dir: Path,
                  vectorstore: Any, user: dict[str, Any], answer_fn: Callable[..., str],
                  jev_verifier: Any, resume: bool = False, use_jev: bool = True) -> None:
    predictions_path, raw_path = paths_for(output_dir, system)
    if not resume and (predictions_path.exists() or raw_path.exists()):
        raise FileExistsError(f"Output exists for System {system}; use a new directory or --resume.")
    completed = set()
    if resume and predictions_path.exists():
        existing = read_jsonl(predictions_path)
        completed = {row["case_id"] for row in existing}
        if len(completed) != len(existing):
            raise ValueError(f"Duplicate case IDs in {predictions_path}")
    if not completed.issubset({row["case_id"] for row in cases}):
        raise ValueError("Existing predictions contain case IDs outside this selected run.")

    diagnostics_path = output_dir / "system_b_diagnostics.jsonl"
    timed = TimedJevVerifier(jev_verifier)
    for index, case in enumerate(cases, start=1):
        case_id = case["case_id"]
        if case_id in completed:
            continue
        timed.calls.clear()
        started = time.perf_counter()
        case_diagnostics: list[dict[str, Any]] = []
        diagnostic_callback = case_diagnostics.append if system == "B" else None
        try:
            output = answer_fn(vectorstore, case["query"], user=user, verifier=timed,
                               evidence_verification=(system == "B"), use_jev=use_jev,
                               diagnostic_callback=diagnostic_callback)
        except Exception as exc:
            output = f"EXPERIMENT_RUNNER_ERROR: {type(exc).__name__}"
        latency = round((time.perf_counter() - started) * 1000, 2)
        decision = classify_output(str(output))
        append_jsonl(raw_path, {
            "case_id": case_id, "system": system,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "raw_output": str(output), "decision": decision,
            "total_latency_ms": latency, "jev_calls": list(timed.calls),
        })
        if decision == "error" or str(output).startswith("EXPERIMENT_RUNNER_ERROR:"):
            raise RuntimeError(
                f"Stopped at {case_id} in System {system}; error is in {raw_path}. "
                "Fix the issue and rerun with --resume."
            )
        answer = scoring_answer(str(output)) if decision == "answer" else ""
        append_jsonl(predictions_path, {
            "case_id": case_id, "decision": decision, "answer": answer,
        })
        if case_diagnostics:
            append_jsonl(diagnostics_path, {
                "case_id": case_id, "system": system, **case_diagnostics[-1],
            })
        print(f"[System {system}] {index}/{len(cases)} {case_id}: {decision} "
              f"({latency} ms; Jev calls: {len(timed.calls)})", flush=True)


def write_metadata(path: Path, dataset_path: Path, cases: list[dict[str, Any]],
                   groq_model: str, jev_model: str, threshold: float, db_name: str,
                   use_jev: bool = True) -> None:
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "selected_case_ids": [row["case_id"] for row in cases],
        "groq_model": groq_model,
        "jev_enabled": use_jev,
        "jev_model": jev_model if use_jev else None,
        "jev_threshold": threshold if use_jev else None,
        "embedding_model": "sentence-transformers/all-mpnet-base-v2",
        "retrieval_k": 4, "database_name": db_name,
        "conditions": ({
            "A": "RAG + local candidate matching; Jev enabled; evidence_verification=False",
            "B": "RAG + local candidate matching; Jev enabled; evidence_verification=True",
        } if use_jev else {
            "A": "RAG + local candidate matching; Jev disabled; evidence_verification=False",
            "B": "RAG + local candidate matching; Jev disabled; evidence_verification=True",
        }),
        "jev_score_note": "Recorded as jev_score; not asserted to be calibrated probability.",
        "diagnostics_schema_version": 1,
    }
    path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--system", choices=("A", "B", "both"), default="both")
    parser.add_argument("--limit", type=int, help="Run the first N cases.")
    parser.add_argument("--pilot", action="store_true",
                        help="Run two cases per category (six total).")
    parser.add_argument("--resume", action="store_true",
                        help="Skip case IDs already saved successfully.")
    parser.add_argument("--disable-jev", action="store_true",
                        help="Run a separately labelled no-Jev ablation; local matching and RBAC remain enabled.")
    args = parser.parse_args()

    dataset = read_jsonl(args.dataset)
    cases = select_cases(dataset, args.limit, args.pilot)
    if not cases:
        raise ValueError("No benchmark cases selected.")

    from chatbot.auth import get_user
    from chatbot.config import DB_NAME, GROQ_MODEL
    from chatbot.jev_verifier import DEFAULT_THRESHOLD, JEV_MODEL, JevVerifier
    from chatbot.rag_pipeline import answer_question, setup_vector_db

    systems = ("A", "B") if args.system == "both" else (args.system,)
    if "B" in systems and any(
        not str(row.get("student_id", "")).startswith("SYN-") for row in cases
    ):
        raise ValueError(
            "System B diagnostics are restricted to synthetic cases with SYN- student IDs."
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = args.output_dir / "metadata.json"
    dataset_hash = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    case_ids = [row["case_id"] for row in cases]
    if metadata_path.exists():
        if not args.resume:
            raise FileExistsError(f"{metadata_path} exists; use a new directory or --resume.")
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (previous.get("dataset_sha256") != dataset_hash
                or previous.get("selected_case_ids") != case_ids
                or previous.get("jev_enabled", True) != (not args.disable_jev)
                or ("B" in systems and previous.get("diagnostics_schema_version") != 1)):
            raise ValueError("Cannot resume: dataset hash, selected case IDs, or Jev configuration differ.")
    else:
        write_metadata(metadata_path, args.dataset, cases, GROQ_MODEL, JEV_MODEL,
                       DEFAULT_THRESHOLD, DB_NAME, use_jev=not args.disable_jev)

    user = get_user("faculty1")
    if not user or user.get("role") not in {"admin", "faculty"}:
        raise RuntimeError("Research identity faculty1 is missing or lacks faculty access.")

    print("Building the vector store once for both conditions...", flush=True)
    vectorstore = setup_vector_db()
    jev_verifier = JevVerifier() if not args.disable_jev else None
    if args.disable_jev:
        print("Jev disabled for this ablation; local matching and authorization remain enabled.", flush=True)
    for system in systems:
        run_condition(system, cases, args.output_dir, vectorstore, user,
                      answer_question, jev_verifier, args.resume, use_jev=not args.disable_jev)
    print(f"Run completed. Results: {args.output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
