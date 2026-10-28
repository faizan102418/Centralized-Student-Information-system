"""Core RAG pipeline with deterministic resolution, Jev signal, and RBAC."""

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from chatbot.auth import can_access_student
from chatbot.candidate_matcher import match_candidate
from chatbot.database import fetch_student_names_from_db, fetch_student_records_from_db
from chatbot.jev_verifier import JevVerifier
from chatbot.llm_client import query_groq_api

EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
DEBUG_DUMP_PATH = Path(__file__).resolve().parents[2] / "data" / "combined_student_records_from_db.txt"

NAME_PATTERN = re.compile(
    r"(?:student|for|of|about|details for|record of|show me|what is|"
    r"tell me about|who is)\s+"
    r"([A-Za-z][A-Za-z\s'-]*?)(?:'s\b|[?.,]|$)",
    re.IGNORECASE,
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


def get_student_record_prompt(
    vectorstore: Chroma,
    student_name: str,
    user_question: str,
    student_id: str | None = None,
) -> str:
    """Retrieve context scoped to one canonical student ID, never global nearest chunks."""
    query = f"Information about {student_name}. {user_question}"
    if not student_id:
        # Do not permit an unscoped record retrieval.
        return ""
    relevant_docs = vectorstore.similarity_search(
        query,
        k=4,
        filter={"student_id": str(student_id)},
    )
    if not relevant_docs:
        return ""

    retrieved_text = "\n\n".join(doc.page_content for doc in relevant_docs)
    return (
        f"Given only the following extracted record for {student_name}:\n{retrieved_text}\n\n"
        f'Answer the user\'s question about {student_name}: "{user_question}".\n'
        "Use only the supplied record. If the requested detail is absent, say it is not available. "
        "Do not infer or reveal information about any other student."
    )


def extract_student_name(query: str) -> str | None:
    """Best-effort regex name extraction; unresolved phrasing must fail closed."""
    match = NAME_PATTERN.search(query)
    if not match:
        return None
    return " ".join(match.group(1).strip().split()).title()


def answer_question(
    vectorstore: Chroma,
    user_input: str,
    user: dict | None = None,
    verifier: JevVerifier | None = None,
) -> str:
    """Answer general questions, or safely resolve, authorize, then retrieve a student record."""
    student_name = extract_student_name(user_input)
    if not student_name:
        if STUDENT_RECORD_TERMS.search(user_input):
            return (
                "I couldn't safely identify one student from that question. "
                "Please include the student's full name. No student record was accessed."
            )
        return query_groq_api(user_input)

    try:
        candidates = fetch_student_names_from_db()
    except RuntimeError:
        return "Student lookup is temporarily unavailable. No student record was accessed."

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

    prompt = get_student_record_prompt(vectorstore, canonical_name, user_input, student_id)
    if not prompt:
        return "The authorized student record could not be retrieved. No answer was generated."

    return query_groq_api(prompt)


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
