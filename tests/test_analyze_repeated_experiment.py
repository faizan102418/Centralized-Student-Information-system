"""Regression tests for repeated-experiment prediction file discovery."""
import json

import pytest

from scripts.analyze_repeated_experiment import load_system


def write_predictions(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_load_system_combined_file_preserves_all_repetitions(tmp_path):
    rows = [
        {"case_id": case, "run_number": run, "decision": "answer", "latency_ms": 1.0}
        for case in ("ANS-001", "ANS-002")
        for run in range(1, 6)
    ]
    write_predictions(tmp_path / "system_a_predictions.jsonl", rows)

    loaded = load_system(tmp_path, "A")

    assert set(loaded) == {"ANS-001", "ANS-002"}
    assert all(len(attempts) == 5 for attempts in loaded.values())
    assert {row["run_number"] for row in loaded["ANS-001"]} == set(range(1, 6))


def test_load_system_supports_legacy_per_run_files(tmp_path):
    for run in (1, 2):
        write_predictions(
            tmp_path / f"system_b_run_{run}_predictions.jsonl",
            [{"case_id": "ANS-001", "run_number": run}],
        )

    loaded = load_system(tmp_path, "B")

    assert len(loaded["ANS-001"]) == 2


def test_load_system_rejects_duplicate_case_and_run_in_combined_file(tmp_path):
    row = {"case_id": "ANS-001", "run_number": 1}
    write_predictions(tmp_path / "system_c_predictions.jsonl", [row, row])

    with pytest.raises(ValueError, match="duplicate case/run output"):
        load_system(tmp_path, "C")


def test_load_system_rejects_unequal_repeat_counts(tmp_path):
    write_predictions(
        tmp_path / "system_a_predictions.jsonl",
        [
            {"case_id": "ANS-001", "run_number": 1},
            {"case_id": "ANS-001", "run_number": 2},
            {"case_id": "ANS-002", "run_number": 1},
        ],
    )

    with pytest.raises(ValueError, match="same number of repeated runs"):
        load_system(tmp_path, "A")


def test_load_system_prefers_per_run_files_if_both_formats_exist(tmp_path):
    write_predictions(
        tmp_path / "system_a_predictions.jsonl",
        [{"case_id": "ANS-001", "run_number": 1}],
    )
    write_predictions(
        tmp_path / "system_a_run_1_predictions.jsonl",
        [{"case_id": "ANS-002", "run_number": 1}],
    )

    assert set(load_system(tmp_path, "A")) == {"ANS-002"}


def test_load_system_missing_files_reports_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="No repeated prediction files found"):
        load_system(tmp_path, "A")
