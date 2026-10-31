"""Core RAG pipeline with deterministic resolution, Jev signal, and RBAC."""

import re
from pathlib import Path
from typing import Callable

from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from chatbot.auth import can_access_student
from chatbot.candidate_matcher import match_candidate, normalize_name
from chatbot.database import fetch_student_names_from_db, fetch_student_records_from_db
from chatbot.evidence_verifier import verify_answer_against_evidence
from chatbot.jev_verifier import JevVerifier
from chatbot.llm_client import GroqAPIError, query_groq_api

EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
DEBUG_DUMP_PATH = Path(__file__).resolve().parents[2] / "data" / "combined_student_records_from_db.txt"

# Prefer specific phrases so "What is the fee status for Alice Smith?" resolves
# to Alice Smith rather than treating "the fee status for Alice Smith" as a name.
NAME_PATTERNS = (
    re.compile(
        r"\b(?:what is|tell me about|show me details for|details for|record of|"
        r"who is|show me|for|of|about)\s+"
        r"([A-Za-z][A-Za-z\s'-]*?)(?:'s\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:show me details for|details for|record of|tell me about|who is|"
        r"for|of|about|show me|student)\s+"
        r"([A-Za-z][A-Za-z\s'-]*?)(?:'s\b|[?.,]|$)",
        re.IGNORECASE,
    ),
)
STUDENT_RECORD_TERMS = re.compile(
    r"\b(student|discipline|scholarship|fee|roll number|registration number|"
    r"student record|enrollment|enrolment)\b",
    re.IGNORECASE,
)


def setup_vector_db() -> Chroma:
    """Build the vector store with each document tagged by its canonical student ID."""
    records = fetch_student_records_from_db()
    if not records:
        raise ValueError("No student records found in the database; cannot create a vector store.")

    try:
        DEBUG_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEBUG_DUMP_PATH.write_text(
            "\n\n".join(record["text"] for record in records),
            encoding="utf-8",
        )
    except OSError:
        pass

    documents = [
        Document(
            page_content=record["text"],
            metadata={"student_id": record["student_id"], "student_name": record["name"]},
        )
        for record in records
    ]
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise ValueError("Text splitting produced no chunks from the database data.")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return Chroma.from_documents(chunks, embeddings)


def retrieve_student_record_evidence(
    vectorstore: Chroma,
    student_name: str,
    user_question: str,
    student_id: str | None = None,
) -> list[str]:
    """Retrieve text evidence scoped to one canonical student ID."""
    if not student_id:
        return []
    query = f"Information about {student_name}. {user_question}"
    relevant_docs = vectorstore.similarity_search(
        query,
        k=4,
        filter={"student_id": str(student_id)},
    )
    return [doc.page_content for doc in relevant_docs if doc.page_content]


def build_student_record_prompt(
    student_name: str,
    user_question: str,
    evidence: list[str],
) -> str:
    """Build the grounded-answer prompt from already retrieved evidence."""
    if not evidence:
        return ""
    retrieved_text = "\n\n".join(evidence)
    return (
        f"Given only the following extracted record for {student_name}:\n{retrieved_text}\n\n"
        f'Answer the user\'s question about {student_name}: "{user_question}".\n'
        "Use only the supplied record. If the requested detail is absent, say it is not available. "
        "Do not infer or reveal information about any other student."
    )


def get_student_record_prompt(
    vectorstore: Chroma,
    student_name: str,
    user_question: str,
    student_id: str | None = None,
) -> str:
    """Retrieve scoped evidence and return the original contextualized prompt."""
    evidence = retrieve_student_record_evidence(
        vectorstore, student_name, user_question, student_id
    )
    return build_student_record_prompt(student_name, user_question, evidence)


def extract_student_name(query: str) -> str | None:
    """Best-effort name extraction for common query forms; ambiguous names are rejected later."""
    for pattern in NAME_PATTERNS:
        match = pattern.search(query)
        if match:
            name = " ".join(match.group(1).strip().split())
            if name:
                return name.title()
    return None


def _names_mentioned_in_query(query: str, candidates: list[dict]) -> list[dict]:
    """Find canonical full names explicitly mentioned in the query."""
    normalized_query = f" {normalize_name(query)} "
    found = []
    for candidate in candidates:
        name = normalize_name(str(candidate.get("name") or ""))
        if name and f" {name} " in normalized_query:
            found.append(candidate)
    # Prefer a fully mentioned longer name over its prefix (e.g. "David Miller Jr"
    # should not also count as a separate mention of "David Miller"). Duplicate
    # rows with the same canonical name remain ambiguous because their IDs differ.
    filtered = []
    normalized_names = [normalize_name(str(item.get("name") or "")) for item in found]
    for index, candidate in enumerate(found):
        name = normalized_names[index]
        shadowed_by_longer_name = any(
            other != name and other.startswith(name + " ")
            for other in normalized_names
        )
        if not shadowed_by_longer_name:
            filtered.append(candidate)
    return filtered


def answer_question(
    vectorstore: Chroma,
    user_input: str,
    user: dict | None = None,
    verifier: JevVerifier | None = None,
    evidence_verification: bool = False,
    use_jev: bool = True,
    diagnostic_callback: Callable[[dict], None] | None = None,
) -> str:
    """Answer a question; optionally verify the requested field against retrieved evidence.

    Set evidence_verification=True only for the research experimental condition.
    Set use_jev=False only for the explicitly labelled no-Jev ablation; local
    deterministic candidate matching and authorization remain enabled.
    Defaults preserve the existing application behaviour.
    """
    student_name = extract_student_name(user_input)
    is_record_question = bool(STUDENT_RECORD_TERMS.search(user_input))

    if not student_name and not is_record_question:
        return query_groq_api(user_input)

    try:
        candidates = fetch_student_names_from_db()
    except RuntimeError:
        if not student_name:
            return (
                "I couldn't safely identify one student from that question. "
                "Please include the student's full name. No student record was accessed."
            )
        return "Student lookup is temporarily unavailable. No student record was accessed."

    mentioned = _names_mentioned_in_query(user_input, candidates)
    if len(mentioned) > 1:
        options = sorted({candidate["name"] for candidate in mentioned})
        return (
            "I found multiple student names in the question, so I can't safely choose one: "
            + ", ".join(options)
            + ". Please ask about one student at a time. No student record was accessed."
        )
    if len(mentioned) == 1:
        student_name = mentioned[0]["name"]

    if not student_name:
        return (
            "I couldn't safely identify one student from that question. "
            "Please include the student's full name. No student record was accessed."
        )

    match = match_candidate(student_name, candidates)
    if match.status == "NO_MATCH":
        return "I couldn't find that student in the directory. No student record was accessed."
    if match.status == "AMBIGUOUS":
        options = sorted({candidate["name"] for candidate in match.matches})
        return (
            "I found multiple possible students, so I can't safely choose one: "
            + ", ".join(options)
            + ". Please provide the exact full name. No student record was accessed."
        )

    candidate = match.candidate
    assert candidate is not None
    canonical_name = candidate["name"]
    student_id = candidate["student_id"]

    # Authorization precedes the third-party call and all record retrieval.
    if user is None:
        return "Please sign in before requesting student records. No student record was accessed."
    if not can_access_student(user, canonical_name, student_id):
        return (
            f"You don't have permission to view {canonical_name}'s record. "
            "Student accounts can only view their own record."
        )

    if use_jev:
        verifier = verifier or JevVerifier()
        result = verifier.verify(
            query=user_input,
            candidate=canonical_name,
            # Data minimization: send only the already-resolved candidate name.
            database_candidates=[canonical_name],
        )
        if result.decision != "ACCEPT":
            return (
                "I couldn't safely confirm which record to use, so I haven't retrieved any student data. "
                f"Resolution status: ABSTAIN ({result.reason})"
            )

    evidence = retrieve_student_record_evidence(
        vectorstore, canonical_name, user_input, student_id
    )
    prompt = build_student_record_prompt(canonical_name, user_input, evidence)
    if not prompt:
        return "The authorized student record could not be retrieved. No answer was generated."

    answer = query_groq_api(prompt)
    if evidence_verification:
        verification = verify_answer_against_evidence(
            question=user_input,
            answer=answer,
            evidence_text="\n\n".join(evidence),
        )
        final_output = answer
        if not verification.supported:
            final_output = (
                "I couldn't verify the requested answer against the retrieved student record. "
                "I won't present it as a fact. "
                f"Verification: {verification.reason}"
            )
        if diagnostic_callback is not None:
            diagnostic_callback({
                "generated_answer": answer,
                "evidence": list(evidence),
                "verification": {
                    "supported": verification.supported,
                    "field": verification.field,
                    "evidence_value": verification.evidence_value,
                    "reason": verification.reason,
                },
                "final_output": final_output,
            })
        if not verification.supported:
            return final_output
    return answer


def run_console() -> None:
    """Interactive console loop. Student records require an authenticated user."""
    vectorstore = setup_vector_db()
    print("Welcome to the Student Record Chatbot!")
    print("Student-record questions require an authenticated user session.")
    print("Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in {"quit", "exit", "bye", "stop"}:
            print("Goodbye!")
            break
        print("Bot:", answer_question(vectorstore, user_input))


if __name__ == "__main__":
    run_console()
