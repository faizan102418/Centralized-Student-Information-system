from pathlib import Path
import json
import sys
import pytest
import requests
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_research_experiment import (
    classify_output, run_condition, select_cases, validate_diagnostic_scope,
)
from experiment_error_utils import safe_exception_details


def test_classifies_ambiguous_name_as_clarification():
    assert classify_output("I found multiple possible students. Please provide the exact full name.") == "clarify"


def test_classifies_evidence_rejection_as_abstention():
    assert classify_output("I couldn't verify the requested answer. Verification: unrecognized_requested_field") == "abstain"


def test_classifies_missing_information_as_abstention():
    assert classify_output("The requested information is not available in the source student record.") == "abstain"


def test_classifies_api_failure_as_error_not_abstention():
    assert classify_output("Could not reach the Groq API: timeout") == "error"
    assert classify_output("Jev verification unavailable (Timeout).") == "error"


def test_unknown_normal_response_is_answer():
    assert classify_output("Maya Patel's discipline is Computer Science.") == "answer"


def test_pilot_is_balanced_and_deterministic():
    rows = ([{"case_id": f"a{i}", "category": "answerable"} for i in range(3)]
            + [{"case_id": f"b{i}", "category": "ambiguous"} for i in range(3)]
            + [{"case_id": f"m{i}", "category": "missing"} for i in range(3)])
    assert [r["case_id"] for r in select_cases(rows, pilot=True)] == [
        "a0", "a1", "b0", "b1", "m0", "m1"
    ]


def test_limit_selects_first_n_cases():
    rows = [{"case_id": str(i)} for i in range(5)]
    assert [r["case_id"] for r in select_cases(rows, limit=2)] == ["0", "1"]


def test_operational_error_is_logged_but_not_scored(tmp_path):
    with pytest.raises(RuntimeError, match="Stopped"):
        run_condition("A", 1, [{"case_id": "C1", "query": "q"}], tmp_path,
                      object(), {"role": "faculty"},
                      Mock(return_value="Jev verification unavailable (Timeout)."),
                      Mock())
    assert not (tmp_path / "system_a_run_01_predictions.jsonl").exists()
    raw = json.loads((tmp_path / "system_a_run_01_raw.jsonl").read_text().strip())
    assert raw["decision"] == "error"


def test_success_writes_compact_scoring_answer_and_full_raw_output(tmp_path):
    run_condition("B", 1, [{"case_id": "C2", "query": "q"}], tmp_path,
                  object(), {"role": "faculty"},
                  Mock(return_value="Maya Patel's discipline is **Computer Science**."),
                  Mock(), use_jev=False)
    prediction = json.loads((tmp_path / "system_b_run_01_predictions.jsonl").read_text().strip())
    raw = json.loads((tmp_path / "system_b_run_01_raw.jsonl").read_text().strip())
    assert prediction["case_id"] == "C2"
    assert prediction["run_number"] == 1
    assert prediction["system"] == "B"
    assert prediction["decision"] == "answer"
    assert prediction["answer"] == "Computer Science"
    assert prediction["latency_ms"] >= 0
    assert "**Computer Science**" in raw["raw_output"]


def test_run_condition_passes_explicit_no_jev_configuration(tmp_path):
    answer_fn = Mock(return_value="Computer Science")
    run_condition(
        "A", 1, [{"case_id": "C3", "query": "q"}], tmp_path,
        object(), {"role": "faculty"}, answer_fn, None, use_jev=False,
    )
    assert answer_fn.call_args.kwargs["use_jev"] is False
    assert answer_fn.call_args.kwargs["evidence_verification"] is False
    assert answer_fn.call_args.kwargs["selective_decisions"] is False
    raw = json.loads((tmp_path / "system_a_run_01_raw.jsonl").read_text().strip())
    assert raw["jev_calls"] == []


def test_system_c_enables_verification_and_selective_decisions(tmp_path):
    answer_fn = Mock(return_value="The requested information is not available in the source student record.")
    run_condition("C", 1, [{"case_id": "MIS-001", "query": "q"}], tmp_path,
                  object(), {"role": "faculty"}, answer_fn, None, use_jev=False)
    assert answer_fn.call_args.kwargs["evidence_verification"] is True
    assert answer_fn.call_args.kwargs["selective_decisions"] is True
    prediction = json.loads((tmp_path / "system_c_run_01_predictions.jsonl").read_text().strip())
    assert prediction["decision"] == "abstain"


def test_system_b_persists_diagnostics_separately_from_scoring_outputs(tmp_path):
    def answer_fn(*args, diagnostic_callback=None, **kwargs):
        assert kwargs["evidence_verification"] is True
        diagnostic_callback({
            "generated_answer": "The fee status is Paid.",
            "evidence": ["Student Name: Maya Patel -- Fee Status: Paid"],
            "verification": {
                "supported": False,
                "field": "fee_status",
                "evidence_value": "Paid",
                "reason": "answer_does_not_contain_evidence_value",
            },
            "final_output": "I couldn't verify the requested answer.",
        })
        return "I couldn't verify the requested answer."

    run_condition("B", 1, [{"case_id": "ANS-006", "query": "q"}], tmp_path,
                  object(), {"role": "faculty"}, answer_fn, None, use_jev=False)
    diagnostic = json.loads((tmp_path / "system_b_diagnostics.jsonl").read_text().strip())
    prediction = json.loads((tmp_path / "system_b_run_01_predictions.jsonl").read_text().strip())
    assert diagnostic["generated_answer"] == "The fee status is Paid."
    assert diagnostic["verification"]["reason"] == "answer_does_not_contain_evidence_value"
    assert prediction["case_id"] == "ANS-006"
    assert prediction["run_number"] == 1
    assert prediction["decision"] == "abstain"
    assert prediction["answer"] == ""


def test_diagnostic_scope_allows_pre_retrieval_cases_without_student_ids():
    cases = [
        {"case_id": "ANS-001", "student_id": "SYN-001"},
        {"case_id": "AMB-001"},
        {"case_id": "MIS-001", "student_id": "SYN-002"},
    ]
    validate_diagnostic_scope(cases, "research_eval")


def test_diagnostic_scope_rejects_non_synthetic_student_ids():
    with pytest.raises(ValueError, match="research_eval"):
        validate_diagnostic_scope(
            [{"case_id": "ANS-001", "student_id": "real-student-123"}],
            "research_eval",
        )


def test_diagnostic_scope_rejects_non_research_database():
    with pytest.raises(ValueError, match="research_eval"):
        validate_diagnostic_scope([{"case_id": "AMB-001"}], "university_db")


def test_operational_exception_is_not_scored_and_resume_retries_case(tmp_path):
    cases = [{"case_id": "C-RETRY", "query": "q"}]
    failing_answer = Mock(side_effect=RuntimeError("temporary API failure"))
    with pytest.raises(RuntimeError, match="Stopped at C-RETRY"):
        run_condition("A", 1, cases, tmp_path, object(), {"role": "faculty"},
                      failing_answer, None, use_jev=False)

    predictions = tmp_path / "system_a_run_01_predictions.jsonl"
    raw = tmp_path / "system_a_run_01_raw.jsonl"
    assert not predictions.exists()
    failed_row = json.loads(raw.read_text(encoding="utf-8").splitlines()[0])
    assert failed_row["decision"] == "error"
    assert failed_row["error_type"] == "RuntimeError"
    assert failed_row["error_category"] == "application_error"
    assert "error_message" not in failed_row

    successful_answer = Mock(return_value="Computer Science")
    run_condition("A", 1, cases, tmp_path, object(), {"role": "faculty"},
                  successful_answer, None, resume=True, use_jev=False)

    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
    prediction = json.loads(predictions.read_text(encoding="utf-8").strip())
    assert len(rows) == 2
    assert rows[0]["decision"] == "error"
    assert rows[1]["decision"] == "answer"
    assert prediction["case_id"] == "C-RETRY"
    assert prediction["run_number"] == 1
    assert prediction["decision"] == "answer"
    assert prediction["answer"] == "Computer Science"



def test_safe_groq_diagnostics_preserve_http_status_without_request_message():
    class GroqAPIError(RuntimeError):
        pass

    response = Mock()
    response.status_code = 503
    cause = requests.exceptions.HTTPError(
        "sensitive request detail should not be logged", response=response
    )
    error = GroqAPIError("Groq API request failed (HTTP 503) after 3 attempts.")
    error.__cause__ = cause

    details = safe_exception_details(error)

    assert details == {
        "error_type": "GroqAPIError",
        "error_message": "Groq API request failed (HTTP 503) after 3 attempts.",
        "error_cause_type": "HTTPError",
        "http_status": 503,
        "error_category": "http_error",
    }
    assert "sensitive request detail" not in str(details)


def test_runner_logs_groq_failure_details_but_never_scores_it(tmp_path):
    class GroqAPIError(RuntimeError):
        pass

    response = Mock()
    response.status_code = 429
    cause = requests.exceptions.HTTPError("rate limit response body", response=response)
    error = GroqAPIError("Groq API request failed (HTTP 429) after 3 attempts.")
    error.__cause__ = cause

    with pytest.raises(RuntimeError, match="Stopped at C-GROQ"):
        run_condition(
            "A", 1, [{"case_id": "C-GROQ", "query": "q"}], tmp_path,
            object(), {"role": "faculty"}, Mock(side_effect=error), None,
            use_jev=False,
        )

    raw_path = tmp_path / "system_a_run_01_raw.jsonl"
    predictions_path = tmp_path / "system_a_run_01_predictions.jsonl"
    row = json.loads(raw_path.read_text(encoding="utf-8").strip())
    assert row["decision"] == "error"
    assert row["error_type"] == "GroqAPIError"
    assert row["http_status"] == 429
    assert row["error_category"] == "http_error"
    assert row["error_message"].endswith("after 3 attempts.")
    assert "rate limit response body" not in raw_path.read_text(encoding="utf-8")
    assert not predictions_path.exists()
