from chatbot.evidence_verifier import requested_field, verify_answer_against_evidence


def test_recognizes_structured_fields():
    assert requested_field("What is Alice Smith's scholarship name?") == "scholarship_name"
    assert requested_field("What is Alice's scholarship status?") == "enrollment_status"
    assert requested_field("What is Alice's fee status?") == "fee_status"
    assert requested_field("Which department is Alice enrolled in?") == "discipline"
    assert requested_field("What subject area is Alice enrolled in?") == "discipline"


def test_accepts_answer_supported_by_retrieved_evidence():
    result = verify_answer_against_evidence(
        "What is Alice Smith's discipline?",
        "Alice studies Computer Science.",
        "Student Name: Alice Smith -- Discipline: Computer Science",
    )
    assert result.supported
    assert result.evidence_value == "Computer Science"


def test_rejects_conflicting_answer():
    result = verify_answer_against_evidence(
        "What is Alice Smith's fee status?",
        "Pending",
        "Student Name: Alice Smith -- Fee Status: Paid",
    )
    assert not result.supported
    assert result.reason == "answer_does_not_contain_evidence_value"


def test_missing_requested_field_fails_closed():
    result = verify_answer_against_evidence(
        "What is Alice Smith's scholarship status?",
        "Enrolled",
        "Student Name: Alice Smith -- Discipline: Computer Science",
    )
    assert not result.supported
    assert result.reason == "requested_field_missing_from_evidence"


def test_unrecognized_field_fails_closed():
    result = verify_answer_against_evidence(
        "What is Alice Smith's CGPA?",
        "3.5",
        "Student Name: Alice Smith -- Discipline: Computer Science",
    )
    assert not result.supported
    assert result.reason == "unrecognized_requested_field"
