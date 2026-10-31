import pytest

from scripts.evaluate_research import evaluate


def case(case_id, category, decision, answer=""):
    return {"case_id": case_id, "category": category, "expected_decision": decision, "expected_answer": answer}


def test_evaluator_reports_answer_coverage_and_abstention_quality():
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
    metrics = evaluate(dataset, predictions)["metrics"]
    assert metrics["decision_accuracy"] == 0.75
    assert metrics["answer_coverage_on_answerable"] == 0.5
    assert metrics["exact_answer_accuracy_when_answered"] == 1.0
    assert metrics["unnecessary_nonanswer_rate_on_answerable"] == 0.5
    assert metrics["ambiguous_clarification_rate"] == 1.0
    assert metrics["missing_information_abstention_rate"] == 1.0


def test_evaluator_requires_matching_case_ids():
    with pytest.raises(ValueError, match="do not match"):
        evaluate([case("a1", "answerable", "answer", "Paid")], [{"case_id":"x","decision":"answer","answer":"Paid"}])
