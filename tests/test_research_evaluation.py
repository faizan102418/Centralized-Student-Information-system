import pytest

from scripts.evaluate_research import evaluate


def case(case_id, category, decision, answer=""):
    return {
        "case_id": case_id,
        "category": category,
        "expected_decision": decision,
        "expected_answer": answer,
    }


def test_evaluator_reports_answer_coverage_and_decision_quality():
    dataset = [
        case("a1", "answerable", "answer", "Computer Science"),
        case("a2", "answerable", "answer", "Paid"),
        case("u1", "ambiguous", "clarify"),
        case("m1", "missing", "abstain"),
    ]
    predictions = [
        {"case_id": "a1", "decision": "answer", "answer": "Computer Science"},
        {"case_id": "a2", "decision": "abstain", "answer": ""},
        {"case_id": "u1", "decision": "clarify", "answer": ""},
        {"case_id": "m1", "decision": "abstain", "answer": ""},
    ]
    metrics = evaluate(dataset, predictions)["per_run"]["1"]["metrics"]
    assert metrics["decision_accuracy"] == 0.75
    assert metrics["answer_coverage_on_answerable"] == 0.5
    assert metrics["exact_answer_accuracy_when_answered"] == 1.0
    assert metrics["unnecessary_nonanswer_rate_on_answerable"] == 0.5
    assert metrics["unsafe_answer_rate_on_non_answerable"] == 0.0
    assert metrics["correct_nonanswer_rate_on_non_answerable"] == 1.0
    assert metrics["clarification_precision"] == 1.0
    assert metrics["clarification_recall"] == 1.0
    assert metrics["missing_abstention_precision"] == 1.0
    assert metrics["missing_abstention_recall"] == 1.0


def test_evaluator_aggregates_repeated_runs_by_run_number():
    dataset = [case("a1", "answerable", "answer", "Paid")]
    predictions = [
        {"case_id": "a1", "run_number": 1, "decision": "answer", "answer": "Paid", "latency_ms": 10},
        {"case_id": "a1", "run_number": 2, "decision": "answer", "answer": "Paid", "latency_ms": 20},
    ]
    result = evaluate(dataset, predictions)
    assert result["n_runs"] == 2
    assert result["n_attempts"] == 2
    assert result["summary"]["median_latency_ms"]["mean_across_runs"] == 15


def test_evaluator_requires_matching_case_ids():
    with pytest.raises(ValueError, match="exactly one prediction"):
        evaluate(
            [case("a1", "answerable", "answer", "Paid")],
            [{"case_id": "x", "decision": "answer", "answer": "Paid"}],
        )
