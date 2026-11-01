import pytest

from scripts.run_repeated_research_experiment import select_cases


def test_select_cases_by_id_preserves_canonical_dataset_order():
    dataset = [
        {"case_id": "ANS-001", "category": "answerable"},
        {"case_id": "AMB-001", "category": "ambiguous"},
        {"case_id": "MIS-001", "category": "missing", "source_state": "null_value"},
        {"case_id": "MIS-026", "category": "missing", "source_state": "related_record_absent"},
        {"case_id": "ANS-002", "category": "answerable"},
    ]

    selected = select_cases(dataset, case_ids=["MIS-026", "ANS-001", "AMB-001"])

    assert [case["case_id"] for case in selected] == [
        "ANS-001", "AMB-001", "MIS-026"
    ]


def test_select_cases_rejects_unknown_ids():
    with pytest.raises(ValueError, match="Unknown case IDs"):
        select_cases([{"case_id": "ANS-001"}], case_ids=["NOPE-001"])


def test_select_cases_rejects_duplicate_requested_ids():
    with pytest.raises(ValueError, match="duplicate IDs"):
        select_cases([{"case_id": "ANS-001"}], case_ids=["ANS-001", "ANS-001"])


def test_select_cases_rejects_limit_and_ids_together():
    with pytest.raises(ValueError, match="cannot be used together"):
        select_cases([{"case_id": "ANS-001"}], case_ids=["ANS-001"], limit=1)


def test_select_cases_keeps_existing_limit_behavior():
    dataset = [{"case_id": f"ANS-{i:03d}"} for i in range(1, 4)]

    selected = select_cases(dataset, limit=2)

    assert [case["case_id"] for case in selected] == ["ANS-001", "ANS-002"]
