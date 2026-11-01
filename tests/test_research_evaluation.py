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
    assert metrics["missing_abstention_precision"] == 0.5
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


def test_evaluator_keeps_systems_separate_for_same_case_and_run():
    dataset = [case("a1", "answerable", "answer", "Paid")]
    predictions = [
        {"system": "A", "case_id": "a1", "run_number": 1, "decision": "answer",
         "answer": "Paid", "latency_ms": 10},
        {"system": "B", "case_id": "a1", "run_number": 1, "decision": "abstain",
         "answer": "", "latency_ms": 20},
    ]

    result = evaluate(dataset, predictions)

    assert result["n_systems"] == 2
    assert result["systems"]["A"]["per_run"]["1"]["metrics"]["decision_accuracy"] == 1.0
    assert result["systems"]["B"]["per_run"]["1"]["metrics"]["decision_accuracy"] == 0.0
    assert result["systems"]["A"]["summary"]["median_latency_ms"]["mean_across_runs"] == 10
    assert result["systems"]["B"]["summary"]["median_latency_ms"]["mean_across_runs"] == 20


def test_evaluator_groups_repeated_runs_independently_per_system():
    dataset = [case("a1", "answerable", "answer", "Paid")]
    predictions = [
        {"system": "A", "case_id": "a1", "run_number": 1, "decision": "answer",
         "answer": "Paid", "latency_ms": 10},
        {"system": "A", "case_id": "a1", "run_number": 2, "decision": "answer",
         "answer": "Paid", "latency_ms": 20},
        {"system": "B", "case_id": "a1", "run_number": 1, "decision": "answer",
         "answer": "Paid", "latency_ms": 30},
    ]

    result = evaluate(dataset, predictions)

    assert result["systems"]["A"]["n_runs"] == 2
    assert result["systems"]["A"]["n_attempts"] == 2
    assert result["systems"]["B"]["n_runs"] == 1
    assert result["systems"]["B"]["n_attempts"] == 1


def test_evaluator_rejects_duplicate_case_within_same_system_and_run():
    dataset = [case("a1", "answerable", "answer", "Paid")]
    predictions = [
        {"system": "A", "case_id": "a1", "run_number": 1, "decision": "answer", "answer": "Paid"},
        {"system": "A", "case_id": "a1", "run_number": 1, "decision": "answer", "answer": "Paid"},
    ]

    with pytest.raises(ValueError, match="Duplicate system/case/run key"):
        evaluate(dataset, predictions)


def test_evaluator_supports_a_matching_dataset_subset_for_each_system():
    dataset = [
        case("pilot-1", "answerable", "answer", "Paid"),
        case("pilot-2", "missing", "abstain"),
    ]
    predictions = [
        {"system": "A", "case_id": "pilot-1", "decision": "answer", "answer": "Paid"},
        {"system": "A", "case_id": "pilot-2", "decision": "abstain", "answer": ""},
        {"system": "B", "case_id": "pilot-1", "decision": "answer", "answer": "Paid"},
        {"system": "B", "case_id": "pilot-2", "decision": "abstain", "answer": ""},
    ]

    result = evaluate(dataset, predictions)

    assert result["n_queries"] == 2
    assert result["systems"]["A"]["n_queries"] == 2
    assert result["systems"]["B"]["n_queries"] == 2
    assert result["systems"]["A"]["n_attempts"] == 2
    assert result["systems"]["B"]["n_attempts"] == 2
