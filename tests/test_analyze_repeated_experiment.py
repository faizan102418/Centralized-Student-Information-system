"""Regression tests for repeated prediction file discovery and validation."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_repeated_experiment import load_system


class LoadSystemTests(unittest.TestCase):
    def write_rows(self, path, rows):
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_combined_predictions_with_five_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            rows = [
                {"case_id": case, "run_number": run}
                for case in ("q1", "q2")
                for run in range(1, 6)
            ]
            self.write_rows(directory / "system_a_predictions.jsonl", rows)
            loaded = load_system(directory, "A")
            self.assertEqual(set(loaded), {"q1", "q2"})
            self.assertTrue(all(len(attempts) == 5 for attempts in loaded.values()))

    def test_legacy_per_run_files(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for run in (1, 2):
                self.write_rows(
                    directory / f"system_b_run_{run}_predictions.jsonl",
                    [{"case_id": "q1", "run_number": run}],
                )
            self.assertEqual(len(load_system(directory, "B")["q1"]), 2)

    def test_duplicate_case_run_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.write_rows(
                directory / "system_c_predictions.jsonl",
                [{"case_id": "q1", "run_number": 1}] * 2,
            )
            with self.assertRaisesRegex(ValueError, "duplicate case/run"):
                load_system(directory, "C")

    def test_unequal_repeat_counts_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.write_rows(
                directory / "system_a_predictions.jsonl",
                [
                    {"case_id": "q1", "run_number": 1},
                    {"case_id": "q1", "run_number": 2},
                    {"case_id": "q2", "run_number": 1},
                ],
            )
            with self.assertRaisesRegex(ValueError, "same number"):
                load_system(directory, "A")

    def test_missing_files_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                load_system(Path(temp), "A")


if __name__ == "__main__":
    unittest.main()
