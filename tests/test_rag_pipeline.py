import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatbot import rag_pipeline
from chatbot.rag_pipeline import answer_question, extract_student_name


def test_extracts_name_after_about():
    assert extract_student_name("Tell me about Alice Smith") == "Alice Smith"


def test_extracts_name_with_what_is():
    assert extract_student_name("What is Bob Johnson's discipline?") == "Bob Johnson"


def test_returns_none_for_general_question():
    assert extract_student_name("Hello, what can you do?") is None


def test_handles_extra_whitespace():
    assert extract_student_name("show me   diana   prince") == "Diana Prince"


def test_ambiguous_name_abstains_without_calling_jev(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [
            {"student_id": "1", "name": "Alice Smith"},
            {"student_id": "2", "name": "Alice Johnson"},
        ],
    )
    verifier = Mock()
    answer = answer_question(Mock(), "Tell me about Alice", user={"role": "admin"}, verifier=verifier)
    assert "multiple possible students" in answer
    verifier.verify.assert_not_called()


def test_unknown_student_abstains(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [{"student_id": "1", "name": "Alice Smith"}],
    )
    answer = answer_question(Mock(), "Tell me about Unknown Person", user={"role": "admin"})
    assert "couldn't find that student" in answer


def test_unauthorized_user_is_rejected_before_jev(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [{"student_id": "1", "name": "Alice Smith"}],
    )
    verifier = Mock()
    answer = answer_question(
        Mock(),
        "What is Alice Smith's discipline?",
        user={"role": "student", "student_id": "other-id", "student_name": "Bob Jones"},
        verifier=verifier,
    )
    assert "don't have permission" in answer
    verifier.verify.assert_not_called()


def test_missing_user_is_not_allowed_to_access_records(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [{"student_id": "1", "name": "Alice Smith"}],
    )
    verifier = Mock()
    answer = answer_question(Mock(), "What is Alice Smith's discipline?", verifier=verifier)
    assert "sign in" in answer
    verifier.verify.assert_not_called()


def test_jev_abstain_prevents_retrieval(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [{"student_id": "1", "name": "Alice Smith"}],
    )
    verifier = Mock()
    verifier.verify.return_value = Mock(decision="ABSTAIN", reason="test failure")
    vectorstore = Mock()
    answer = answer_question(
        vectorstore,
        "What is Alice Smith's discipline?",
        user={"role": "admin"},
        verifier=verifier,
    )
    assert "haven't retrieved any student data" in answer
    vectorstore.similarity_search.assert_not_called()


def test_successful_path_filters_retrieval_by_student_id(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [{"student_id": "student-123", "name": "Alice Smith"}],
    )
    verifier = Mock()
    verifier.verify.return_value = Mock(decision="ACCEPT", reason="provisional")
    vectorstore = Mock()
    vectorstore.similarity_search.return_value = [
        Mock(page_content="Student Name: Alice Smith -- Discipline: Computer Science")
    ]
    monkeypatch.setattr(rag_pipeline, "query_groq_api", lambda prompt: "Computer Science")

    answer = answer_question(
        vectorstore,
        "What is Alice Smith's discipline?",
        user={"role": "admin"},
        verifier=verifier,
    )
    assert answer == "Computer Science"
    assert vectorstore.similarity_search.call_args.kwargs["filter"] == {
        "student_id": "student-123"
    }


def test_student_specific_question_without_name_does_not_use_general_llm(monkeypatch):
    groq = Mock()
    monkeypatch.setattr(rag_pipeline, "query_groq_api", groq)
    answer = answer_question(Mock(), "What is the fee status?")
    assert "full name" in answer
    groq.assert_not_called()


def test_evidence_verification_rejects_unsupported_generated_answer(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [{"student_id": "student-123", "name": "Alice Smith"}],
    )
    verifier = Mock()
    verifier.verify.return_value = Mock(decision="ACCEPT", reason="provisional")
    vectorstore = Mock()
    vectorstore.similarity_search.return_value = [
        Mock(page_content="Student Name: Alice Smith -- Discipline: Computer Science")
    ]
    monkeypatch.setattr(rag_pipeline, "query_groq_api", lambda prompt: "Software Engineering")

    answer = answer_question(
        vectorstore,
        "What is Alice Smith's discipline?",
        user={"role": "admin"},
        verifier=verifier,
        evidence_verification=True,
    )
    assert "couldn't verify" in answer
    assert "won't present it as a fact" in answer


def test_evidence_verification_accepts_supported_answer(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [{"student_id": "student-123", "name": "Alice Smith"}],
    )
    verifier = Mock()
    verifier.verify.return_value = Mock(decision="ACCEPT", reason="provisional")
    vectorstore = Mock()
    vectorstore.similarity_search.return_value = [
        Mock(page_content="Student Name: Alice Smith -- Discipline: Computer Science")
    ]
    monkeypatch.setattr(rag_pipeline, "query_groq_api", lambda prompt: "Computer Science")

    answer = answer_question(
        vectorstore,
        "What is Alice Smith's discipline?",
        user={"role": "admin"},
        verifier=verifier,
        evidence_verification=True,
    )
    assert answer == "Computer Science"


def test_baseline_mode_preserves_existing_answer_without_evidence_check(monkeypatch):
    monkeypatch.setattr(
        rag_pipeline,
        "fetch_student_names_from_db",
        lambda: [{"student_id": "student-123", "name": "Alice Smith"}],
    )
    verifier = Mock()
    verifier.verify.return_value = Mock(decision="ACCEPT", reason="provisional")
    vectorstore = Mock()
    vectorstore.similarity_search.return_value = [
        Mock(page_content="Student Name: Alice Smith -- Discipline: Computer Science")
    ]
    monkeypatch.setattr(rag_pipeline, "query_groq_api", lambda prompt: "Software Engineering")

    answer = answer_question(
        vectorstore,
        "What is Alice Smith's discipline?",
        user={"role": "admin"},
        verifier=verifier,
        evidence_verification=False,
    )
    assert answer == "Software Engineering"
