from pathlib import Path
import json
import sys
import pytest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_research_experiment import (
    classify_output, run_condition, select_cases, validate_diagnostic_scope,
)


def test_classifies_ambiguous_name_as_clarification():
    assert classify_output("I found multiple possible students. Please provide the exact full name.") == "clarify"


def test_classifies_evidence_rejection_as_abstention():
    assert classify_output("I couldn't verify the requested answer. Verification: unrecognized_requested_field") == "abstain"


def test_classifies_missing_information_as_abstention():
    assert classify_output("Maya Patel's CGPA is not available in the provided record.") == "abstain"


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
        run_condition("A", [{"case_id": "C1", "query": "q"}], tmp_path,
                      object(), {"role": "faculty"},
                      Mock(return_value="Jev verification unavailable (Timeout)."),
                      Mock())
    assert not (tmp_path / "system_a_predictions.jsonl").exists()
    raw = json.loads((tmp_path / "system_a_raw.jsonl").read_text().strip())
    assert raw["decision"] == "error"


def test_success_writes_compact_scoring_answer_and_full_raw_output(tmp_path):
    run_condition("B", [{"case_id": "C2", "query": "q"}], tmp_path,
                  object(), {"role": "faculty"},
                  Mock(return_value="Maya Patel's discipline is **Computer Science**."),
                  Mock())
    prediction = json.loads((tmp_path / "system_b_predictions.jsonl").read_text().strip())
    raw = json.loads((tmp_path / "system_b_raw.jsonl").read_text().strip())
    assert prediction == {"case_id": "C2", "decision": "answer", "answer": "Computer Science"}
    assert "**Computer Science**" in raw["raw_output"]


def test_run_condition_passes_explicit_no_jev_configuration(tmp_path):
    answer_fn = Mock(return_value="Computer Science")
    run_condition(
        "A",
        [{"case_id": "C3", "query": "q"}],
        tmp_path,
        object(),
        {"role": "faculty"},
        answer_fn,
        None,
        use_jev=False,
    )
    assert answer_fn.call_args.kwargs["use_jev"] is False
    assert answer_fn.call_args.kwargs["evidence_verification"] is False
    raw = json.loads((tmp_path / "system_a_raw.jsonl").read_text().strip())
    assert raw["jev_calls"] == []


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

    run_condition("B", [{"case_id": "ANS-006", "query": "q"}], tmp_path,
                  object(), {"role": "faculty"}, answer_fn, None, use_jev=False)
    diagnostic = json.loads((tmp_path / "system_b_diagnostics.jsonl").read_text().strip())
    prediction = json.loads((tmp_path / "system_b_predictions.jsonl").read_text().strip())
    assert diagnostic["generated_answer"] == "The fee status is Paid."
    assert diagnostic["verification"]["reason"] == "answer_does_not_contain_evidence_value"
    assert prediction == {"case_id": "ANS-006", "decision": "abstain", "answer": ""}


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
        validate_diagnostic_scope(
            [{"case_id": "AMB-001"}],
            "university_db",
        )



def test_operational_exception_is_not_scored_and_resume_retries_case(tmp_path):
    cases = [{"case_id": "C-RETRY", "query": "q"}]
    failing_answer = Mock(side_effect=RuntimeError("temporary API failure"))
    with pytest.raises(RuntimeError, match="Stopped at C-RETRY"):
        run_condition("A", cases, tmp_path, object(), {"role": "faculty"},
                      failing_answer, None, use_jev=False)

    predictions = tmp_path / "system_a_predictions.jsonl"
    raw = tmp_path / "system_a_raw.jsonl"
    assert not predictions.exists()
    failed_row = json.loads(raw.read_text(encoding="utf-8").splitlines()[0])
    assert failed_row["decision"] == "error"
    assert failed_row["error_type"] == "RuntimeError"

    successful_answer = Mock(return_value="Computer Science")
    run_condition("A", cases, tmp_path, object(), {"role": "faculty"},
                  successful_answer, None, resume=True, use_jev=False)

    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
    prediction = json.loads(predictions.read_text(encoding="utf-8").strip())
    assert len(rows) == 2
    assert rows[0]["decision"] == "error"
    assert rows[1]["decision"] == "answer"
    assert prediction == {
        "case_id": "C-RETRY", "decision": "answer", "answer": "Computer Science"
    }
